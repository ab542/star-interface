# utils/api_client.py
import json
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger
import pytest
from config.config import DEFAULT_MAX_RETRIES

# 关键字集合，可自行扩展
DB_ERROR_KEYWORDS = {"数据库", "DB Error", "SQL", "ORA-", "MySQL", "PostgreSQL"}

def get_speed_label(elapsed):
    if elapsed < 200:
        return "🟢快"
    elif elapsed < 500:
        return "🟡较快"
    elif elapsed < 1000:
        return "🟠一般"
    else:
        return "🔴慢"

def format_json_response(json_obj):
    import pprint
    return pprint.pformat(json_obj, width=120, compact=True)

def request_and_assert(
    name: str,
    method: str,
    url: str,
    headers: dict,
    timeout: int = 10,
    expected_status: int = 200,
    params: dict = None,
    data: dict = None,
    json: dict = None,
    expect_json: bool = True,
    expected_code: int = None,
    expected_response: dict = None,  # 期望响应 JSON 字段断言
    max_retries: int = None,  # None 表示使用默认配置
    verify: bool = False,  # 是否校验证书
    max_response_lines: Optional[int] = 10,  # 超过该行数将截断显示（None 表示不截断）
    fail_on_msg: bool = True,  # 当响应 JSON 中存在非空 'msg' 字段时视为异常并失败
) -> requests.Response:
    """
    统一发请求 + 重试 + 断言 + 日志
    成功 -> logs/success.log
    失败 -> logs/failure.log
    """
    # 使用默认重试次数
    if max_retries is None:
        max_retries = DEFAULT_MAX_RETRIES
    sess = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE'])
    )
    sess.mount("http://", HTTPAdapter(max_retries=retry))
    sess.mount("https://", HTTPAdapter(max_retries=retry))

    # 2. 统一错误详情模板
    def _detail(resp, elapsed=None, error=None):
        status = getattr(resp, 'status_code', 'N/A')
        text = getattr(resp, 'text', None)
        is_json = False
        try:
            json_obj = resp.json() if resp is not None else None
            is_json = isinstance(json_obj, dict)
        except Exception:
            json_obj = None
        lines = [
            f"[用例] {name}",
            f"[头部] {headers}",
            f"[URL] {method} {url}",
            f"[状态] {status}",
            f"[参数] params: {params} | data: {data} | json: {json}",
        ]
        if elapsed is not None:
            lines.append(f"[耗时] {elapsed}ms {get_speed_label(elapsed)}")
        if error:
            lines.append(f"[错误] {error}")
        # 将响应格式化为字符串，再按行处理截断（默认超过 10 行截断）
        if is_json and json_obj is not None:
            formatted = format_json_response(json_obj)
            header = "[响应-JSON]"
        else:
            formatted = str(text)
            header = "[响应]"

        formatted_lines = formatted.splitlines()
        total_lines = len(formatted_lines)
        if max_response_lines is not None and total_lines > max_response_lines:
            # 显示前 max_response_lines 行，并标注被截断
            preview = '\n  '.join(formatted_lines[:max_response_lines])
            lines.append(f"{header}-已截断（显示前{max_response_lines}行，共{total_lines}行）\n  {preview}\n  ... (truncated) ...")
        else:
            # 不截断，完整显示
            if header == "[响应-JSON]":
                lines.append(f"{header}\n  {formatted}")
            else:
                lines.append(f"{header} {formatted}")
        return '\n  '.join(lines)

    import time
    start_time = time.time()
    try:
        resp = sess.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
            verify=verify,  # 传递参数
        )
    except requests.RequestException as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.opt(depth=1).bind(sink="failure").error("❌\n  " + _detail(None, elapsed, f"Network/Timeout Error: {e}"))
        pytest.fail(str(e))
    elapsed = round((time.time() - start_time) * 1000, 2)

    # 4. 状态码断言
    # if resp.status_code != expected_status:
    #     logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, f"Status Code Error: expected {expected_status}") + "\n" + "-"*80)
    #     pytest.fail(f"Status Code Error: expected {expected_status}")

    # 6. 数据库异常关键字
    if any(k in resp.text for k in DB_ERROR_KEYWORDS):
        logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, "Database anomaly detected") + "\n" + "-"*80)
        pytest.fail("Database anomaly detected")

    # 7. 系统异常字符串
    if "系统异常" in resp.text:
        logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, "系统异常") + "\n" + "-"*80)
        pytest.fail("系统异常")

    # 8. 期望响应字段验证
    if expected_response is not None:
        try:
            body = resp.json()
            for key, expected_value in expected_response.items():
                if key not in body:
                    logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, f"Response missing key: '{key}'") + "\n" + "-"*80)
                    pytest.fail(f"Response missing expected key: {key}")
                actual_value = body.get(key)
                if actual_value != expected_value:
                    logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, f"Value mismatch for '{key}': expected {repr(expected_value)}, got {repr(actual_value)}") + "\n" + "-"*80)
                    pytest.fail(f"Value mismatch for key {key}: expected {repr(expected_value)}, got {repr(actual_value)}")
        except Exception as e:
            logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, f"Failed to validate expected_response: {e}") + "\n" + "-"*80)
            pytest.fail(f"Failed to validate expected_response: {e}")

    # 9. 业务层 msg 字段作为异常处理（可配置）
    # 如果预期 code != 0 说明是预期的错误响应，此时 msg 应有错误信息，跳过检查
    expected_code = None
    if expected_response is not None and 'code' in expected_response:
        expected_code = expected_response['code']
    if fail_on_msg and (expected_code is None or expected_code == 0):
        try:
            body = resp.json()
            if isinstance(body, dict) and 'msg' in body and body.get('msg'):
                msg_val = str(body.get('msg'))
                # 如果 msg 明确为成功性的短语（如 Success/OK），则不认为是异常
                if msg_val.strip().lower() not in ("success", "ok", "0", "true"):
                    logger.opt(depth=1).bind(sink="failure").error(f"❌\n  " + _detail(resp, elapsed, f"Business msg indicates failure: {msg_val}") + "\n" + "-"*80)
                    pytest.fail(f"Business msg indicates failure: {msg_val}")
        except Exception:
            # 无法解析为 JSON 则跳过此检查
            pass

    # 成功
    logger.opt(depth=1).bind(sink="success").info(f"✅\n  " + _detail(resp, elapsed) + "\n" + "-"*80)
    return resp
