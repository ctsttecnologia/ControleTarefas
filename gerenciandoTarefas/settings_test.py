# gerenciandoTarefas/settings_test.py
"""
Settings dedicados para testes.
Força IS_DEVELOPMENT=True ANTES de importar settings.py para que
todos os blocos `if IS_PRE_PRODUCTION:` sejam ignorados.
"""
import os

# 🔑 CRÍTICO: definir ANTES do import do settings base
os.environ['IS_DEVELOPMENT'] = 'True'
os.environ['DEBUG'] = 'True'

from .settings import *  # noqa: F401, F403, E402

# =============================================================================
# 🔓 Reforço: neutraliza qualquer redirect HTTPS residual
# =============================================================================
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# =============================================================================
# 🌐 HOSTS — libera testserver
# =============================================================================
ALLOWED_HOSTS = ['*', 'testserver', 'localhost', '127.0.0.1']

# =============================================================================
# ⚡ Performance
# =============================================================================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =============================================================================
# 📧 Email em memória
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# =============================================================================
# 🚫 Cache local
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# =============================================================================
# 🔇 Logs silenciados
# =============================================================================
import logging  # noqa: E402
logging.disable(logging.CRITICAL)

# =============================================================================
# 🐛 DEBUG ligado (ajuda em tracebacks durante desenvolvimento de testes)
# =============================================================================
DEBUG = True
