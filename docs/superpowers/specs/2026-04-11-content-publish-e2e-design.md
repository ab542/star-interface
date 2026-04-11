# 素材发布完整业务流程端到端测试设计

## 需求概述

实现一个完整的业务流程自动化测试：
1. 在素材库创建文件夹
2. 在文件夹中上传素材并保存
3. 查询素材列表接口，获取素材ID
4. 查询授权账户（发布达人）列表接口，获取可用账户ID
5. 选中素材和账户进行发布
6. 最后查询发布列表，验证新发布数据存在

## 架构设计

### 总体方案

在保持现有数据驱动测试架构基础上，**扩展支持 `pre_steps` 前置步骤功能**，允许多个接口按顺序链式调用，后续接口可以从先前接口响应中提取数据作为自己的请求参数。

- 不破坏现有功能：原有单接口独立测试用例仍然正常工作
- 增量扩展：只在有 `pre_steps` 的用例才启用链式调用
- 遵循现有约定：YAML 格式配置，无需编写 Python 代码

### YAML 格式扩展

#### 新增字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pre_steps` | `list[PreStep]` | 否 | 前置步骤列表，按顺序执行 |
| `pre_steps[*].extract` | `dict[str, str]` | 否 | 提取变量字典，key=变量名，value=JSONPath |

#### JSONPath 语法

采用简化 JSONPath，支持点号访问：
- `data.id` → `response.json()['data']['id']`
- `data.items[0].id` → `response.json()['data']['items'][0]['id']`
- 支持数组索引访问，不支持复杂查询语法

#### 占位符语法

在 `params` / `json` / `data` 中使用占位符 `${step_name.json.path}` 引用前置步骤提取的变量：
- `${create_folder.data.id}` → 替换为 `create_folder` 步骤响应中 `data.id` 的值
- `${get_accounts.data.list[0].id}` → 取第一个账户的ID

#### 完整示例

```yaml
- name: "content_publish - 完整端到端业务流程测试"
  description: "创建文件夹 → 上传素材 → 查询素材 → 查询授权账户 → 发布 → 验证发布列表"
  pre_steps:
    - name: "create_folder"
      method: POST
      url: /api/material/folder/create
      headers:
        Content-Type: application/json
      json:
        name: "auto-test-folder"
        description: "自动化测试创建文件夹"
      expected_status: 200
      expected_response:
        code: 0
      extract:
        folder_id: "data.id"

    - name: "upload_material"
      method: POST
      url: /api/material/upload
      json:
        folderId: "${create_folder.data.id}"
        name: "test_material.jpg"
        type: 1
      expected_status: 200
      expected_response:
        code: 0
      extract:
        material_id: "data.id"

    - name: "get_material_list"
      method: POST
      url: /api/material/list
      json:
        page: 1
        size: 10
      expected_status: 200
      expected_response:
        code: 0
      extract:
        latest_material_id: "data.list[0].id"

    - name: "get_author_accounts"
      method: POST
      url: /api/publish/accounts
      json:
        page: 1
        size: 10
      expected_status: 200
      expected_response:
        code: 0
      extract:
        first_account_id: "data.list[0].id"

  # 最终发布请求（使用前面提取的所有变量）
  method: POST
  url: /api/publish/batch
  json:
    materialId: "${get_material_list.data.list[0].id}"
    accountId: "${get_author_accounts.data.list[0].id}"
  expected_status: 200
  expected_response:
    code: 0

  # 最终验证步骤检查发布列表中是否存在刚发布的数据
  verify:
    url: /api/publish/list
    method: POST
    json:
      page: 1
      size: 10
    check_exists:
      materialId: "${publish.materialId}"
```

### 代码修改范围

| 文件 | 修改方式 | 说明 |
|------|----------|------|
| `tests/star_digi+/test_star_api.py` | 修改 | 添加 `pre_steps` 处理逻辑、变量提取替换 |
| `util/api_client.py` | 兼容扩展 | `request_and_assert` 返回 response 以供提取数据 |
| `testdata/star_digi+/content_publish/` | 新增 | 为每个接口单独生成测试用例 |
| `testdata/star_digi+/content_publish/e2e_business_flow.yaml` | 新增 | 完整端到端业务流程测试用例 |
| `pytest.ini` | 修改 | 添加 `content_publish` marker |

### 核心处理流程

```
1. 测试用例开始执行
2. 如果有 pre_steps → 按顺序依次执行：
   a. 变量替换（使用前面步骤提取的值）
   b. 添加 star-token 认证头
   c. 调用 request_and_assert
   d. 根据 extract 配置从响应提取变量存入上下文
3. 对主请求进行变量替换（使用所有前置步骤提取的变量）
4. 执行主请求，进行断言
5. 如果有 verify 配置 → 执行验证步骤检查结果
6. 测试完成
```

### 变量替换规则

变量替换支持：
- `json` 对象中的字符串值替换
- `params` 字典中的字符串值替换
- `data` 中的字符串值替换
- 支持嵌套对象中深层替换
- 整个字符串是占位符 → 保留原始类型（数字/字符串）
- 字符串包含占位符 → 替换后仍为字符串

### 错误处理

- `pre_steps` 中任意一步失败 → 整个测试立即失败
- 占位符引用不存在的变量 → 测试失败，提示清晰错误
- JSONPath 提取失败（路径不存在） → 测试失败，提示清晰错误

## 测试用例规划

### 1. 每个接口单独测试（遵循现有方法论）

每个接口一个 YAML 文件，包含：
- 基础场景（必填参数）
- 单个参数独立测试
- 边界测试（page=0, size=0, size=10000）
- 错误参数测试

| 接口 | YAML 文件 |
|------|-----------|
| 新建素材库文件夹 | `create_folder.yaml` |
| 上传素材 | `upload_material.yaml` |
| 获取素材列表 | `get_material_list.yaml` |
| 获取发布达人（授权账户）列表 | `get_publisher_list.yaml` |
| 批量发布 | `batch_publish.yaml` |
| 获取发布列表 | `get_publish_list.yaml` |

### 2. 完整端到端测试

一个 YAML 文件 `e2e_business_flow.yaml`，包含一个完整链式调用测试用例。

## 依赖项

无需新增 Python 依赖，使用标准库即可实现简单 JSONPath。

## 成功标准

1. 所有单个接口测试通过
2. 完整端到端链式调用测试通过
3. 不影响现有测试用例的运行
4. 错误提示清晰，便于调试
