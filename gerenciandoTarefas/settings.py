"""
Django settings for gerenciandoTarefas 1.01 project por Emerson Goncalves.
"""
import os
import sys
from pathlib import Path
from decouple import config
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# DETECÇÃO AUTOMÁTICA DE AMBIENTE
# =============================================================================
IS_WINDOWS = sys.platform == 'win32'
IS_RUNSERVER = 'runserver' in sys.argv
IS_DEVELOPMENT = IS_WINDOWS and IS_RUNSERVER

# =============================================================================
# SEGURANÇA
# =============================================================================
SECRET_KEY = config('SECRET_KEY')
FERNET_KEYS = config('FERNET_KEYS')
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

CSRF_TRUSTED_ORIGINS = [
    'https://www.cetestgerenciandotarefas.com.br',
    'https://cetestgerenciandotarefas.com.br',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# =============================================================================
# INSTALLED APPS
# =============================================================================
INSTALLED_APPS = []

# Daphne e Channels são APENAS para produção (Linux)
if not IS_WINDOWS:
    INSTALLED_APPS.extend(['daphne', 'channels'])

# Apps que rodam em todos os ambientes    
INSTALLED_APPS = [
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
    'core',
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
]

# Daphne apenas em produção
if not IS_DEVELOPMENT:
    INSTALLED_APPS.insert(0, 'daphne')

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

# WhiteNoise apenas em desenvolvimento
if IS_DEVELOPMENT:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

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
# DATABASE
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
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
# ARQUIVOS ESTÁTICOS E MÍDIA
# =============================================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

if IS_DEVELOPMENT:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

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
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 30
}

# =============================================================================
# CELERY
# =============================================================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_WORKER_CONCURRENCY = 4 if DEBUG else 8
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
# CHANNELS (WebSocket)
# =============================================================================
if IS_DEVELOPMENT:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [config('REDIS_URL', default='redis://localhost:6379/0')],
            },
        },
    }

CHAT_CONFIG = {
    'DESKTOP_NOTIFICATIONS': True,
    'SOUND_NOTIFICATIONS': True,
    'AUTO_RECONNECT': True,
    'RECONNECT_INTERVAL': 3000,
}

# =============================================================================
# LOG DE AMBIENTE
# =============================================================================
if IS_DEVELOPMENT:
    print("🔧 DESENVOLVIMENTO (Windows/WSGI) - WhiteNoise ativado")
else:
    print("🚀 PRODUÇÃO (Linux/ASGI) - Nginx serve estáticos")



