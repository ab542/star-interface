import pytest
import requests
import yaml
from pathlib import Path
from loguru import logger
from config.config import BASE_URL2, TIMEOUT, PROJECT_ID
from util.api_client import request_and_assert
import string
# 一次性加载 testdata/cartea 目录下所有 yaml 文件
def load_all_test_data(dir_path="testdata/star_digi+"):
    files = sorted(Path(dir_path).rglob("*.yaml"))
    cases = []
    for f in files:
        raw = f.read_text(encoding="utf-8")          # 一次性读完
        tpl = string.Template(raw)
        content = tpl.safe_substitute(projectId=PROJECT_ID)
        for doc in yaml.safe_load_all(content):      # ← 用替换后的字符串
            if not doc:
                continue
            if isinstance(doc, list):
                cases.extend(doc)
            else:
                cases.append(doc)
    return cases

ALL_CASES = load_all_test_data()

# 根据目录自动添加 pytest markers
def add_markers():
    import itertools
    markers = {}
    for case in ALL_CASES:
        # 从 url 路径推断模块
        parts = case['url'].strip('/').split('/')
        if len(parts) >= 2:
            module = parts[1]
            if module not in markers:
                markers[module] = getattr(pytest.mark, module, pytest.mark.generic)
    return markers

markers = add_markers()

@pytest.mark.parametrize("test_case", ALL_CASES, ids=[c.get("name") for c in ALL_CASES])
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