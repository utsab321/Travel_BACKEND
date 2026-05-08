import os
from pathlib import Path
from datetime import timedelta

# Load environment variables from .env file
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# ========================
# BASE DIR
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# SECURITY
# ========================
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-33a!xk@x1n43*g-cg=9+(nnpcd+_m%xtuscg#0p(%6^0n#lnui')

# DEBUG should be False in production
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Production domains and localhost for development
ALLOWED_HOSTS = [
    'travel-companion-api-mrmr.onrender.com',
    'localhost',
    '127.0.0.1',
    '.onrender.com',  # Allow all Render domains
]
# Add any additional hosts from environment variable
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.environ.get('ALLOWED_HOSTS', '').split(','))

# ========================
# CORS (React connection)
# ========================
# For development
CORS_ALLOWED_ORIGINS_DEV = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# For production - add Vercel frontend URLs and Render backend
CORS_ALLOWED_ORIGINS_PROD = [
    # Vercel Frontend URLs
    "https://project-front-tan.vercel.app",
    "https://project-front-c76lpejp6-aayushdais-projects.vercel.app",
    "https://project-front-n8mk7f7ll-aayushdais-projects.vercel.app",
    "https://travelcompanionsystem-git-main-aayushdais-projects.vercel.app",
    "https://travelcompanionsystem.vercel.app",
    # Render Backend (for internal API calls - WebSocket, etc)
    "https://travel-companion-api-mrmr.onrender.com",
]
# Add additional origins via environment variable if needed
if os.environ.get('CORS_ALLOWED_ORIGINS'):
    CORS_ALLOWED_ORIGINS_PROD.extend(os.environ.get('CORS_ALLOWED_ORIGINS', '').split(','))

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
    'jazzmin',
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'channels',
    'corsheaders',

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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========================
# SECURITY HEADERS (Production)
# ========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
    }
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"

# ========================
# URLS & TEMPLATES
# ========================
ROOT_URLCONF = 'travel_companion.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

WSGI_APPLICATION = 'travel_companion.wsgi.application'

# ========================
# DATABASE (SQLite for dev, PostgreSQL for prod)
# ========================
if DEBUG:
    # Development: SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    # Production: PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'travel_companion_7ldf'),
            'USER': os.environ.get('DB_USER', 'travel_companion_7ldf_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'OkkQ8ZcsBTKdFfSQ7Wil2vA0iKDWxaQp'),
            'HOST': os.environ.get('DB_HOST', 'dpg-d7urmchj2pic73c6ocbg-a'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'ATOMIC_REQUESTS': True,
            'CONN_MAX_AGE': 600,  # Connection pooling
        }
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
    "site_title": "Travel Companion Admin",
    "site_header": "Travel Companion",
    "welcome_sign": "Welcome to Travel Companion Admin",
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.group": "fas fa-users",
    },
    "order_with_respect_to": [
        "auth",
        "users",
        "core",
        "trips",
        "expenses",
    ],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": True,
    "body_small_text": False,
    "brand_color": "#1e3a8a",
    "accent": "accent-primary",
    "rounded_corners": True,
}

# ========================
# PASSWORD VALIDATION
# ========================
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

# ========================
# INTERNATIONALIZATION
# ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

USE_I18N = True
USE_TZ = True

# ========================
# STATIC FILES (FIXED)
# ========================
STATIC_URL = "/static/"

# Your static files (CSS, JS, images)
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Collected static files (for deployment)
STATIC_ROOT = BASE_DIR / "staticfiles"

# ========================
# MEDIA FILES (UPLOADS)
# ========================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# ========================
# EMAIL CONFIGURATION (Gmail SMTP)
# ========================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@travelcompanion.com')

# ========================
# DEFAULT FIELD
# ========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# settings.py

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB (for file uploads)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'