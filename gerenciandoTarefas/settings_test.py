# gerenciandoTarefas/settings_test.py
"""
Settings dedicados para testes.

Estratégia:
- Força IS_DEVELOPMENT=True ANTES de importar settings base
- SQLite em memória para velocidade
- Desativa migrations, WebSocket real, Redis, HTTPS, logs
- Channels e cache locais (sem dependências externas)
"""
import os

# =============================================================================
# 🔑 CRÍTICO — definir ANTES do import do settings base
# =============================================================================
os.environ['IS_DEVELOPMENT'] = 'True'
os.environ['DEBUG'] = 'True'

from .settings import *  # noqa: F401, F403, E402

# =============================================================================
# 🗄️ BANCO DE DADOS 
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': ':memory:',
    }
}


# =============================================================================
# 🚫 MIGRATIONS — desativa (cria schema direto dos models = muito mais rápido)
# =============================================================================
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# =============================================================================
# ⚡ PERFORMANCE — hasher rápido
# =============================================================================
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =============================================================================
# 🔓 Neutraliza HTTPS/segurança residual
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
# 🌐 HOSTS
# =============================================================================
ALLOWED_HOSTS = ['*', 'testserver', 'localhost', '127.0.0.1']

# =============================================================================
# 📧 EMAIL — em memória
# =============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# =============================================================================
# 💾 CACHE — local em memória
# =============================================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# =============================================================================
# 📡 CHANNELS — layer em memória (sem Redis) + desativa push em tempo real
# =============================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Flag para o seu código pular push de WebSocket em testes
NOTIFICATIONS_REALTIME_ENABLED = False

# =============================================================================
# 🌿 CELERY — síncrono (sem broker)
# =============================================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# 📦 STORAGES — força backend moderno e remove settings antigas herdadas
# =============================================================================
import sys as _sys  # noqa: E402

_mod = _sys.modules[__name__]
for _attr in ('STATICFILES_STORAGE', 'DEFAULT_FILE_STORAGE'):
    if hasattr(_mod, _attr):
        delattr(_mod, _attr)

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# =============================================================================
# 🔇 LOGGING — silencia tudo (output limpo nos testes)
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {'handlers': ['null'], 'level': 'CRITICAL'},
}

import logging  # noqa: E402
logging.disable(logging.CRITICAL)

# =============================================================================
# 🐛 DEBUG — ligado ajuda em tracebacks; pode trocar para False se quiser
# =============================================================================
DEBUG = True

if 'TEMPLATES' in globals() and TEMPLATES:
    TEMPLATES[0].setdefault('OPTIONS', {})
    TEMPLATES[0]['OPTIONS']['debug'] = True
