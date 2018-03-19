import os

SECRET_KEY = 'roverdotcom'
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
ROOT_URLCONF = []

TEST_DATABASE = os.environ.get('TEST_DATABASE', 'sqlite')

if TEST_DATABASE == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'testdb',
            'USER': 'travis',
            'PASSWORD': '',
            'HOST': '127.0.0.1',
            'PORT': 3306,
        }
    }
if TEST_DATABASE == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'testdb',
            'USER': 'postgres',
            'PASSWORD': '',
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
