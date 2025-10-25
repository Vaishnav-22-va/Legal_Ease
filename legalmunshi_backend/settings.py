from pathlib import Path
import os

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = BASE_DIR / 'staticfiles'

SECRET_KEY = 'jyrj9+#u!o_d%t6k$r+487=qewkro0ym7p89x%ks*o!ps7e0!)'
DEBUG = True
ALLOWED_HOSTS = ['*']


# ---------------------------------------------------------
# ✅ Application definition
# ---------------------------------------------------------
# In your settings.py file

INSTALLED_APPS = [
    # Admin theme (should be first)
    'jazzmin',
    
    # Django's built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'import_export',
    
    # Your custom apps
    'accounts',
    'partner',
    'services',
    'admin_panel',
    'payments',
    
    # Your core app should be last so its script runs after all other apps are loaded
    'core.apps.CoreConfig',

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
]

ROOT_URLCONF = 'legalmunshi_backend.urls'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.CaseInsensitiveAuthBackend',  # or 'myapp.backends.CaseInsensitiveAuthBackend'
]

AUTH_USER_MODEL = 'accounts.CustomUser'


# ---------------------------------------------------------
# ✅ Templates
# ---------------------------------------------------------
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
                'services.context_processors.navbar_categories',

            ],
        },
    },
]

WSGI_APPLICATION = 'legalmunshi_backend.wsgi.application'


# ---------------------------------------------------------
# ✅ Database
# ---------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://legalmunshi_db_user:6xuVWkzFMsYfnTaHjcRMUgvmHB7f5Iol@dpg-d3ucl0ali9vc73c0og0g-a.oregon-postgres.render.com/legalmunshi_db',
        conn_max_age=600,
        ssl_require=True
    )
}



# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------
# ✅ Password Validation
# ---------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    #{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    #{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------
# ✅ Internationalization
# ---------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------
# ✅ Static and Media
# ---------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # ✅ for dev static files

# ---------------------------------------------------------
# ✅ Custom User Model
# ---------------------------------------------------------
#AUTH_USER_MODEL = 'accounts.CustomUser'

# ---------------------------------------------------------
# ✅ Login Redirect
# ---------------------------------------------------------
LOGIN_URL = '/login/'

# ---------------------------------------------------------
# ✅ Default PK field
# ---------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


#Email OTP Setup
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = ""       # your Gmail
EMAIL_HOST_PASSWORD = "hlba gfcj zqgm pdzk"      # Gmail App Password

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER              # sender shown in inbox
SERVER_EMAIL = EMAIL_HOST_USER

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True


