# 素材发布完整业务流程端到端测试实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现支持链式调用的端到端业务流程自动化测试，支持创建文件夹 → 上传素材 → 查询素材 → 查询授权账户 → 发布 → 验证发布列表完整流程。

**Architecture:** 在现有数据驱动测试架构基础上扩展，增加 `pre_steps` 前置步骤支持，使用 JSONPath 从先前响应提取变量，占位符替换到后续请求参数中。保持向后兼容，不影响现有单接口测试用例。

**Tech Stack:** Python 3.x, Pytest, YAML, requests, JSONPath（简化实现）

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/star_digi+/test_star_api.py` | 修改 | 增加 pre_steps 处理、变量提取、占位符替换逻辑 |
| `pytest.ini` | 修改 | 添加 `content_publish` marker |
| `testdata/star_digi+/content_publish/create_folder.yaml` | 新建 | 创建文件夹接口独立测试用例 |
| `testdata/star_digi+/content_publish/upload_material.yaml` | 新建 | 上传素材接口独立测试用例 |
| `testdata/star_digi+/content_publish/get_material_list.yaml` | 新建 | 获取素材列表接口独立测试用例 |
| `testdata/star_digi+/content_publish/get_publisher_list.yaml` | 新建 | 获取发布达人（授权账户）列表接口独立测试用例 |
| `testdata/star_digi+/content_publish/batch_publish.yaml` | 新建 | 批量发布接口独立测试用例 |
| `testdata/star_digi+/content_publish/get_publish_list.yaml` | 新建 | 获取发布列表接口独立测试用例 |
| `testdata/star_digi+/content_publish/e2e_business_flow.yaml` | 新建 | 完整端到端业务流程测试用例 |

---

## Tasks

### Task 1: 添加 content_publish marker 到 pytest.ini

**Files:**
- Modify: `pytest.ini`

- [ ] **Step 1: Read current pytest.ini**

- [ ] **Step 2: Add content_publish marker to [pytest] section**

```ini
[pytest]
addopts = --alluredir=output/allure-results --html=output/report.html --self-contained-html
testpaths = tests/
python_files = test_*.py
console_output_encoding = utf-8
reruns = 1
markers =
    login: login module tests
    monitor: monitor module tests
    monitor_center: monitor_center module tests
    workbench: workbench module tests
    content_publish: content_publish module tests
```

- [ ] **Step 3: Commit changes**

```bash
git add pytest.ini
git commit -m "feat: add content_publish marker to pytest.ini"
```

### Task 2: 实现变量提取和占位符替换功能到 test_star_api.py

**Files:**
- Modify: `tests/star_digi+/test_star_api.py`

- [ ] **Step 1: Read current file content**

- [ ] **Step 2: Add helper functions for JSONPath extraction and variable substitution**

Add after `load_all_test_data()` function:

```python
def extract_by_jsonpath(obj: dict, path: str):
    """
    简化版 JSONPath 提取
    支持: data.id, data.list[0].id, data.items[1].name
    """
    parts = path.split('.')
    current = obj
    for part in parts:
        if '[' in part and ']' in part:
            # 处理数组索引: list[0]
            name_part, index_part = part.split('[', 1)
            index = int(index_part.rstrip(']'))
            if name_part:
                current = current[name_part]
            current = current[index]
        else:
            current = current[part]
    return current
```

```python
import re
import string

def substitute_variables(obj, context: dict):
    """
    递归替换对象中的占位符 ${step.path}
    支持替换整个值或字符串中的部分占位符
    """
    pattern = re.compile(r'\$\{([^}]+)\}')

    if isinstance(obj, str):
        # 整个字符串就是一个占位符 → 返回原始类型
        match = pattern.fullmatch(obj)
        if match:
            path = match.group(1)
            return get_variable_from_context(path, context)
        # 字符串中包含占位符 → 替换后保持字符串
        def replace_func(match):
            path = match.group(1)
            val = get_variable_from_context(path, context)
            return str(val)
        return pattern.sub(replace_func, obj)
    elif isinstance(obj, dict):
        return {k: substitute_variables(v, context) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_variables(item, context) for item in obj]
    else:
        # 数字/布尔/null 不替换
        return obj
