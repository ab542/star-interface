# api_client 接口断言判断逻辑分析

## 文件位置
`util/api_client.py` - 统一API请求客户端，包含**多层级断言验证**机制

---

## 断言层级结构（从底层到业务）

`request_and_assert()` 函数采用**分层断言**设计，按顺序执行：

| 层级 | 顺序 | 检查点 | 触发条件 | 失败行为 |
|------|------|--------|----------|----------|
| 1. 网络层 | 1 | 网络请求/超时异常 | 请求抛出异常 | 直接失败 |
| 2. 异常关键字层 | 2 | 数据库异常关键字 | 响应文本包含 `数据库`, `SQL`, `MySQL`, `PostgreSQL`, `ORA-` 等 | 失败 |
| 3. 系统异常层 | 3 | 系统异常字符串 | 响应文本包含 `系统异常` | 失败 |
| 4. 业务字段断言层 | 4 | 期望响应字段精确匹配 | YAML配置了 `expected_response` | 字段缺失或值不匹配 → 失败 |
| 5. 业务消息层 | 5 | `msg` 字段非空即失败 | `fail_on_msg=True` **且**预期 `code` 为 `None` 或 `0` | `msg` 非空且不是成功短语 → 失败 |

---

## 各层级断言详解

### 1. 网络层断言

```python
except requests.RequestException as e:
    logger.error(... 网络/超时错误 ...)
    pytest.fail(str(e))
```

- **作用**：捕获网络异常、连接超时、DNS解析失败等
- **日志**：记录详细请求信息到 `logs/failure.log`

---

### 2. 数据库异常关键字检测

```python
DB_ERROR_KEYWORDS = {"数据库", "DB Error", "SQL", "ORA-", "MySQL", "PostgreSQL"}
if any(k in resp.text for k in DB_ERROR_KEYWORDS):
    pytest.fail("Database anomaly detected")
```

- **作用**：检测数据库层面未被处理的异常
- **原理**：很多框架会将数据库错误信息直接返回给前端，通过关键字匹配快速捕获
- **优点**：不需要解析JSON就能发现问题，覆盖各种异常输出形式

---

### 3. 系统异常检测

```python
if "系统异常" in resp.text:
    pytest.fail("系统异常")
```

- **作用**：捕获服务端未处理的全局异常
- **原理**：中文系统通常会返回"系统异常"提示信息

---

### 4. 期望响应字段验证

```python
if expected_response is not None:
    for key, expected_value in expected_response.items():
        if key not in body → fail
        if actual_value != expected_value → fail
```

- **作用**：对指定JSON字段进行精确值匹配
- **本项目约定**：`expected_response: {code: 0}` 表示业务成功
- **示例**：
  ```yaml
  expected_response:
    code: 0        # 验证业务码为0
    status: 1      # 同时验证status字段为1
  ```

---

### 5. 业务消息 `msg` 异常检测

```python
# 如果预期 code != 0 说明是预期的错误响应，此时 msg 应有错误信息，跳过检查
expected_code = None
if expected_response is not None and 'code' in expected_response:
    expected_code = expected_response['code']
if fail_on_msg and (expected_code is None or expected_code == 0):
    # 检查 msg 字段
    if msg_val.strip().lower() not in ("success", "ok", "0", "true"):
        pytest.fail(...)
```

#### 核心逻辑：

| 场景 | `expected_code` | `fail_on_msg` | 行为 |
|------|----------------|---------------|------|
| 正常成功场景 | `0` | `True` (默认) | 检查msg，非成功短语 → 失败 |
| 预期错误场景 | `400` | `True` | **跳过检查**（因为错误本来就会有msg） |
| 未指定code | `None` | `True` | 执行检查 |

#### 白名单：
以下 `msg` 值视为成功，不会触发失败：
- `"success"`
- `"ok"`
- `"0"`
- `"true"`（不区分大小写）

---

## 特殊设计说明

### 为什么不做 HTTP 状态码断言？

