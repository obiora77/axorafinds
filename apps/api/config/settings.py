"""Django settings for Axora Finds. All secrets and host-specific values come from the environment."""
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# One .env at the repo root is shared with the web app. apps/api/.env is also honoured.
load_dotenv(BASE_DIR.parent.parent / '.env')
load_dotenv(BASE_DIR / '.env')


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


DEBUG = env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'insecure-dev-only-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY (copy .env.example to .env).')

# Render sets these for every web service; using them means the API works even if the host
# variables are forgotten.
ON_RENDER = bool(os.getenv('RENDER'))
RENDER_HOST = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'django_filters',
    'accounts',
    'listings',
    'inspections',
    'pages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

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

# --- Database ---
# 1) DATABASE_URL (Render gives you one), 2) POSTGRES_* variables, 3) SQLite for local dev.
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if DATABASE_URL:
    _db = urlparse(DATABASE_URL)
    if _db.scheme not in {'postgres', 'postgresql'}:
        raise ImproperlyConfigured('DATABASE_URL must start with postgres:// or postgresql://')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(_db.path.lstrip('/')),
            'USER': unquote(_db.username or ''),
            'PASSWORD': unquote(_db.password or ''),
            'HOST': _db.hostname or '',
            'PORT': str(_db.port or 5432),
        }
    }
elif os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['POSTGRES_DB'],
            'USER': os.getenv('POSTGRES_USER', ''),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

FIXTURE_DIRS = [BASE_DIR / 'fixtures']

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']  # apps/api/static (the email logo lives here)
# Serve the admin's CSS/JS straight from the installed apps, so the admin is styled on Render even
# if `collectstatic` was never run. (After collectstatic, WhiteNoise serves the collected copies.)
WHITENOISE_USE_FINDERS = True
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- API ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer']
    + (['rest_framework.renderers.BrowsableAPIRenderer'] if DEBUG else []),
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    # Public forms are rate-limited per client (scopes are set on the views).
    'DEFAULT_THROTTLE_RATES': {
        'auth': '30/hour',
        'inspections': '30/hour',
        'payments': '60/hour',
        'newsletter': '20/hour',
        'contact': '20/hour',
        'reviews': '5/hour',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'UPDATE_LAST_LOGIN': True,
}

CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:5173')
CORS_ALLOW_HEADERS = (*default_headers, 'x-inspection-token')
# Optional: allow Vercel preview deployments too, e.g. ^https://axora-finds.*\.vercel\.app$
CORS_ALLOWED_ORIGIN_REGEXES = env_list('CORS_ALLOWED_ORIGIN_REGEXES')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173')
if RENDER_HOST:
    # The Django admin is served from this host over HTTPS.
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOST}')

# --- Email ---
# Every message is rendered from apps/api/templates/emails/. See config/emails.py.
#
# Render's FREE web services block outbound SMTP (ports 25, 465, 587), so Gmail/SMTP cannot send
# there. Pick ONE way to send:
#   * EMAIL_PROVIDER=brevo  + BREVO_API_KEY   (HTTPS, works on Render free)
#   * EMAIL_PROVIDER=resend + RESEND_API_KEY  (HTTPS, works on Render free)
#   * SMTP: EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD (local dev, or a paid Render instance)
# With nothing set, development prints emails to the terminal and production refuses to send.
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '').strip()
# Gmail shows app passwords as four groups with spaces; the spaces are not part of the password.
EMAIL_HOST_PASSWORD = ''.join(os.getenv('EMAIL_HOST_PASSWORD', '').split())
EMAIL_HOST = os.getenv('EMAIL_HOST', '').strip() or ('smtp.gmail.com' if EMAIL_HOST_USER else '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587') or 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '15') or 15)

BREVO_API_KEY = os.getenv('BREVO_API_KEY', '').strip()
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '').strip()
EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', '').strip().lower()
if not EMAIL_PROVIDER:
    EMAIL_PROVIDER = 'brevo' if BREVO_API_KEY else 'resend' if RESEND_API_KEY else ''
EMAIL_API_KEY = {'brevo': BREVO_API_KEY, 'resend': RESEND_API_KEY}.get(EMAIL_PROVIDER, '')
EMAIL_API_URL = os.getenv('EMAIL_API_URL', '').strip()  # override the provider endpoint (tests)
EMAIL_API_TIMEOUT = int(os.getenv('EMAIL_API_TIMEOUT', '15') or 15)

_explicit_backend = os.getenv('EMAIL_BACKEND', '').strip()
if _explicit_backend:
    EMAIL_BACKEND = _explicit_backend
elif EMAIL_PROVIDER == 'brevo':
    EMAIL_BACKEND = 'config.mail_backends.BrevoEmailBackend'
elif EMAIL_PROVIDER == 'resend':
    EMAIL_BACKEND = 'config.mail_backends.ResendEmailBackend'
elif EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
elif DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'  # not configured: refuse, don't pretend

TEAM_EMAIL = os.getenv('TEAM_EMAIL', 'axorafindsteam@gmail.com')
# With Brevo/Resend this must be an address (or domain) you verified in their dashboard.
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Axora Finds <no-reply@gmail.com>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# Absolute frontend URL used for links inside emails (no trailing slash).
SITE_URL = os.getenv('SITE_URL', 'http://localhost:5173').rstrip('/')
# HTTP email providers cannot embed the logo inline, so the HTML points at this public URL instead.
_render_url = os.getenv('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
EMAIL_LOGO_URL = os.getenv('EMAIL_LOGO_URL', '').strip() or (
    f'{_render_url}/static/img/logo.png' if _render_url else f'{SITE_URL}/logo.png'
)

# --- Production hardening (applies when DJANGO_DEBUG is off) ---
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
    # Behind Render's (or any) HTTPS proxy: without this Django thinks every request is plain HTTP,
    # which breaks admin login (CSRF) and makes uploaded-photo URLs http:// (blocked on an https site).
    if ON_RENDER or env_bool('DJANGO_BEHIND_PROXY', False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
