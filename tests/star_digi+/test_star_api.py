import pytest
import requests
import yaml
from pathlib import Path
from loguru import logger
from config.config import BASE_URL2, TIMEOUT, HEADERS
from util.api_client import request_and_assert
import string

# 你自己想定义的项目 ID
PROJECT_ID = "45"      # 想换就改这里
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

@pytest.mark.parametrize("test_case", ALL_CASES, ids=[c.get("name") for c in ALL_CASES])
def test_star_api(test_case, global_token):          # ① 注入 fixture
    # headers = HEADERS.copy()                         # ② 复制默认头
    headers = test_case.get("headers", {}).copy()    # ② 复制用例头
    headers["Cookie"] = f"token={global_token}"      # ③ 加 Cookie
    request_and_assert(
        name=test_case["name"],
        method=test_case["method"],
        url=f"{BASE_URL2}{test_case['url']}",
        headers=headers,                           # ④ 使用新 headers
        timeout=TIMEOUT,
        expected_status=test_case["expected_status"],
        params=test_case.get("params"),
        data=test_case.get("data"),
        json=test_case.get("json"),
        verify=False
    )