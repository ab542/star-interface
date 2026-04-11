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
DEFAULT_PROJECT_ID = "47"

# 默认登录 credentials
# 推荐在 local_config.py 中覆盖这些配置，local_config.py 不会提交到 git
DEFAULT_LOGIN_EMAIL = "your-email@example.com"
DEFAULT_LOGIN_PASSWORD = "your-password"

# 尝试导入本地配置（本地配置不会提交到 git）
try:
    from .local_config import *
except ImportError:
    pass

# 如果 local_config.py 中定义了 LOGIN_EMAIL，使用它覆盖默认值
if 'LOGIN_EMAIL' in globals():
    DEFAULT_LOGIN_EMAIL = LOGIN_EMAIL
if 'LOGIN_PASSWORD' in globals():
    DEFAULT_LOGIN_PASSWORD = LOGIN_PASSWORD
# 如果 local_config.py 中定义了 PROJECT_ID，使用它，否则使用默认值
if 'PROJECT_ID' not in globals():
    PROJECT_ID = DEFAULT_PROJECT_ID
