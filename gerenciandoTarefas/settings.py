
"""
Django settings for gerenciandoTarefas 1.02 por Emerson Goncalves.
"""

import os
import sys
import ssl
import logging
from pathlib import Path

from dotenv import load_dotenv
from decouple import config
from celery.schedules import crontab

from core.upload_config import UPLOAD_CONFIG
from datetime import timedelta

load_dotenv()
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# DETECÇÃO DE AMBIENTE — fonte da verdade: variável ENVIRONMENT
# =============================================================================
IS_WINDOWS = sys.platform == 'win32'

_env_name = config('ENVIRONMENT', default='').lower()

if _env_name:
    # Fonte explícita e confiável
    IS_DEVELOPMENT = _env_name in ('dev', 'development', 'local')
else:
    # Fallback: detecção antiga por sys.argv
    IS_RUNSERVER = 'runserver' in sys.argv or any('uvicorn' in a for a in sys.argv)
    IS_DEVELOPMENT = IS_WINDOWS and IS_RUNSERVER

IS_PRE_PRODUCTION = not IS_DEVELOPMENT

TESTING = 'test' in sys.argv or 'pytest' in sys.modules



# =============================================================================
# SEGURANÇA
# =============================================================================
SECRET_KEY = config('SECRET_KEY')
FERNET_KEYS = config('FERNET_KEYS')
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

DEBUG = config('DEBUG', default=IS_DEVELOPMENT, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# CSRF/CORS Origins - adaptativo por ambiente
if IS_DEVELOPMENT:
    CSRF_TRUSTED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'http://10.0.2.2:8000',
    ]
    CORS_ALLOWED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        'http://10.0.2.2:8000',
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://www.cetestgerenciandotarefas.com.br',
        'https://cetestgerenciandotarefas.com.br',
    ]
    CORS_ALLOWED_ORIGINS = [
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
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 dias

# =============================================================================
# TRAVA DE SEGURANÇA — em DEBUG, nunca forçar HTTPS (evita travar dev local)
# =============================================================================
if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_PROXY_SSL_HEADER = None

# =============================================================================
# JWT (JSON Web Token) - Configurações do Simple JWT
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),   # ajuste conforme necessidade
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
}

# =============================================================================
# INSTALLED APPS
# =============================================================================
INSTALLED_APPS = [
    'daphne',
    'channels',
    'core',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'rest_framework_simplejwt.token_blacklist',


    # Extensões
    'django_extensions',
    'django_bootstrap5',
    'django_htmx',
    'django_select2',
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

    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloudinary_storage',
    'django.contrib.staticfiles',  # deve vir DEPOIS de cloudinary_storage
    'cloudinary',

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
    'tributacao',
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
    'relatorio_fotografico',
]

# =============================================================================
# MIDDLEWARE - ADAPTATIVO POR AMBIENTE
# =============================================================================
MIDDLEWARE = [
    'core.middleware.DBConnectionMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

if IS_PRE_PRODUCTION:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')

MIDDLEWARE.extend([
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.CurrentFilialMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'core.middleware.MaintenanceModeMiddleware',
])

MAINTENANCE_MODE = False
APPEND_SLASH = True

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
                'usuario.context_processors.usuario_filial_context',
                'chat.context_processors.chat_global_data',
                'pgr_gestao.context_processors.pgr_stats',
                'notifications.context_processors.notification_processor',
                'gestao_riscos.context_processors.dias_sem_acidentes',
                'suprimentos.context_processors.suprimentos_contadores',
            ],
        },
    },
]

DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'  # Django < 4.0
DEFAULT_CONTENT_TYPE = 'text/html'

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
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

# Testes usam SQLite em memória (rápido e isolado do banco real)
if TESTING:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
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
USE_TZ = True
TIME_ZONE = 'America/Sao_Paulo'

# =============================================================================
# ARQUIVOS ESTÁTICOS E MÍDIA - ADAPTATIVO POR AMBIENTE
# =============================================================================
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'midia'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

if IS_DEVELOPMENT:
    # ── DESENVOLVIMENTO LOCAL ──
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    STATIC_URL = '/static/'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/midia/'
    logger.debug("📁 Usando storage local (Desenvolvimento)")
else:
    # ── PRODUÇÃO COM WHITENOISE + CLOUDINARY ──
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    STATIC_URL = '/static/'
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = '/midia/'
    logger.debug("📦 Usando WhiteNoise + Cloudinary (Produção)")

