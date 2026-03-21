"""
Django settings for gerenciandoTarefas 1.02 por Emerson Goncalves.
"""

import os
import sys
import ssl
from pathlib import Path
from decouple import config
from celery.schedules import crontab
import logging


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# DETECÇÃO AUTOMÁTICA DE AMBIENTE - CORRIGIDO
# =============================================================================
IS_WINDOWS = sys.platform == 'win32'
IS_RUNSERVER = 'runserver' in sys.argv or any('uvicorn' in arg for arg in sys.argv)
IS_UVICORN = any('uvicorn' in arg for arg in sys.argv)
IS_DEVELOPMENT = IS_WINDOWS and (IS_RUNSERVER or IS_UVICORN)
IS_PRE_PRODUCTION = not IS_DEVELOPMENT

# =============================================================================
# SEGURANÇA
# =============================================================================
SECRET_KEY = config('SECRET_KEY')
FERNET_KEYS = config('FERNET_KEYS')
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

DEBUG = config('DEBUG', default=IS_DEVELOPMENT, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# CSRF Origins - adaptativo por ambiente
if IS_DEVELOPMENT:
    CSRF_TRUSTED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://localhost:8000',
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://www.cetestgerenciandotarefas.com.br',
        'https://cetestgerenciandotarefas.com.br',
    ]

# =============================================================================
# SEGURANÇA - CONFIGURAÇÕES ADAPTATIVAS POR AMBIENTE
# =============================================================================
if IS_PRE_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'


INSTALLED_APPS = [
    'daphne',
    'channels',
    'core',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Extensões
    'django_components',
    'django_extensions',
    'django_bootstrap5',
    'django_htmx',
    'django_select2',
    'rest_framework',
    'rest_framework.authtoken',
    'dj_rest_auth', 
    'widget_tweaks',
    'crispy_forms',
    'crispy_bootstrap5',
    'localflavor',
    'template_partials',
    'phonenumber_field',
    'notifications.apps.NotificationsConfig',
    'dal',
    'dal_select2',                                       
    # Apps Locais
    'dashboard.apps.DashboardConfig',
    'usuario.apps.UsuarioConfig', 
    'home',
    'logradouro',
    'cliente',
    'departamento_pessoal',
    'automovel.apps.AutomovelConfig',
    'seguranca_trabalho',
    'suprimentos',
    'tarefas.apps.TarefasConfig',
    'treinamentos.apps.TreinamentosConfig',
    'gestao_riscos',
    'ata_reuniao',
    'ferramentas',
    'controle_de_telefone',
    'chat',
    'documentos',
    'api',
    'pgr_gestao.apps.PgrGestaoConfig',
    'ltcat',
]

# Adicionar storages apenas quando disponível (produção)
_storage_provider = config('STORAGE_PROVIDER', default='LOCAL')
if _storage_provider == 'GCS':
    try:
        import storages  # noqa: F401
        if 'storages' not in INSTALLED_APPS:
            INSTALLED_APPS.append('storages')
    except ImportError:
        logger.warning(
            "⚠️ STORAGE_PROVIDER=GCS mas 'django-storages' não está instalado!"
        )


# =============================================================================
# MIDDLEWARE - ADAPTATIVO POR AMBIENTE
# =============================================================================
MIDDLEWARE = [
    'core.middleware.DBConnectionMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

if IS_PRE_PRODUCTION:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')

MIDDLEWARE.extend([
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
])

MAINTENANCE_MODE = False

# =============================================================================
# URLs E TEMPLATES
# =============================================================================
ROOT_URLCONF = 'gerenciandoTarefas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.filial_context',
                'usuario.context_processors.filial_context',
                'chat.context_processors.chat_global_data',
                'pgr_gestao.context_processors.pgr_stats',
                'notifications.context_processors.notification_processor', 
            ],
        },
    },
]

CRISPY_TEMPLATE_PACK = 'bootstrap5'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

WSGI_APPLICATION = 'gerenciandoTarefas.wsgi.application'
ASGI_APPLICATION = 'gerenciandoTarefas.asgi.application'

