import os
import sys
from pathlib import Path
from datetime import timedelta
from env import env
from api.settings.constant import constant

BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / 'app'  # app directory
sys.path.insert(0, str(APPS_DIR))  # Add app directory first to ensure user can be found
sys.path.insert(0, str(BASE_DIR))  # Add root directory to ensure settings can be found

SECRET_KEY = constant.SECRET_KEY
DEBUG = env.DEBUG
APPEND_SLASH = False  # No longer automatically add trailing slash

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'health_check',
    'rest_framework',
    'drf_yasg',
    'corsheaders',
    'user',
    'doc',
    'project',
    "llm",
    'base',
    'error'
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

ROOT_URLCONF = 'api.settings.urls'
WSGI_APPLICATION = 'settings.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env.DB_NAME,
        'USER': env.DB_USER,
        'PASSWORD': env.DB_PASSWORD,
        'HOST': env.DB_HOST,
        'PORT': env.DB_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',  # Character set
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",  # Strict mode
        },
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
}

SIMPLE_JWT = {
    # 1. access token expiration time (default 5 minutes)
    'ACCESS_TOKEN_LIFETIME': timedelta(days=5),

    # 2. refresh token expiration time (default 1 day)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),

    # 3. Whether rotation is allowed (optional)
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # 4. Keep other settings as default
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Log format
    'formatters': {
        'django_verbose': {
            'format': '[{asctime}] {levelname} {name} [{process:d}:{thread:d}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'app_verbose': {
            'format': '[{asctime}] {levelname} {name} [{process:d}:{thread:d}] {pathname}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'django_simple': {
            'format': '[{asctime}] {levelname} {name} {pathname}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
        'app_simple': {
            'format': '[{asctime}] {levelname} {name} {pathname}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
    },
    # Handlers
    'handlers': {
        # Output to console
        'console_apps': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'app_simple',
            'stream': 'ext://sys.stdout',  # Explicitly specify output to stdout
        },
        'console_django': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'django_simple',
            'stream': 'ext://sys.stdout',  # Explicitly specify output to stdout
        },
        # Output to log file
        'file_apps': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR.parent, 'api/logs/app.log'),
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'app_verbose',
            'encoding': 'utf-8',
        },
        # Output to log file
        'file_django': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR.parent, 'api/logs/django.log'),
            'when': 'midnight',
            'backupCount': 30,
            'formatter': 'django_verbose',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        # Django framework's own logger, all logs from the framework (request processing, ORM warnings, migration prompts, etc.) will go to this logger
        'django': {
            'handlers': ['console_django', 'file_django'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console_apps', 'file_apps'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Root logger configuration is empty, let each logger handle independently
    }
}

# Email related configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env.EMAIL_HOST
EMAIL_PORT = env.EMAIL_PORT
EMAIL_USE_SSL = env.EMAIL_USE_SSL
EMAIL_HOST_USER = env.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = env.EMAIL_HOST_PASSWORD  # Email authorization code, not password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Cache configuration (for storing verification codes)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{env.REDIS_HOST}:{env.REDIS_PORT}/{env.REDIS_DB}',
    }
}


AUTH_USER_MODEL = "user.User"

# -----------------The following configurations are generally not modified-----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_URL = '/static/'
# Add static file directory configuration, pure backend without any interface (not using Admin, DRF browsing interface, Swagger) does not need this configuration
STATICFILES_DIRS = []

# Production environment static file collection directory, production environment needs static files to be collected
STATIC_ROOT = BASE_DIR.parent / "static"