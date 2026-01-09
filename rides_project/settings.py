
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")

#DEBUG = os.getenv("DJA
# NGO_DEBUG", "True") == "True"
DEBUG = 'FALSE'

ALLOWED_HOSTS = ["*"]

# CSRF trusted origins: supply a comma-separated list of origins (including scheme)
# e.g. DJANGO_CSRF_TRUSTED_ORIGINS=https://abcd1234.ngrok.io,https://example.com
csrf_origins = os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if csrf_origins:
    CSRF_TRUSTED_ORIGINS = [s.strip() for s in csrf_origins.split(',') if s.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

# When running behind a proxy (ngrok etc) it's useful to honour the X-Forwarded-Proto header
# so Django knows requests were originally HTTPS. Only enable if your proxy sets this header.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # third party
    "rest_framework",

    # local
    "rides",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware"
]

ROOT_URLCONF = "rides_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rides_project.wsgi.application"

# Database
""" DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "rides_db"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
} """

# DATABASES: prefer DATABASE_URL, then Postgres env vars, then sqlite fallback
if os.getenv("DB_ENGINE", "").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
    elif os.getenv("DB_NAME"):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.getenv("DB_NAME"),
                "USER": os.getenv("DB_USER", ""),
                "PASSWORD": os.getenv("DB_PASSWORD", ""),
                "HOST": os.getenv("DB_HOST", "localhost"),
                "PORT": os.getenv("DB_PORT", "5432"),
            }
        }
    else:
        # final fallback to local sqlite
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(BASE_DIR / "db.sqlite3"),
            }
        }

# Optional: allow a simple sqlite fallback for local development and tests.
# Set the environment variable DB_ENGINE=sqlite to enable this.
if os.getenv('DB_ENGINE', '').lower() == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Email
# In development prefer the console backend to avoid real SMTP/TLS issues.
if DEBUG:
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
else:
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "enquiries@easytransit.co.zw")

# Google Maps
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
# Cache timeout for distance results (seconds)
GOOGLE_DISTANCE_CACHE_TIMEOUT = int(os.getenv("GOOGLE_DISTANCE_CACHE_TIMEOUT", str(6 * 3600)))

# Paynow
PAYNOW_INTEGRATION_ID = os.getenv("PAYNOW_INTEGRATION_ID", "")
PAYNOW_INTEGRATION_KEY = os.getenv("PAYNOW_INTEGRATION_KEY", "")
PAYNOW_RETURN_URL = os.getenv("PAYNOW_RETURN_URL", "http://localhost:8000/rides/paynow/return/")
PAYNOW_RESULT_URL = os.getenv("PAYNOW_RESULT_URL", "http://localhost:8000/rides/paynow/result/")
# Whether to verify TLS certs when contacting Paynow (set False for local troubleshooting only)
PAYNOW_VERIFY_SSL = os.getenv("PAYNOW_VERIFY_SSL", "True") == "True"
# Merchant email to use for authemail (important in Paynow test mode)
PAYNOW_MERCHANT_EMAIL = os.getenv("PAYNOW_MERCHANT_EMAIL", os.getenv("TAXI_OWNER_EMAIL", "enquiries@easytransit.co.zw"))

# Taxi owner contact (defaults to easytransit from user input)
TAXI_OWNER_EMAIL = os.getenv("TAXI_OWNER_EMAIL", "enquiries@easytransit.co.zw")
TAXI_OWNER_PHONE = os.getenv("TAXI_OWNER_PHONE", "+263789423154")

# Pricing constants
PRICING = {
    "MIN_DISTANCE_KM": 13.0,
    "BRACKETS": [
        {"min": 13, "max": 15, "price": 25.0},
        {"min": 16, "max": 20, "price": 30.0},
        {"min": 21, "max": 25, "price": 35.0},
        {"min": 26, "max": 35, "price": 40.0},
    ],
    # For distance above 35 km, charge $40 + 1.30*(distance-35)
    "ABOVE_35_PER_KM": 1.30,
    "EXTRA_ADULT_FEE": 10.0,
    "KID_SEATED_FACTOR": 0.5,
    "LUGGAGE_FEE": 5.0,
}

# Use JSONField default for Django < 3.1 alternative
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
