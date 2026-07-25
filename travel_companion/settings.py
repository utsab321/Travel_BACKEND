import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from decouple import config as env_config

# Load environment variables from .env file
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

print("Loading .env from:", env_path)
print("DATABASE_URL =", os.getenv("DB_URL"))
load_dotenv(env_path, verbose=True)


# ========================
# BASE DIR
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# SECURITY
# ========================
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set!")

# DEBUG should be False in production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Production domains — NO protocol prefix in ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'travel-companion-api-mrmr.onrender.com',
    'travel-backend-plm3.onrender.com',
    'localhost',
    '127.0.0.1',
    '.onrender.com',  # Allow all Render subdomains
]
# Add any additional hosts from environment variable (comma-separated, no protocol)
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.environ.get('ALLOWED_HOSTS', '').split(','))

# ========================
# CORS (React connection)
# ========================
# Development origins
CORS_ALLOWED_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Production origins
CORS_ALLOWED_ORIGINS_PROD = [
    "https://travelfrontend-nu.vercel.app",
    "https://travel-companion-api-mrmr.onrender.com",
]
CSRF_TRUSTED_ORIGINS = [
    "https://travelfrontend-nu.vercel.app",
]

# Merge env-injected origins into whichever list is active
if os.environ.get('CORS_ALLOWED_ORIGINS'):
    _extra_origins = [o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
    if DEBUG:
        CORS_ALLOWED_ORIGINS_DEV.extend(_extra_origins)
    else:
        CORS_ALLOWED_ORIGINS_PROD.extend(_extra_origins)

CORS_ALLOWED_ORIGINS = CORS_ALLOWED_ORIGINS_DEV if DEBUG else CORS_ALLOWED_ORIGINS_PROD

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ========================
# INSTALLED APPS
# ========================
INSTALLED_APPS = [
    # Admin UI — using jazzmin only (unfold conflicts with jazzmin; choose one)
    'jazzmin',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'channels',
    'corsheaders',
    "cloudinary",
    "cloudinary_storage",
    'apps.trips',
    'apps.chat',
    'apps.expenses',
    'apps.kyc.apps.KycConfig',
    'apps.users.apps.UsersConfig',

    'core',
]

# ========================
# MIDDLEWARE
# ========================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',      # Must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serves static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========================
# SECURITY HEADERS (Production only)
# ========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'

# ========================
# URLS & TEMPLATES
# ========================
ROOT_URLCONF = 'travel_companion.urls'

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

# ========================
# CHANNELS (WebSocket)
# ========================
ASGI_APPLICATION = 'travel_companion.asgi.application'
WSGI_APPLICATION = 'travel_companion.wsgi.application'

# Use Redis in production for multi-worker support; fallback to InMemory for dev
REDIS_URL = os.environ.get('REDIS_URL', '')

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    # InMemoryChannelLayer — fine for single-worker dev/staging
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ========================
# DATABASE
# ========================
if DEBUG:
    # Development: SQLite (no extra config needed)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production: PostgreSQL via DATABASE_URL / DB_URL env variable
    _db_url = os.environ.get('DATABASE_URL') or os.environ.get('DB_URL')
    if not _db_url:
        raise ValueError("DATABASE_URL (or DB_URL) environment variable must be set in production!")
    DATABASES = {
        'default': dj_database_url.parse(_db_url, conn_max_age=600, ssl_require=True)
    }

# ========================
# REST FRAMEWORK + JWT
# ========================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ========================
# JAZZMIN ADMIN UI
# ========================
JAZZMIN_SETTINGS = {
    'site_title': 'Travel Companion Admin',
    'site_header': 'Travel Companion',
    'welcome_sign': 'Welcome to Travel Companion Admin',
    'show_sidebar': True,
    'navigation_expanded': True,
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.group': 'fas fa-users',
    },
    'order_with_respect_to': [
        'auth',
        'users',
        'core',
        'trips',
        'expenses',
    ],
}


CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}


JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': True,
    'body_small_text': False,
    'brand_color': '#1e3a8a',
    'accent': 'accent-primary',
    'rounded_corners': True,
}

# ========================
# PASSWORD VALIDATION
# ========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ========================
# INTERNATIONALIZATION
# ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ========================
# STATIC FILES
# ========================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Django 4.2+ recommended way to configure static file storage
STORAGES = {
    'default': {
    
        # 'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

WHITENOISE_MANIFEST_STRICT = False

WHITENOISE_MIMETYPES = {
    ".map": "application/json",
}

# ========================
# MEDIA FILES (Uploads)
# ========================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# ========================
# EMAIL CONFIGURATION (Gmail SMTP)
# ========================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@travelcompanion.com')

# ========================
# FILE UPLOAD LIMITS
# ========================
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB

# ========================
# DEFAULT PRIMARY KEY
# ========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'