```

```python
def get_variable_from_context(path: str, context: dict):
    """
    从上下文获取变量，路径格式: step_name.json.path
    """
    # context 格式: {step_name: response_obj}
    # path: create_folder.data.id → split → step_name=create_folder, sub_path=data.id
    first_dot = path.find('.')
    if first_dot == -1:
        return context[path]
    step_name = path[:first_dot]
    sub_path = path[first_dot+1:]
    resp = context[step_name]
    return extract_by_jsonpath(resp.json(), sub_path)
```

- [ ] **Step 3: Modify test_star_api function to handle pre_steps**

Modify `test_star_api` function to:

```python
@pytest.mark.parametrize("test_case", PARAM_CASES)
def test_star_api(test_case, global_token):
    headers = test_case.get("headers", {}).copy()
    headers["star-token"] = f"Bearer {global_token}"

    # 处理 pre_steps 前置步骤
    context = {}  # {step_name: response}
    pre_steps = test_case.get("pre_steps", [])
    for pre_step in pre_steps:
        # 替换变量
        step_headers = pre_step.get("headers", {}).copy()
        step_headers["star-token"] = f"Bearer {global_token}"

        step_method = pre_step["method"]
        step_url = f"{BASE_URL2.rstrip('/')}/{pre_step['url'].lstrip('/')}"
        step_params = substitute_variables(pre_step.get("params"), context)
        step_data = substitute_variables(pre_step.get("data"), context)
        step_json = substitute_variables(pre_step.get("json"), context)
        step_expected_status = pre_step.get("expected_status", 200)
        step_expected_response = pre_step.get("expected_response")
        step_max_retries = pre_step.get("max_retries")

        resp = request_and_assert(
            name=f"{test_case['name']} - 前置: {pre_step['name']}",
            method=step_method,
            url=step_url,
            headers=step_headers,
            timeout=TIMEOUT,
            expected_status=step_expected_status,
            expected_response=step_expected_response,
            params=step_params,
            data=step_data,
            json=step_json,
            max_retries=step_max_retries,
            verify=False
        )
        # 保存响应到上下文供后续提取
        context[pre_step["name"]] = resp

    # 主请求变量替换
    params = substitute_variables(test_case.get("params"), context)
    data = substitute_variables(test_case.get("data"), context)
    json_body = substitute_variables(test_case.get("json"), context)

    url = f"{BASE_URL2.rstrip('/')}/{test_case['url'].lstrip('/')}"
    request_and_assert(
        name=test_case["name"],
        method=test_case["method"],
        url=url,
        headers=headers,
        timeout=TIMEOUT,
        expected_status=test_case["expected_status"],
        expected_response=test_case.get("expected_response"),
        params=params,
        data=data,
        json=json_body,
        max_retries=test_case.get("max_retries"),
        verify=False
    )
```

- [ ] **Step 4: Run existing tests to verify no regression**

```bash
pytest -m "not content_publish" -v --tb=short
```

Expected: All existing tests pass.

- [ ] **Step 5: Commit changes**

```bash
git add tests/star_digi+/test_star_api.py
git commit -m "feat: add pre_steps support with variable extraction and substitution"
```

### Task 3: Generate create_folder.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/create_folder.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/新建素材库文件夹_OpenAPI.json`**

- [ ] **Step 2: Create YAML test cases following project methodology**

Include:
- 基础场景：正常创建文件夹
- 边界测试：文件夹名称为空字符串
- 边界测试：文件夹名称超长

- [ ] **Step 3: Save file and commit**

```bash
git add testdata/star_digi+/content_publish/create_folder.yaml
git commit -m "test: add create_folder test cases"
```

