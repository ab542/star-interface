# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**`star_interface`** - API automation testing for the Star Digi+ advertising platform (`https://star.digiplus-intl.com`).

This project uses **Pytest** with a **data-driven testing architecture** - all test cases are defined in YAML files, and generic test code executes them.

OpenAPI/Swagger specs are stored in `api/` directory, and test cases are auto-generated from them following the project's testing methodology.

## Commands

### Setup
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Create local config (will not be committed to git)
cp config/local_config.py.example config/local_config.py
# Edit config/local_config.py to set your credentials
```

### Running Tests
```bash
# Run all tests (uses default options from pytest.ini)
pytest

# Run specific test file
pytest tests/star_digi+/test_star_api.py

# Run tests by module (auto-markers based on directory)
pytest -m login        # Run login module tests
pytest -m monitor      # Run monitor module tests
pytest -m monitor_center # Run monitor_center module tests
pytest -m workbench    # Run workbench module tests

# Run a single specific test by name
pytest -k "监控中心 - 获取监控账户列表-只传分页参数"

# Run with Allure and HTML reports
pytest --alluredir=output/allure-results --html=output/report.html --self-contained-html

# View Allure report
allure serve output/allure-results
```

## Project Structure

```
star_interface/
├── api/                # OpenAPI/Swagger JSON files (source for test generation)
│   ├── README.txt              # Instructions for adding new APIs
│   └── <module>/               # OpenAPI files grouped by module
├── config/              # Configuration
│   ├── config.py               # BASE_URL, TIMEOUT, default HEADERS, default credentials
│   └── local_config.py.example # Local config template (git-ignored)
├── tests/
│   ├── conftest.py      # Pytest fixtures (session-scoped login token)
│   └── star_digi+/
│       └── test_star_api.py    # Main parameterized test runner with auto-markers
├── testdata/
│   └── star_digi+/      # YAML test cases organized by module (directory = pytest marker)
│       ├── login/
│       ├── monitor/
│       ├── monitor_center/     # Auto-generated test cases (one YAML per API endpoint)
│       └── workbench/
├── util/
│   └── api_client.py    # HTTP client with retry/logging/multi-layer assertion
├── docs/                # Technical documentation and analysis
├── logs/                # Success/failure logs (gitignored)
├── output/              # Test reports (gitignored)
├── requirements.txt
└── pytest.ini           # Pytest default configuration (markers, addopts, encoding)
```

## Architecture

### Key Components

**1. `util/api_client.py`** - Universal API client with multi-layered assertion:
- Sends HTTP requests with automatic retries (3 retries for 5xx errors by default)
- **Layer 1**: Catches network/timeout exceptions
- **Layer 2**: Detects database error keywords ("数据库", "SQL", "MySQL", etc.)
- **Layer 3**: Detects "系统异常" string
- **Layer 4**: Exact field matching via `expected_response`
- **Layer 5**: `fail_on_msg` - fails if `msg` is non-empty and not a success phrase (skipped when expected `code != 0`)
- Tracks response time and categorizes by speed
- Logs requests/responses via loguru (separate success/failure logs in `logs/`)
- Per-request `max_retries` override via YAML config

**Assertion rule for error scenarios**:
- When `expected_response: {code: 400}` (expected parameter validation error), `fail_on_msg` is automatically skipped
- This allows error messages to exist in `msg` without causing test failure

**2. `tests/conftest.py`** - Provides `global_token` session-scoped fixture:
- Logs in **once** before all tests run
- Shares the authentication token with all test cases
- Avoids repeated login for every test
- Authentication uses `star-token: Bearer <token>` header

**3. `tests/star_digi+/test_star_api.py`** - Parameterized test runner:
- Auto-scans all `*.yaml` files in `testdata/star_digi+/`
- Auto-adds **pytest markers based on directory**: `login/` → `@pytest.mark.login`
- Supports YAML variable substitution: `$projectId` → replaced from config
- Injects global token into all requests automatically (`star-token` header)

**4. `api/` directory** - OpenAPI source files:
- Stores original OpenAPI/Swagger JSON for each API endpoint
- One module per subdirectory
- Used as source for auto-generating YAML test cases

**5. `config/`** - Configuration management:
- `config.py`: Default configuration with base URL, timeout, retry count
- `local_config.py`: Optional local override (git-ignored) for custom credentials
- Copy `local_config.py.example` to create your local config

**6. YAML Test Data** - Each API endpoint has one YAML file with multiple test cases:
```yaml
- name: "模块 - 接口名称-只传分页参数"
  method: POST
  url: /api/path/to/endpoint
  headers:
    Content-Type: application/json
  json:
    page: 1
    size: 10
  expected_status: 200
  expected_response:
    code: 0
  max_retries: 3  # Optional, override default max retries
