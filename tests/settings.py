import os

SECRET_KEY = 'roverdotcom'
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
ROOT_URLCONF = []

test_database = os.environ.get('TEST_DATABASE', 'sqlite')

if test_database == 'mysql':
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
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3'
        }
    }
