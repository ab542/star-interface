# config/config.py

BASE_URL = "https://cartea.icartea.com"
BASE_URL2 = 'https://star.digiplus-intl.com'
TIMEOUT = 10  # 请求超时时间（秒）
DEFAULT_MAX_RETRIES = 3  # 默认重试次数
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 默认项目 ID
PROJECT_ID = "45"

# 默认登录 credentials
DEFAULT_LOGIN_EMAIL = "liying@ama-auto.com"
DEFAULT_LOGIN_PASSWORD = "3149390154Li"

# 尝试导入本地配置（本地配置不会提交到 git）
try:
    from .local_config import *
except ImportError:
    pass