```

- One test case per scenario
- Each filter parameter gets its own independent test case (to isolate which filter fails)
- Include: base scenarios + single parameter tests + boundary tests + special value tests
- `star-token` is automatically injected by test runner - do NOT include in YAML

YAML supports variable substitution for `$projectId`:
```yaml
json:
  projectId: $projectId  # Will be replaced from config.PROJECT_ID
```

**7. `pytest.ini`** - Pre-configured defaults:
```ini
[pytest]
addopts = --alluredir=output/allure-results --html=output/report.html --self-contained-html
testpaths = tests/
python_files = test_*.py
console_output_encoding = utf-8
reruns = 1
# markers (auto-registered): login, monitor, monitor_center, workbench
```

### Response Time Categories

| Range | Category | Action |
|-------|----------|--------|
| `< 200ms` | Very Fast | No action needed |
| `200ms - 500ms` | Fast | Good for normal business APIs |
| `500ms - 1000ms` | Normal | Acceptable for complex queries |
| `1000ms - 2000ms` | Slow | Investigate potential bottlenecks |
| `> 2000ms` | Very Slow | Recommend optimization |

## Testing Methodology

When adding new test cases from OpenAPI, follow this methodology:

### 1. Test Case Generation Strategy

**One API endpoint → one YAML file → multiple test cases**

**Test case categories** (always include all):
- **基础场景** (2): Only required pagination params, full parameter combination
- **数组类型参数筛选** (N): One test case per array parameter (with realistic example values)
- **整数枚举类型参数** (N × 2): One test case per enum option (0/1, open/closed, enabled/disabled)
- **字符串类型参数** (N): One test case per option value
- **边界测试** (3): `page=0`, `size=0`, `size=10000` (expect `code: 400` when API validates)
- **特殊值测试** (N+): Empty arrays, empty string, missing optional parameters

**Core Principle**: **Each filter parameter must have its own independent test case**. This ensures you can quickly identify which filter is broken when a test fails.

### 2. Functional Testing
- Verify HTTP status code is correct (always 200 in this project)
- Verify response format matches expectations
- Verify business `code` field matches expected value
- Verify business logic works as expected

### 3. Boundary Conditions
- Test minimum/maximum values for numeric parameters
- Test empty strings, null values, missing parameters
- Test illegal data types (string where number expected)

### 4. Error Handling
- Verify correct error codes are returned
- Verify error messages are clear and meaningful
- Verify system exceptions ("系统异常") are properly handled
- Verify business logic errors are correctly reported

### 5. Interface Dependency Handling

When one API's parameter requires data from another API:

**Recommended approach (Test Data Pre-preparation)**:
1. Run the dependency API test to get real valid IDs
2. Update the dependent API's YAML with these real IDs
3. Keep static data - no framework changes needed
4. This is the most common approach in enterprise automation when test data is stable

**Alternative approach** (if data changes frequently): Extend YAML to support `pre_steps` with JSONPath extraction

### 6. Performance
- GET requests should respond in < 500ms
- POST requests should respond in < 1 second
- Slower responses should be investigated for optimization

### 7. Security
- Verify authentication/authorization is enforced
- Test for SQL injection and XSS vulnerabilities
- Verify sensitive data is encrypted in transit

## Adding New Tests from OpenAPI

1. Put the OpenAPI JSON file in `api/<module>/` directory
2. Follow the generation methodology above to create YAML
3. Create YAML file at `testdata/star_digi+/<module>/<endpoint_name>.yaml`
   - Directory name determines the pytest marker automatically
   - Add the marker to `pytest.ini`
4. Follow the YAML format: one entry per test case, add classification comment at top
5. For interface dependencies: get real IDs from dependency API and hardcode them
6. Include normal cases, boundary cases, and error cases
7. Add optional `max_retries`: `3` for normal cases, `1` for boundary/error cases
8. Run `pytest -m <module>` to test only your new module

The test runner is already parameterized to run all test cases from the YAML file - **no Python code needs to be added** for new test cases.


