import os
import pytest                      # 1. 记得导入
from loguru import logger

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

# 2. 去掉 URL 末尾空格
LOGIN_CASE = {
    "name": "login_once",
    "method": "POST",
    "url": "https://star.digiplus-intl.com/api/media/advertiser/login",
    "headers": {"Content-Type": "application/json"},
    "json": {"email": "liying@ama-auto.com", "password": "3149390154Li"},
}

@pytest.fixture(scope="session", autouse=True)
def global_token():
    """整个会话只登录一次，返回 token"""
    from util.api_client import request_and_assert
    resp = request_and_assert(**LOGIN_CASE, verify=False)
    token = resp.json()["data"]["token"]
    logger.bind(sink="success").info(f"全局 token 提取成功: {token[:20]}...")
    return token