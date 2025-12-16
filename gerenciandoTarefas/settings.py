"""
Django settings for gerenciandoTarefas 1.01 por Emerson Goncalves.
"""

import os
import sys
from pathlib import Path
from decouple import config
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# DETECÇÃO AUTOMÁTICA DE AMBIENTE - CORRIGIDO
# =============================================================================
IS_WINDOWS = sys.platform == 'win32'
IS_RUNSERVER = 'runserver' in sys.argv
IS_DEVELOPMENT = IS_WINDOWS and IS_RUNSERVER
IS_PRE_PRODUCTION = not IS_DEVELOPMENT

# Debug adicional para verificar ambiente (remova depois)
#print(f"Ambiente detectado: {'DESENVOLVIMENTO' if IS_DEVELOPMENT else 'PRÉ-PRODUÇÃO'}")

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
    # Configurações de segurança para pré-produção
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    print("Configurações de segurança HTTPS ativadas (Pré-produção)")
else:
    # Configurações relaxadas para desenvolvimento local
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    print("Configurações de segurança HTTP ativadas (Desenvolvimento)")

# ADICIONE AQUI SUA NOVA CONDIÇÃO PARA DESENVOLVIMENTO
if IS_DEVELOPMENT:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    print("Configurações de SSL desativadas para ambiente de desenvolvimento")

# Configurações de segurança que se aplicam em qualquer ambiente
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'


# Apps que rodam em todos os ambientes    
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
    'notifications',
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
    'arquivos',
    'documentos',
    'api', 
]


# =============================================================================
# MIDDLEWARE - ADAPTATIVO POR AMBIENTE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]

# Adiciona WhiteNoise apenas em pré-produção
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
])

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
        'CONN_MAX_AGE': 0 if IS_DEVELOPMENT else 60,  # Connection pooling apenas em produção
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'connect_timeout': 10 if IS_DEVELOPMENT else 5,  # Timeout maior em dev
        }
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
# ARQUIVOS ESTÁTICOS E MÍDIA - ADAPTATIVO POR AMBIENTE
# =============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configuração de storage adaptativa
if IS_DEVELOPMENT:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    print("Usando storage simples para arquivos estáticos (Desenvolvimento)")
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    print("Usando storage comprimido para arquivos estáticos (Pré-produção)")

MEDIA_URL = '/midia/'
MEDIA_ROOT = BASE_DIR / 'midia'

PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR, 'private_media')
SENDFILE_BACKEND = 'sendfile2.backends.simple'
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = '/private'

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# E-MAIL
# =============================================================================
EMAIL_BACKEND = config('EMAIL_BACKEND')
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
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
    # Em desenvolvimento, usa 'localhost' como padrão se não houver .env
    REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
    print(f"Redis URL (Desenvolvimento): {REDIS_URL}")
else:
    # Em produção (hospedagem), EXIGE que a variável de ambiente exista.
    REDIS_URL = config('REDIS_URL')
    print(f"Redis URL (Pré-produção): configurado via variável de ambiente")

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
    print("Usando InMemory para WebSockets (Desenvolvimento)")
else:
    # Em produção, usa o Redis
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
            },
        },
    }
    print("Usando Redis para WebSockets (Pré-produção)")

CHAT_CONFIG = {
    'DESKTOP_NOTIFICATIONS': True,
    'SOUND_NOTIFICATIONS': True,
    'AUTO_RECONNECT': True,
    'RECONNECT_INTERVAL': 3000,
}

# =============================================================================
# LOGGING - CONFIGURAÇÃO ADAPTATIVA E SEGURA
# =============================================================================

# Criar diretório de logs se não existir (antes de configurar o logging)
LOGS_DIR = BASE_DIR / 'logs'
if IS_PRE_PRODUCTION:
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        print(f"Diretório de logs criado/verificado: {LOGS_DIR}")
    except Exception as e:
        print(f"Erro ao criar diretório de logs: {e}")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
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
        'level': 'WARNING',  # Só mostra WARNING, ERROR e CRITICAL
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Adicionar handler de arquivo apenas em pré-produção e se o diretório existir
if IS_PRE_PRODUCTION and LOGS_DIR.exists():
    try:
        LOGGING['handlers']['file'] = {
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        }
        # Adicionar o handler de arquivo aos loggers
        LOGGING['loggers']['django']['handlers'].append('file')
        LOGGING['root']['handlers'].append('file')
        print("Logging em arquivo ativado para pré-produção")
    except Exception as e:
        print(f"Não foi possível configurar logging em arquivo: {e}")
else:
    print("Logging apenas no console (Desenvolvimento)")


