# Star Interface

Star Digi+ 广告平台的 API 自动化测试框架，基于 Pytest 数据驱动测试架构。

## 📋 项目简介

本项目采用 **数据驱动测试** 思想，所有测试用例以 YAML 格式定义，通用测试代码执行所有用例。

特点：
- ✅ YAML 定义测试用例，无需修改 Python 代码添加用例
- ✅ YAML 支持变量替换，方便配置项目ID
- ✅ 自动重试失败请求（5xx 错误重试 3 次）
- ✅ 响应时间自动分类统计
- ✅ 自动检测响应中的系统异常关键词
- ✅ Session 级别的登录复用，无需每个测试重新登录
- ✅ 本地配置覆盖，账号信息不提交到 git
- ✅ Allure + HTML 双报告输出

## 🚀 环境搭建

```bash
# 克隆项目
git clone git@github.com:ab542/star-interface.git
cd star-interface

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# （可选）配置本地账号信息
cp config/local_config.py.example config/local_config.py
# 编辑 config/local_config.py 修改为你的账号信息
```

## 🏃 运行测试

```bash
# 运行所有测试 (pytest.ini 已配置默认参数)
pytest

# 运行指定测试文件
pytest tests/star_digi+/test_star_api.py

# 按模块运行测试（自动生成 markers，login 模块示例）
pytest -m login

# 生成 Allure 报告
pytest --alluredir=output/allure-results
allure serve output/allure-results

# 生成 HTML 报告
pytest --html=output/report.html --self-contained-html
```

## 📁 项目结构

```
star_interface/
├── config/              # 配置文件
│   ├── config.py               # 全局配置：BASE_URL、TIMEOUT、默认HEADERS
│   └── local_config.py.example # 本地配置示例（不提交到git）
├── tests/
│   ├── conftest.py      # Pytest fixtures (Session级登录token)
│   └── star_digi+/
│       └── test_star_api.py    # 参数化测试运行器
├── testdata/
│   └── star_digi+/      # YAML 测试用例（按模块分类）
│       ├── login/
│       ├── monitor/
│       └── workbench/
├── util/
│   └── api_client.py    # API 客户端 (请求+重试+断言+日志)
├── logs/                # 日志文件 (gitignore)
├── output/              # 测试报告 (gitignore)
└── pytest.ini           # Pytest 默认配置
```

## 🏗️ 架构说明

### api_client.py

通用 API 客户端，提供以下功能：
- 发送 HTTP 请求（支持 GET/POST 等方法）
- **5xx 错误自动重试**：默认重试 3 次，可在测试用例中单独配置 `max_retries`
- 自动验证 HTTP 状态码
- 自动检测响应中的错误关键词（"系统异常"等）
- 记录响应时间并按速度分类
- loguru 日志记录，成功失败分开存储

### YAML 测试用例格式

```yaml
- name: "登录 - 有效凭证"
  method: POST
  url: /api/media/advertiser/login
  headers:
    Content-Type: application/json
  json:
    email: user@example.com
    password: "password"
  expected_status: 200
  expected_response:
    code: 0
    msg: "success"
  max_retries: 3  # 可选，覆盖默认重试次数
```

### YAML 变量替换

测试运行器支持变量替换，可在 YAML 中使用 `$projectId` 占位符，会自动替换为配置文件中的 `PROJECT_ID`：

```yaml
json:
  projectId: $projectId
```

### conftest.py

提供 `global_token` fixture，**整个测试会话只登录一次**，获取的 token 给所有测试用例复用，避免重复登录。

### 配置说明

- `config.py`：默认配置，包含 `BASE_URL`、超时时间、重试次数、默认登录账号等
- `local_config.py`：**本地自定义配置**（可选），复制 `local_config.py.example` 创建，会覆盖默认配置。该文件已在 `.gitignore` 中，不会提交到 git

### 认证方式

