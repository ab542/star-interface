import os
import pytest                      # 1. 记得导入
from loguru import logger
from config.config import BASE_URL2, DEFAULT_LOGIN_EMAIL, DEFAULT_LOGIN_PASSWORD

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger.add(
    f"{LOG_DIR}/success.log",
    rotation="1 MB",
    retention="10 days",
    level="INFO",
    filter=lambda r: r["extra"].get("sink") == "success"
)

logger.add(
    f"{LOG_DIR}/failure.log",
    rotation="1 MB",
    retention="10 days",
    level="ERROR",
    filter=lambda r: r["extra"].get("sink") == "failure"
)

# 登录配置从配置文件读取（可通过 local_config.py 覆盖）
LOGIN_CASE = {
    "name": "login_once",
    "method": "POST",
    "url": f"{BASE_URL2}/api/auth/login",
    "headers": {"Content-Type": "application/json"},
    "json": {"email": DEFAULT_LOGIN_EMAIL, "password": DEFAULT_LOGIN_PASSWORD}
}

@pytest.fixture(scope="session", autouse=True)
def global_token():
    """整个会话只登录一次，返回 token"""
    from util.api_client import request_and_assert
    resp = request_and_assert(**LOGIN_CASE, verify=False)
    token = resp.json()["data"]["token"]
    logger.bind(sink="success").info(f"全局 token 提取成功: {token[:20]}...")
    return token