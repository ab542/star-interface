import pytest
import requests
import yaml
import re
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

def extract_by_jsonpath(obj: dict, path: str):
    """
    简化版 JSONPath 提取
    支持: data.id, data.list[0].id, data.items[1].name
    """
    parts = path.split('.')
    current = obj
    try:
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
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"JSONPath extraction failed: path='{path}', error={str(e)}") from e

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

def get_variable_from_context(path: str, context: dict):
    """
    从上下文获取变量，路径格式: step_name.json.path
    """
    # context 格式: {step_name: response_obj}
    # path: create_folder.data.id → split → step_name=create_folder, sub_path=data.id
    first_dot = path.find('.')
    if first_dot == -1:
        if path not in context:
            raise ValueError(f"Pre-step '{path}' not found in context. Available steps: {list(context.keys())}")
        return context[path]
    step_name = path[:first_dot]
    if step_name not in context:
        raise ValueError(f"Pre-step '{step_name}' not found in context. Available steps: {list(context.keys())}")
    sub_path = path[first_dot+1:]
    resp = context[step_name]
    return extract_by_jsonpath(resp.json(), sub_path)

@pytest.mark.parametrize("test_case", PARAM_CASES)
def test_star_api(test_case, global_token):
    headers = test_case.get("headers", {}).copy()
    headers["star-token"] = f"Bearer {global_token}"

    # 处理 pre_steps 前置步骤
    context = {}  # {step_name: response}
    pre_steps = test_case.get("pre_steps", [])
    for pre_step in pre_steps:
        # 验证必填字段
        if "name" not in pre_step:
            raise ValueError(f"pre-step is missing 'name' field in test case '{test_case['name']}'")
        if "method" not in pre_step:
            raise ValueError(f"pre-step '{pre_step.get('name', 'unnamed')}' is missing 'method' field")
        if "url" not in pre_step:
            raise ValueError(f"pre-step '{pre_step.get('name', 'unnamed')}' is missing 'url' field")

        # 替换变量
        step_headers = pre_step.get("headers", {}).copy()
        step_headers["star-token"] = f"Bearer {global_token}"

        step_method = pre_step["method"]
        step_url = f"{BASE_URL2.rstrip('/')}/{pre_step['url'].lstrip('/')}"
        step_params = substitute_variables(pre_step.get("params"), context) if pre_step.get("params") is not None else None
        step_data = substitute_variables(pre_step.get("data"), context) if pre_step.get("data") is not None else None
        step_json = substitute_variables(pre_step.get("json"), context) if pre_step.get("json") is not None else None
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
    params = substitute_variables(test_case.get("params"), context) if test_case.get("params") is not None else None
    data = substitute_variables(test_case.get("data"), context) if test_case.get("data") is not None else None
    json_body = substitute_variables(test_case.get("json"), context) if test_case.get("json") is not None else None

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
