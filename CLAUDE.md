# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**`star_interface`** - API automation testing for the Star Digi+ advertising platform (`https://star.digiplus-intl.com`).

This project uses **Pytest** with a **data-driven testing architecture** - all test cases are defined in YAML files, and generic test code executes them.

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
pytest -m workbench    # Run workbench module tests

# Run with Allure and HTML reports
pytest --alluredir=output/allure-results --html=output/report.html

# View Allure report
allure serve output/allure-results
```

## Project Structure

```
star_interface/
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
│       │   └── data_login.yaml
│       ├── monitor/
│       └── workbench/
├── util/
│   └── api_client.py    # HTTP client with retry/logging/assertion
├── logs/                # Success/failure logs (gitignored)
├── output/              # Test reports (gitignored)
├── requirements.txt
└── pytest.ini           # Pytest default configuration
```

## Architecture

### Key Components

**1. `util/api_client.py`** - Universal API client that:
- Sends HTTP requests with automatic retries (3 retries for 5xx errors by default)
- Validates HTTP status codes
- Detects error keywords in responses ("系统异常", database errors)
- Tracks response time and categorizes by speed
- Logs requests/responses via loguru (separate success/failure logs)
- Per-request `max_retries` override via YAML config

**2. `tests/conftest.py`** - Provides `global_token` session-scoped fixture:
- Logs in **once** before all tests run
- Shares the authentication token with all test cases
- Avoids repeated login for every test
- Authentication uses `star-token: Bearer <token>` header

**3. `tests/star_digi+/test_star_api.py`** - Parameterized test runner:
- Auto-scans all `*.yaml` files in `testdata/star_digi+/`
- Auto-adds **pytest markers based on directory**: `login/` → `@pytest.mark.login`
- Supports YAML variable substitution: `$projectId` → replaced from config
- Injects global token into all requests automatically

**4. `config/`** - Configuration management:
- `config.py`: Default configuration with base URL, timeout, retry count
- `local_config.py`: Optional local override (git-ignored) for custom credentials
- Copy `local_config.py.example` to create your local config

**5. YAML Test Data** - Each test case is defined in YAML:
```yaml
- name: "Login - Valid Credentials"
  method: POST
  url: /api/media/advertiser/login
  headers:
    Content-Type: application/json
  json:
    email: example@company.com
    password: "password"
  expected_status: 200
  expected_response:
    code: 0
    msg: "success"
  max_retries: 3  # Optional, override default max retries
```

YAML supports variable substitution for `$projectId`:
```yaml
json:
  projectId: $projectId  # Will be replaced from config.PROJECT_ID
```

**6. `pytest.ini`** - Pre-configured defaults:
```ini
[pytest]
addopts = --alluredir=output/allure-results --html=output/report.html --self-contained-html
testpaths = tests/
python_files = test_*.py
console_output_encoding = utf-8
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

When adding new test cases, follow this testing methodology:

### 1. Functional Testing
- Verify HTTP status code is correct
- Verify response format matches expectations
- Verify data fields and values are correct
- Verify business logic works as expected

### 2. Boundary Conditions
- Test minimum/maximum values for numeric parameters
- Test min/max length for strings
- Test empty strings, null values, missing parameters
- Test illegal data types (string where number expected)

### 3. Error Handling
- Verify correct error codes are returned
- Verify error messages are clear and meaningful
- Verify system exceptions ("系统异常") are properly handled
- Verify business logic errors are correctly reported

### 4. Performance
- GET requests should respond in < 500ms
- POST requests should respond in < 1 second
- Slower responses should be investigated for optimization

### 5. Security
- Verify authentication/authorization is enforced
- Test for SQL injection and XSS vulnerabilities
- Verify sensitive data is encrypted in transit

## Adding New Tests

1. Create or edit the YAML file in `testdata/star_digi+/<module>/`
   - Directory name determines the pytest marker automatically
2. Follow the existing YAML format
3. Use `$projectId` placeholder for project ID
4. Include normal cases, boundary cases, and error cases
5. Add optional `max_retries` to override default retry count
6. Run `pytest -m <module>` to test only your new module

The test runner is already parameterized to run all test cases from the YAML file - **no Python code needs to be added** for new test cases.
