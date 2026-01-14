"""
Django settings for FF (Feuerwehr-Fairness) Electron App.
Configured for local SQLite database and desktop usage.
"""

import os
import secrets
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Electron mode detection
ELECTRON_MODE = os.getenv('ELECTRON_MODE', 'false').lower() == 'true'

# Get data directory from environment (set by Electron) or use local path
# This ensures we write to a location with write permissions (ProgramData on Windows)
DATA_PATH = os.getenv('FF_DATABASE_PATH')
if DATA_PATH:
    SECRET_KEY_DIR = Path(DATA_PATH).parent
else:
    SECRET_KEY_DIR = BASE_DIR

# Security settings - Generate secret key if not exists
SECRET_KEY_FILE = SECRET_KEY_DIR / '.secret_key'
try:
    if SECRET_KEY_FILE.exists():
        SECRET_KEY = SECRET_KEY_FILE.read_text().strip()
    else:
        SECRET_KEY = secrets.token_urlsafe(50)
        SECRET_KEY_DIR.mkdir(parents=True, exist_ok=True)
        SECRET_KEY_FILE.write_text(SECRET_KEY)
except (PermissionError, OSError):
    # Fallback: generate a new key each time (not ideal but works)
    SECRET_KEY = secrets.token_urlsafe(50)

# Debug mode for development
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'

# Allowed hosts for local Electron app
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# CSRF settings for local app
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'django_htmx',
    # Local apps
    'apps.core',
    'apps.members',
    'apps.vehicles',
    'apps.qualifications',
    'apps.scheduling',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Database - SQLite for Electron App
# Database file is stored in user data directory when running in Electron
DB_PATH = os.getenv('FF_DATABASE_PATH', BASE_DIR / 'data' / 'ff_database.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_PATH,
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Ensure data directory exists
DATA_DIR = Path(DB_PATH).parent
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom user model
AUTH_USER_MODEL = 'core.User'

# Internationalization
LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login settings
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Security settings - relaxed for local Electron app
# No SSL/HTTPS required for localhost
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Allow embedding in Electron
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Logging - use writable directory (ProgramData on Windows when in Electron mode)
if ELECTRON_MODE and DATA_PATH:
    LOGS_DIR = Path(DATA_PATH).parent / 'logs'
else:
    LOGS_DIR = BASE_DIR / 'logs'

try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    # Fallback to temp directory
    import tempfile
    LOGS_DIR = Path(tempfile.gettempdir()) / 'FF-Feuerwehr-Fairness' / 'logs'
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'ff_app.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