所有 API 请求使用 `star-token` 请求头携带 Bearer token：
```
star-token: Bearer <token>
```

### test_star_api.py

参数化测试运行器：
- 自动扫描 `testdata/star_digi+` 目录下所有 YAML 文件
- 支持 YAML 变量替换 (`$projectId`)
- **自动添加 pytest markers**：根据**文件所在目录**自动按模块分类，`login/` 目录下的用例自动标记为 `login` marker，方便按模块运行测试
- 全局 token 自动注入到请求头

## ⏱️ 响应时间参考

| 耗时范围 | 评价 | 建议 |
|---------|------|------|
| `< 200ms` | 非常快 | 无需优化 |
| `200ms ~ 500ms` | 较快 | 常规业务接口优秀水平 |
| `500ms ~ 1000ms` | 正常 | 复杂业务接口可接受 |
| `1000ms ~ 2000ms` | 偏慢 | 建议排查 |
| `> 2000ms` | 慢 | 优化至 1 秒以内 |

## 📝 测试用例设计方法

### 设计思路

1. 熟悉业务，梳理业务逻辑和流程 → **场景法**，覆盖接口间业务关联
2. 针对具体接口细化分析测试点 → **等价类+边界值**，设计正常用例和异常用例
3. 关注业务异常流程

**测试思维 = 输入项（参数） + 业务规则**

### 边界测试点

- **数值范围**：最小值、最大值、超出边界、零值
- **字符串**：最小长度、最大长度、空字符串、特殊字符
- **日期时间**：最早/最晚日期、闰年、非法格式
- **集合数组**：空集合、单元素、满容量
- **权限控制**：未授权、最小权限、最大权限
- **网络负载**：并发、超时、网络异常
- **业务逻辑**：状态转换、金额/数量限制、时间窗口

## 📖 接口测试完整方法论

### 1. 功能测试
- 验证 HTTP 状态码正确
- 验证响应格式符合预期
- 验证数据字段和值正确
- 验证业务逻辑正确

### 2. 边界条件测试
- 参数边界值验证
- 空值/缺失字段处理
- 非法输入测试
- 大数据量处理验证

### 3. 异常处理测试
- 错误码和错误消息验证
- 数据库/系统异常处理
- 业务逻辑错误处理
- 错误信息需要清晰便于调试

### 4. 性能测试
- 响应时间：GET < 500ms，POST < 1s
- 吞吐量和并发测试
- 压力测试验证稳定性
- 资源消耗监控

### 5. 安全性测试
- 认证和授权验证
- SQL 注入/XSS 攻击防护测试
- 敏感数据加密传输
- CSRF 防护验证
- 越权访问测试

## 🔧 Git 常用命令

```bash
# 查看状态
git status

# 添加文件到暂存区
git add <file>

# 提交
git commit -m "描述你的改动"

# 推送到远程
git push

# 拉取最新代码
git pull

# 创建并切换分支
git checkout -b <branch-name>

# 切换分支
git checkout <branch-name>

# 查看分支
git branch

# 合并分支到当前分支
git merge <branch-name>

# 查看提交历史
git log
```

## ➕ 添加新测试

只需要在 `testdata/` 对应目录新增 YAML 文件，遵循现有格式即可：
1. 使用标准 YAML 格式定义测试用例
2. 可使用 `$projectId` 变量占位符，自动替换
3. 测试运行器会自动扫描加载所有测试用例
4. **不需要修改 Python 代码**

## ⚙️ 自定义配置

如需自定义登录账号或项目 ID：

```bash
# 复制本地配置示例
cp config/local_config.py.example config/local_config.py
```

然后编辑 `config/local_config.py` 修改你的配置：

```python
LOGIN_EMAIL = "your-email@company.com"
LOGIN_PASSWORD = "your-password"
PROJECT_ID = "your-project-id"
```

本地配置不会提交到 git，保证账号信息安全。

## 📄 许可证

MIT
