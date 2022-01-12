import os

SECRET_KEY = 'roverdotcom'
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'user_profile',
]
ROOT_URLCONF = []
USE_TZ = False

TEST_DATABASE = os.environ.get('TEST_DATABASE', 'sqlite')

if TEST_DATABASE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'testdb',
            'USER': 'user',
            'PASSWORD': 'password',
            'HOST': '127.0.0.1',
            'PORT': 33306,
        }
    }
elif TEST_DATABASE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'testdb',
            'USER': 'postgres',
            'PASSWORD': 'postgres',
            'HOST': '127.0.0.1',
            'PORT': 5432,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3'
        }
    }
