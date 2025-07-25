"""
Django settings for gerenciandoTarefas project.
Production settings for PythonAnywhere.
"""
import os
from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega as variáveis de ambiente de um arquivo .env
# Em produção no PythonAnywhere, você pode definir essas variáveis no arquivo WSGI ou usar um arquivo .env
# from dotenv import load_dotenv
# load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- CONFIGURAÇÕES DE SEGURANÇA PARA PRODUÇÃO ---

#  NUNCA deixe a SECRET_KEY exposta no código. Carregue-a de uma variável de ambiente.
SECRET_KEY = 'django-insecure-wt$exc#ld^38(f66)^zde_&=sd5c_xkx9n0r)^t7x67v0g!2*o'

#  DEBUG deve ser False em produção para evitar expor informações sensíveis.
# O cast=bool garante que 'True' ou 'False' no .env sejam convertidos corretamente.
DEBUG = config('DEBUG', default=False, cast=bool)

#  Especifique exatamente os domínios que servirão seu site.
# No seu arquivo .env, você pode ter: ALLOWED_HOSTS=.pythonanywhere.com,www.seudominio.com

#ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
ALLOWED_HOSTS = ( 
    'localhost',
    '127.0.0.1',
    'https://esgemerson.pythonanywhere.com/'
)

# --- Application definition ---

INSTALLED_APPS = [
    # Seus apps... (sem alteração)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'widget_tweaks',
    'crispy_forms',
    'crispy_bootstrap5',
    'localflavor',
    'home',
    'logradouro',
    'usuario',
    'cliente',
    'departamento_pessoal',
    'automovel.apps.AutomovelConfig',
    'seguranca_trabalho',
    'tarefas.apps.TarefasConfig',
    'treinamentos.apps.TreinamentosConfig',
    'gestao_riscos',
    'ata_reuniao',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
            ],
        },
    },
]

CRISPY_TEMPLATE_PACK = 'bootstrap5'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

WSGI_APPLICATION = 'gerenciandoTarefas.wsgi.application'

# --- BANCO DE DADOS ---
# As credenciais serão carregadas das variáveis de ambiente que você configurar no PythonAnywhere
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.mysql'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

# --- Validação de Senha ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'usuario.Usuario'

# --- Internacionalização ---
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True # Recomendado para produção para lidar com fuso horário de forma consistente (armazena em UTC)

# --- Arquivos Estáticos e de Mídia (Configuração para Produção) ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # O collectstatic juntará tudo aqui

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # Use 'media' em minúsculo por convenção

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Configurações de Email ---
# Carregue de variáveis de ambiente para segurança
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# --- DRF e Login ---
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

LOGIN_URL = 'usuario:login'
LOGIN_REDIRECT_URL = 'usuario:profile'
LOGOUT_REDIRECT_URL = 'usuario:login'

# --- Cabeçalhos de Segurança Adicionais para Produção ---
# Força o uso de HTTPS
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
SECURE_HSTS_SECONDS = 2592000  # 30 dias
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True