### Task 4: Generate upload_material.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/upload_material.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/问我上传素材_OpenAPI.json`**

- [ ] **Step 2: Create YAML test cases**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/upload_material.yaml
git commit -m "test: add upload_material test cases"
```

### Task 5: Generate get_material_list.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/get_material_list.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/get_material_list_OpenAPI.json`**

- [ ] **Step 2: Create YAML test cases following methodology:
  - 基础场景：只传分页参数
  - 按文件夹筛选：folderId 筛选
  - 按名称筛选：name 关键词筛选
  - 分页边界测试：page=0, size=0, size=10000**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/get_material_list.yaml
git commit -m "test: add get_material_list test cases"
```

### Task 6: Generate get_publisher_list.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/get_publisher_list.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/获取发布达人数据_OpenAPI (1).json`**

- [ ] **Step 2: Create YAML test cases**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/get_publisher_list.yaml
git commit -m "test: add get_publisher_list test cases"
```

### Task 7: Generate batch_publish.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/batch_publish.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/批量发布_OpenAPI.json`**

- [ ] **Step 2: Create YAML test cases**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/batch_publish.yaml
git commit -m "test: add batch_publish test cases"
```

### Task 8: Generate get_publish_list.yaml 测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/get_publish_list.yaml`

- [ ] **Step 1: Read OpenAPI spec from `api/content_publish/获取发布列表_OpenAPI.json`**

- [ ] **Step 2: Create YAML test cases**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/get_publish_list.yaml
git commit -m "test: add get_publish_list test cases"
```

### Task 9: Create complete e2e_business_flow.yaml 端到端测试用例

**Files:**
- Create: `testdata/star_digi+/content_publish/e2e_business_flow.yaml`

- [ ] **Step 1: Create YAML with pre_steps using the design format**

Use the structure from design doc:
```yaml
- name: "素材发布 - 完整端到端业务流程测试"
  description: "创建文件夹 → 上传素材 → 查询素材 → 查询授权账户 → 发布 → 验证发布列表存在"
  pre_steps:
    - name: "create_folder"
      method: POST
      url: /api/your/path/to/create-folder  # 从 OpenAPI 获取真实路径
      headers:
        Content-Type: application/json
      json:
        name: "auto_test_folder"
      expected_status: 200
      expected_response:
        code: 0
      extract:
        folder_id: "data.id"

    - name: "upload_material"
      method: POST
      url: /api/your/path/to/upload
      json:
        folderId: "${create_folder.data.id}"
        name: "test_material.jpg"
      expected_status: 200
      expected_response:
        code: 0
      extract:
        material_id: "data.id"

    - name: "get_material_list"
      method: POST
      url: /api/your/path/to/list
      json:
        page: 1
        size: 10
      expected_status: 200
      expected_response:
        code: 0

    - name: "get_publisher_list"
      method: POST
      url: /api/your/path/to/accounts
      json:
        page: 1
        size: 10
      expected_status: 200
      expected_response:
        code: 0

  # Final publish request
  method: POST
  url: /api/your/path/to/batch-publish
  json:
    materialId: "${get_material_list.data.list[0].id}"
    accountId: "${get_publisher_list.data.list[0].id}"
  expected_status: 200
  expected_response:
    code: 0
  max_retries: 1
```

- [ ] **Step 2: Verify all paths from OpenAPI are correct**

- [ ] **Step 3: Save and commit**

```bash
git add testdata/star_digi+/content_publish/e2e_business_flow.yaml
git commit -m "test: add complete e2e business flow test case"
```

### Task 10: Run all content_publish tests and verify

**Files:**
- Test run: all content_publish tests

- [ ] **Step 1: Run all tests in content_publish module**

```bash
pytest -m content_publish -v
```

- [ ] **Step 2: Fix any issues found**

- [ ] **Step 3: Run full test suite to confirm no regression**

```bash
pytest -v
```

