import os 
from .base import * 
import dj_database_url
from datetime import timedelta


#Production Security Key
SECRET_KEY = os.environ['PROD_SECRET_KEY']  

#Debugging mode off
DEBUG = False

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

SITE_PROTOCOL = os.getenv('SITE_PROTOCOL')
SITE_DOMAIN = os.getenv('SITE_DOMAIN')


#Database for production
DATABASES = {
    'default': dj_database_url.config()  #configure database from the DATABASE_URL env variable
}


#JWT's settings for authentication 
SIMPLE_JWT = {
            'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
            'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
            'ROTATE_REFRESH_TOKENS': False,  
            'BLACKLIST_AFTER_ROTATION': False,
            'UPDATE_LAST_LOGIN': True, 
            'AUTH_HEADER_TYPES': ('Bearer', ), 
        }


#CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')


#Security configurations 
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
