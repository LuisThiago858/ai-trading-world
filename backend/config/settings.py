import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-demo-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
INSTALLED_APPS = [
    "django.contrib.contenttypes", "django.contrib.staticfiles", "rest_framework",
    "apps.simulations", "apps.portfolios", "apps.market_data", "apps.ledger", "apps.risk", "apps.orders", "apps.agents",
]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"
if os.getenv("POSTGRES_HOST"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": os.getenv("POSTGRES_DB", "ai_trading_world"),
        "USER": os.getenv("POSTGRES_USER", "ai_trading_world"), "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.environ["POSTGRES_HOST"], "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Manaus"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"], "UNAUTHENTICATED_USER": None}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ai-trading-world-market-data",
    }
}
MARKET_DATA_MODE = os.getenv("MARKET_DATA_MODE", "fixture").lower()
MARKET_DATA_TTL_SECONDS = int(os.getenv("MARKET_DATA_TTL_SECONDS", "300"))
MARKET_DATA_HTTP_TIMEOUT_SECONDS = int(os.getenv("MARKET_DATA_HTTP_TIMEOUT_SECONDS", "8"))
MARKET_DATA_MIN_REQUEST_INTERVAL_SECONDS = int(os.getenv("MARKET_DATA_MIN_REQUEST_INTERVAL_SECONDS", "2"))
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("ANALYSIS_HARD_TIME_LIMIT_SECONDS", "90"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("ANALYSIS_SOFT_TIME_LIMIT_SECONDS", "75"))
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-6-astra")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1200"))
ANALYSIS_MAX_ATTEMPTS = int(os.getenv("ANALYSIS_MAX_ATTEMPTS", "3"))