代码第126-129行：**HTTP状态码断言被注释掉了**

原因：
- 本项目所有请求都返回 `HTTP 200`，通过 `code` 业务码区分成功/失败
- HTTP状态码始终是200，断言没有意义
- 如果你的项目不是这种设计，可以取消注释开启状态码断言

### 为什么分层顺序是这样？

1. **先做关键字检测，再做字段断言**：因为如果已经出现"系统异常"或"数据库错误"，说明请求已经失败，不需要继续断言
2. **字段断言在 msg 检测之前**：先验证期望字段，再做msg检查，保证逻辑顺序正确
3. **预期错误场景跳过msg检测**：这是针对本项目错误处理模式的优化，错误信息放在msg中是正常的

---

## 附加功能

### 响应时间分类监控

```python
def get_speed_label(elapsed):
    if elapsed < 200:      return "🟢快"
    elif elapsed < 500:    return "🟡较快"
    elif elapsed < 1000:   return "🟠一般"
    else:                  return "🔴慢"
```

分类标准（本项目约定）：

| 响应时间 | 标签 | 评价 |
|---------|------|------|
| `< 200ms` | 🟢快 | 优秀 |
| `200ms - 500ms` | 🟡较快 | 良好 |
| `500ms - 1000ms` | 🟠一般 | 可接受 |
| `> 1000ms` | 🔴慢 | 需要优化 |

响应时间会记录在日志中，便于性能分析。

---

### 日志分离

- ✅ 成功请求 → `logs/success.log`
- ❌ 失败请求 → `logs/failure.log`

便于问题定位：
- 只看失败日志 → 快速定位错误
- 成功日志保留完整请求响应 → 成功用例也能追溯

### 长响应截断

```python
if max_response_lines is not None and total_lines > max_response_lines:
    只显示前 N 行，标注被截断
```

默认值：`max_response_lines = 10`

作用：避免大响应（如返回上千条数据）占满日志，影响可读性。

---

## 重试机制

```python
retry = Retry(
    total=max_retries,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],  # 只对5xx错误重试
    allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE'])
)
```

- **默认重试次数**：`DEFAULT_MAX_RETRIES` 来自配置
- **单个用例可覆盖**：YAML中配置 `max_retries: 1` 即可覆盖
- **只重试5xx错误**：4xx错误（参数错误、认证失败）不会重试

---

## 本项目 YAML 配置示例

```yaml
# 成功场景
- name: "基础查询"
  method: POST
  url: /api/media/monitor/list
  headers:
    Content-Type: application/json
  json:
    page: 1
    size: 10
  expected_status: 200
  expected_response:
    code: 0
  max_retries: 3

# 预期参数错误场景
- name: "页码为0边界测试"
  method: POST
  url: /api/media/monitor/list
  headers:
    Content-Type: application/json
  json:
    page: 0
    size: 10
  expected_status: 200
  expected_response:
    code: 400
  max_retries: 1
```

- `expected_status: 200` - HTTP状态码始终为200
- `expected_response.code: 0` - 预期业务成功
- `expected_response.code: 400` - 预期参数错误，此时会自动跳过msg检查
- `max_retries: 1` - 边界错误场景不需要重试

---

## 优点总结

1. **分层防御**：从网络到业务多层检测，不放过任何异常
2. **智能跳过**：预期错误场景自动跳过msg检查，符合实际业务
3. **可配置性**：每个用例可以独立配置 `max_retries`、`expected_response`
4. **可观测性**：日志分离+响应时间分类+长响应截断，便于排障
5. **自动重试**：对5xx服务端错误自动重试，避免偶发失败

## 可改进点

| 改进点 | 说明 |
|--------|------|
| JSON Schema验证 | 目前只做指定字段匹配，可以增加完整JSON Schema验证 |
| 包含断言 | 目前只做精确匹配，可以增加 `contains` 断言支持子字符串包含 |
| 正则断言 | 支持对字段用正则匹配，适应动态值场景 |