# =============================================================================
# ARQUIVOS PRIVADOS (sendfile2 - mantém local em qualquer ambiente)
# =============================================================================
PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, 'private_media')
SENDFILE_BACKEND = 'sendfile2.backends.simple'
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = '/private'

DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# E-MAIL
# =============================================================================
FORCE_REAL_EMAIL = config('FORCE_REAL_EMAIL', default=False, cast=bool)

# Backend por ambiente
if DEBUG and not FORCE_REAL_EMAIL:
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = BASE_DIR / 'sent_emails'
else:
    EMAIL_BACKEND = 'gerenciandoTarefas.email_backend.InsecureEmailBackend'

EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# Contexto SSL seguro por padrão (NÃO desabilitar check_hostname/verify_mode
# — isso abriria brecha para ataques MITM)
EMAIL_SSL_CONTEXT = ssl.create_default_context()

EMAIL_NOTIFICACAO_PGR = config('EMAIL_NOTIFICACAO_PGR', default='esg@cetestsp.com.br')
EMAIL_ALERTA_RISCO_CRITICO = config('EMAIL_ALERTA_RISCO_CRITICO', default='esg@cetestsp.com.br')

# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
# CONFIGURAÇÕES — APP TAREFAS
# =============================================================================
# Limite de recorrências geradas por execução do fallback (segurança)
TAREFAS_MAX_RECORRENCIAS_POR_EXECUCAO = 50

# =============================================================================
# CELERY - CONFIGURAÇÃO ADAPTATIVA
# =============================================================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False  # usa TZ local
CELERY_WORKER_CONCURRENCY = 2 if IS_DEVELOPMENT else 4  # reduzido pra container all-in-one
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

CELERY_TASK_TIME_LIMIT = 30 * 60        # 30min hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60   # 25min soft limit
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_DISABLE_RATE_LIMITS = True

CELERY_BEAT_SCHEDULE = {
    # ─── Tasks existentes ─────────────────────────────────────
    'verificar-vencimentos-diariamente': {
        'task': 'documentos.verificar_vencimentos',
        'schedule': crontab(minute=0, hour=9),
    },
    'gerar-notificacoes-diariamente': {
        'task': 'notifications.gerar_notificacoes',
        'schedule': crontab(minute=0, hour=11),
    },

    # ─── App Tarefas — Recorrência e Lembretes ────────────────
    'tarefas-marcar-atrasadas': {
        'task': 'tarefas.marcar_tarefas_atrasadas',
        'schedule': crontab(hour=0, minute=30),
    },
    'tarefas-gerar-recorrencias-pendentes': {
        'task': 'tarefas.gerar_recorrencias_pendentes',
        'schedule': crontab(hour=2, minute=0),
    },
    'tarefas-enviar-lembretes-prazo': {
        'task': 'tarefas.enviar_lembretes_prazo',
        'schedule': crontab(hour=8, minute=0),
    },
    'tarefas-avisar-recorrencias-proximas-fim': {
        'task': 'tarefas.avisar_recorrencias_proximas_fim',
        'schedule': crontab(hour=9, minute=0, day_of_week='monday'),
    },
}

# =============================================================================
# CHANNELS (WebSocket) - CONFIGURAÇÃO ADAPTATIVA
# =============================================================================
REDIS_HOST = config('REDIS_HOST', default='127.0.0.1')
REDIS_PORT = config('REDIS_PORT', default=6380, cast=int)

if IS_DEVELOPMENT:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(REDIS_HOST, REDIS_PORT)],
            },
        },
    }
    logger.debug("Usando Redis para WebSockets (Desenvolvimento)")
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(REDIS_HOST, REDIS_PORT)],
                'capacity': 1500,
                'expiry': 10,
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
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'fontTools': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'suprimentos': {
            'handlers': ['console'],
            'level': 'DEBUG' if IS_DEVELOPMENT else 'INFO',
            'propagate': False,
        },
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

# ══════════════════════════════════════════════════════════════════════
# Silenciar loggers verbosos de libs de terceiros
# (necessário porque Daphne/fontTools inicializam antes do LOGGING dict)
# ══════════════════════════════════════════════════════════════════════
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
    logging.getLogger(_name).setLevel(logging.ERROR)
    logging.getLogger(_name).propagate = False


