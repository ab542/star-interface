import pytest
import requests
import yaml
from pathlib import Path
from loguru import logger
from config.config import BASE_URL2, TIMEOUT, PROJECT_ID
from util.api_client import request_and_assert
import string
# 一次性加载 testdata/star_digi+ 目录下所有 yaml 文件
# 并根据文件所在目录自动添加 pytest marker
def load_all_test_data(dir_path="testdata/star_digi+"):
    files = sorted(Path(dir_path).rglob("*.yaml"))
    parametrized_cases = []
    for f in files:
        # 从文件路径推断模块名称（例如 login/data_login.yaml => module=login）
        module = f.parent.name
        marker = getattr(pytest.mark, module, pytest.mark.generic)
        raw = f.read_text(encoding="utf-8")          # 一次性读完
        tpl = string.Template(raw)
        content = tpl.safe_substitute(projectId=PROJECT_ID)
        for doc in yaml.safe_load_all(content):      # ← 用替换后的字符串
            if not doc:
                continue
            if isinstance(doc, list):
                for case in doc:
                    parametrized_cases.append(pytest.param(case, marks=marker, id=case.get("name")))
            else:
                parametrized_cases.append(pytest.param(doc, marks=marker, id=doc.get("name")))
    return parametrized_cases

PARAM_CASES = load_all_test_data()

@pytest.mark.parametrize("test_case", PARAM_CASES)
def test_star_api(test_case, global_token):          # ① 注入 fixture
    # headers = HEADERS.copy()                         # ② 复制默认头
    headers = test_case.get("headers", {}).copy()    # ② 复制用例头
    headers["star-token"] = f"Bearer {global_token}"      # ③ 加 Bearer token header
    # 正确拼接 URL，处理斜杠避免双斜杠
    url = f"{BASE_URL2.rstrip('/')}/{test_case['url'].lstrip('/')}"
    request_and_assert(
        name=test_case["name"],
        method=test_case["method"],
        url=url,
        headers=headers,                           # ④ 使用新 headers
        timeout=TIMEOUT,
        expected_status=test_case["expected_status"],
        expected_response=test_case.get("expected_response"),
        params=test_case.get("params"),
        data=test_case.get("data"),
        json=test_case.get("json"),
        max_retries=test_case.get("max_retries"),
        verify=False
    )