# =============================================================================
# DATABASE - COM CONFIGURAÇÕES ADAPTATIVAS
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
        'CONN_MAX_AGE': 0 if IS_DEVELOPMENT else 300,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10 if IS_DEVELOPMENT else 5,
            'read_timeout': 30,
            'write_timeout': 30,
            'charset': 'utf8mb4',
            # Reconecta automaticamente (PyMySQL)
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# =============================================================================
# AUTENTICAÇÃO
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'usuario.Usuario'
LOGIN_URL = 'usuario:login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'usuario:login'

# =============================================================================
# INTERNACIONALIZAÇÃO
# =============================================================================
LANGUAGE_CODE = 'pt-br'
USE_I18N = True
USE_L10N = True
USE_TZ = True
TIME_ZONE = 'America/Sao_Paulo'

# =============================================================================
# GOOGLE CLOUD STORAGE - CONFIGURAÇÃO
# =============================================================================
GS_BUCKET_NAME = config('GS_BUCKET_NAME', default='ctst-bucket-estatico-2026')
GS_PROJECT_ID = config('GS_PROJECT_ID', default='ctst-project-2026')
GS_CREDENTIALS_PATH = config('GS_CREDENTIALS', default='ctst-storage-key.json')

STORAGE_PROVIDER = config('STORAGE_PROVIDER', default='LOCAL')

# Carregar credenciais GCS apenas quando necessário
GS_CREDENTIALS = None
if STORAGE_PROVIDER == 'GCS':
    try:
        from google.oauth2 import service_account
        import json

        # OPÇÃO 1: Credenciais via variável de ambiente (JSON inline) - PRODUÇÃO
        gs_credentials_json = os.getenv('GS_CREDENTIALS_JSON', '')

        if gs_credentials_json:
            credentials_info = json.loads(gs_credentials_json)
            GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
                credentials_info
            )
            logger.info("✅ Credenciais GCS carregadas via variável de ambiente")
        else:
            # OPÇÃO 2: Fallback para arquivo local (desenvolvimento)
            _credentials_file = os.path.join(BASE_DIR, GS_CREDENTIALS_PATH)
            if os.path.exists(_credentials_file):
                GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
                    _credentials_file
                )
                logger.info("✅ Credenciais GCS carregadas via arquivo local")
            else:
                logger.warning(f"⚠️ Arquivo de credenciais não encontrado: {_credentials_file}")

    except Exception as e:
        logger.error(f"❌ Erro ao carregar credenciais GCS: {e}")

GS_DEFAULT_ACL = None
GS_QUERYSTRING_AUTH = False
GS_FILE_OVERWRITE = False


# =============================================================================
# ARQUIVOS ESTÁTICOS E MÍDIA - ADAPTATIVO POR AMBIENTE              ← ALTERADO
# =============================================================================
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'midia'                     # ← SEMPRE definido (fallback)

if STORAGE_PROVIDER == 'GCS':
    # ── PRODUÇÃO COM GOOGLE CLOUD STORAGE ──
    STATICFILES_STORAGE = 'storage_backends.StaticStorage'
    STATIC_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/static/'

    DEFAULT_FILE_STORAGE = 'storage_backends.MediaStorage'
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/media/'

    # MEDIA_ROOT já definido acima como fallback para management commands
    logger.info(f"☁️ Usando Google Cloud Storage: {GS_BUCKET_NAME}")

elif IS_DEVELOPMENT:
    # ── DESENVOLVIMENTO LOCAL ──
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    STATIC_URL = '/static/'

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/midia/'
    # MEDIA_ROOT já definido acima

    logger.debug("📁 Usando storage local (Desenvolvimento)")

else:
    # ── PRÉ-PRODUÇÃO COM WHITENOISE (sem GCS) ──
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    STATIC_URL = '/static/'

    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/midia/'
    # MEDIA_ROOT já definido acima

    logger.debug("📦 Usando WhiteNoise (Pré-produção sem GCS)")

# =============================================================================
# ARQUIVOS PRIVADOS (sendfile2 - mantém local em qualquer ambiente)
# =============================================================================
PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, 'private_media')
SENDFILE_BACKEND = 'sendfile2.backends.simple'
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = '/private'

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# O bucket name é obrigatório para o fallback funcionar
GS_BUCKET_NAME = 'seu-bucket-da-producao'  # mesmo nome que usa em produção

