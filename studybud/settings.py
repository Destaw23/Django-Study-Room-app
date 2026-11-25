import os
import secrets
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off'}:
        return False
    raise ImproperlyConfigured(f'{name} must be a boolean value.')


def env_list(name, default=None):
    value = os.environ.get(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


DEBUG = env_bool('DJANGO_DEBUG', False)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            'Set DJANGO_SECRET_KEY to a long, unique secret in production.'
        )
    SECRET_KEY = secrets.token_urlsafe(50)
elif not DEBUG and (
    len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure-')
):
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY must be at least 50 characters and not a development key.'
    )

ALLOWED_HOSTS = env_list(
    'DJANGO_ALLOWED_HOSTS',
    ['localhost', '127.0.0.1', '[::1]'] if DEBUG else None,
)
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'Set DJANGO_ALLOWED_HOSTS to the hostnames served by this deployment.'
    )

CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'base.apps.BaseConfig',
    'rest_framework',
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
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'studybud.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'studybud.wsgi.application'


def database_config():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        if not DEBUG:
            raise ImproperlyConfigured(
                'Set DATABASE_URL to a PostgreSQL or absolute SQLite database '
                'URL in production.'
            )
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }

    parsed_url = urlparse(database_url)
    if parsed_url.scheme == 'sqlite':
        if parsed_url.netloc or parsed_url.query or parsed_url.fragment:
            raise ImproperlyConfigured(
                'SQLite DATABASE_URL must be an absolute URL such as '
                'sqlite:////home/username/project/db.sqlite3.'
            )
        database_name = unquote(parsed_url.path)
        if not database_name.startswith('//'):
            raise ImproperlyConfigured(
                'SQLite DATABASE_URL must contain an absolute filesystem path.'
            )
        database_name = database_name[1:]
        if (
            not PurePosixPath(database_name).is_absolute()
            or database_name == '/'
        ):
            raise ImproperlyConfigured(
                'SQLite DATABASE_URL must contain an absolute filesystem path.'
            )
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': database_name,
        }

    if parsed_url.scheme not in {'postgres', 'postgresql'}:
        raise ImproperlyConfigured(
            'DATABASE_URL must use postgres://, postgresql://, or an '
            'absolute sqlite://// path.'
        )

    database_name = unquote(parsed_url.path.lstrip('/'))
    database_host = parsed_url.hostname or ''
    if not database_name or not database_host:
        raise ImproperlyConfigured(
            'DATABASE_URL must include a PostgreSQL database name and host.'
        )

    query_options = dict(parse_qsl(parsed_url.query))
    allowed_options = {
        'application_name',
        'connect_timeout',
        'options',
        'sslmode',
        'sslrootcert',
        'sslcert',
        'sslkey',
    }
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': database_name,
        'USER': unquote(parsed_url.username or ''),
        'PASSWORD': unquote(parsed_url.password or ''),
        'HOST': database_host,
        'PORT': parsed_url.port or '',
        'CONN_MAX_AGE': int(os.environ.get('DJANGO_DB_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            key: value for key, value in query_options.items()
            if key in allowed_options
        },
    }


DATABASES = {'default': database_config()}

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get('DJANGO_MEDIA_ROOT', BASE_DIR / 'media'))
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = int(
    os.environ.get('DJANGO_HSTS_SECONDS', '0' if DEBUG else '31536000')
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    'DJANGO_HSTS_INCLUDE_SUBDOMAINS', False
)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_HSTS_PRELOAD', False)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if env_bool('DJANGO_TRUST_X_FORWARDED_PROTO', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO').upper(),
    },
}
