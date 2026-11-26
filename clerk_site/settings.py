import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY_FILE = BASE_DIR / ".secret_key"


def _load_secret_key():
    """Use an explicit environment value, or keep a generated key out of source control."""
    key = os.environ.get("DJANGO_SECRET_KEY")
    if key:
        return key

    if SECRET_KEY_FILE.exists():
        key = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key

    key = secrets.token_urlsafe(50)
    SECRET_KEY_FILE.write_text(key, encoding="utf-8")
    try:
        SECRET_KEY_FILE.chmod(0o600)
    except OSError:
        pass
    return key


SECRET_KEY = _load_secret_key()

DEBUG = True

# The app is intended for use by clerks on the local network.
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["http://*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "clerk",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "clerk_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "clerk_site.wsgi.application"
ASGI_APPLICATION = "clerk_site.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