# =============================================================================
# E-MAIL
# =============================================================================
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.m9.network')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# O certificado do servidor SMTP é emitido para *.m9.network,
# não para smtp.cetestsp.com.br, então desabilitamos a verificação de hostname
# mantendo a validação do certificado em si (CERT_REQUIRED continua ativo)
EMAIL_SSL_CONTEXT = ssl.create_default_context()
EMAIL_SSL_CONTEXT.check_hostname = False
EMAIL_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

EMAIL_NOTIFICACAO_PGR = config('EMAIL_NOTIFICACAO_PGR', default='esg@cetestsp.com.br')
EMAIL_ALERTA_RISCO_CRITICO = config('EMAIL_ALERTA_RISCO_CRITICO', default='esg@cetestsp.com.br')


# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 30,
    'DATETIME_FORMAT': '%d/%m/%Y %H:%M',
    'DATE_FORMAT': '%d/%m/%Y',
}


# =============================================================================
# CELERY - CONFIGURAÇÃO ADAPTATIVA
# =============================================================================
if IS_DEVELOPMENT:
    REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
else:
    REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')


CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_WORKER_CONCURRENCY = 2 if IS_DEVELOPMENT else 8
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

CELERY_TASK_ROUTES = {
    'documentos.*': {'queue': 'documentos'},
    'chat.*': {'queue': 'chat'},
}

CELERY_BEAT_SCHEDULE = {
    'verificar-vencimentos-diariamente': {
        'task': 'documentos.verificar_vencimentos',
        'schedule': crontab(minute=0, hour=3),
    },
    'gerar-notificacoes-diariamente': {
        'task': 'notifications.gerar_notificacoes',
        'schedule': crontab(minute=0, hour=7),
    },
}

# =============================================================================
# CHANNELS (WebSocket) - CONFIGURAÇÃO ADAPTATIVA
# =============================================================================
if IS_DEVELOPMENT:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
    logger.debug("Usando InMemory para WebSockets (Desenvolvimento)")
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
            },
        },
    }
    logger.debug("Usando Redis para WebSockets (Pré-produção)")

CHAT_CONFIG = {
    'DESKTOP_NOTIFICATIONS': True,
    'SOUND_NOTIFICATIONS': True,
    'AUTO_RECONNECT': True,
    'RECONNECT_INTERVAL': 3000,
}

# =============================================================================
# LOGGING - CONFIGURAÇÃO ADAPTATIVA E SEGURA
# =============================================================================

LOGS_DIR = BASE_DIR / 'logs'
if IS_PRE_PRODUCTION:
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        logger.debug(f"Diretório de logs criado/verificado: {LOGS_DIR}")
    except Exception as e:
        logger.debug(f"Erro ao criar diretório de logs: {e}")


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'fontTools': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'fontTools.subset': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'weasyprint': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'suprimentos': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


if IS_PRE_PRODUCTION and LOGS_DIR.exists():
    try:
        LOGGING['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        }
        LOGGING['loggers']['django']['handlers'].append('file')
        LOGGING['root']['handlers'].append('file')
        logger.debug("Logging em arquivo ativado para pré-produção")
    except Exception as e:
        logger.debug(f"Não foi possível configurar logging em arquivo: {e}")
else:
    logger.debug("Logging apenas no console (Desenvolvimento)")


TESTING = 'test' in sys.argv or 'pytest' in sys.modules

# ══════════════════════════════════════════════════════════════════════
# (necessário porque Daphne/fontTools inicializam antes do LOGGING dict)
# ══════════════════════════════════════════════════════════════════════
import logging as _logging

_QUIET_LOGGERS = [
    'fontTools', 'fontTools.subset', 'fontTools.ttLib',
    'fontTools.ttLib.tables', 'fontTools.misc',
    'fontTools.subset.timer', 'fontTools.cff',
    'weasyprint', 'weasyprint.css', 'weasyprint.html',
    'weasyprint.document', 'weasyprint.images',
    'daphne', 'daphne.server', 'daphne.http_protocol',
    'daphne.ws_protocol',
    'twisted',
]

for _name in _QUIET_LOGGERS:
    _logging.getLogger(_name).setLevel(_logging.ERROR)
    _logging.getLogger(_name).propagate = False
    _logging.getLogger().setLevel(_logging.WARNING)
    _logging.getLogger('django').setLevel(_logging.INFO)
    _logging.getLogger('django.server').setLevel(_logging.WARNING)
    _logging.getLogger('suprimentos').setLevel(_logging.DEBUG)

