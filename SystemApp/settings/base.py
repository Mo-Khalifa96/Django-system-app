import os 
from pathlib import Path
from dotenv import load_dotenv
from .filters import RequestsFilter, DjangoQFilter


#Build paths inside the project like this: BASE_DIR/'sub-dir'
BASE_DIR = Path(__file__).resolve().parents[2]

#Load environment
dotenv_path = BASE_DIR / '.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)   #consider using python-decouple instead of doing all this to load env variables


#Apps list 
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'users',
    'core.apps.CoreConfig',
    'rest_framework_simplejwt',
    'rest_framework',
    'django_filters',
    'corsheaders',
    'django_q',
    'djoser',
]

#Middlewares
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

#Root urls 
ROOT_URLCONF = 'SystemApp.urls'

#Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SystemApp.wsgi.application'


#Default User model 
AUTH_USER_MODEL = 'users.User'


#Set password reset time out 
PASSWORD_RESET_TIMEOUT = 60*60*12  # 12 hours in seconds: 43200


#Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,   
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'users.validators.NumberRequiredValidator',  
    },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
]


#Internationalization
LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', 'English'),
    ('ar', 'Arabic'),   #to enable translation, 1) run: 'django-admin makemessages -l ar', 2) edit the file, then 3) run 'django-admin compilemessages'
]

LOCALE_PATHS = [    
    BASE_DIR / 'locale',                 
]


TIME_ZONE = 'Africa/Cairo'

USE_I18N = True

USE_TZ = True  


#Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

#URL to access the uploaded media 
MEDIA_URL = '/media/'

#Root paths for static and media files (as derivative from the base directory)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


#Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


#Django-Q2 Configurations
Q_CLUSTER = {
    'name': 'SystemApp',
    'label': 'System Tasks',  
    'redis': None,  #don't use redis as message broker 
    'orm': 'default',  #use current DB as the message broker 
    'workers': 1,   #NOTE: adjust this based on your server's cores
    'timeout': 120,    #max time a task can take before being killed 
    'retry': 300,     #retry failed tasks after 5 minutes (in seconds)
    'max_attempts': 5,  #retry failed tasks up to 5 times
    'compress': True,   #allow data compression
    'save_limit': 120,   #limits number of results to 120; removes earlier ones 
    'recycle': 100,   #number of tasks a worker can handle before being restarted (to cleanup memory)
    'queue_limit': 20,   #maximum number of tasks that can be waiting in the queue at any time
    'ack_failures': True,   #acknoweldge failures 
}


#Django REST's settings 
REST_FRAMEWORK = {
            'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
            'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],

            #Custom paginator           
            'DEFAULT_PAGINATION_CLASS': 'core.pagination.PageNumberPaginationWithPermissions',
            'PAGE_SIZE': 25,   

            'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 
                                         'rest_framework.throttling.UserRateThrottle'],
            
            'DEFAULT_THROTTLE_RATES': {
                'anon': '200/hour',   #TODO - for production, change to 50 or 100
                'user': '1000/hour',  
            },
        }


#Configure Djoser's settings
DJOSER = {
    'LOGIN_FIELD': 'email',    
    'TOKEN_MODEL': None,   #None uses JWT authentication
    'HIDE_USERS': False,
    'SET_PASSWORD_RETYPE': True, 
    'PASSWORD_RESET_CONFIRM_RETYPE': True,
    'LOGOUT_ON_PASSWORD_CHANGE': True,  

    #email-related settings   
    'SEND_ACTIVATION_EMAIL': False,  
    'SEND_PASSWORD_RESET_EMAIL': False,   #sends password reset link 
    'SEND_PASSWORD_CHANGED_EMAIL': False,  #sends confirmation email after reset (by unauthorized users)
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': False, #sends confirmation email after reset (by authorized users)

    #url pattern for password resets
    'PASSWORD_RESET_CONFIRM_URL': 'api/users/password-reset/{uidb64}/{token}/',

    #Serializers settings 
    'SERIALIZERS': {
        'set_password': 'djoser.serializers.SetPasswordRetypeSerializer',
        'password_reset': 'djoser.serializers.SendEmailResetSerializer',
        'password_reset_confirm': 'djoser.serializers.PasswordResetConfirmRetypeSerializer',
    },

}


#Configure the logger 
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  
    'formatters': {
        'verbose': {   #used for the logging files 
            'format': '(%(asctime)s) [%(levelname)s] - \'%(name)s\':  %(message)s',
            'datefmt': '%d/%m/%Y %H:%M:%S',
        },
        'simple': {    #to be used for console only
            'format': '[%(asctime)s] %(levelname)s - \'%(name)s\':  %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['ignore_requests']
        },
        'general_file': {
            'class': 'logging.handlers.RotatingFileHandler',  
            'filename': f'{BASE_DIR}/logs/general.log',
            'filters': ['ignore_requests'],
            'formatter': 'verbose',   
            'level': 'DEBUG',
            'maxBytes': 10 * 1024 * 1024,  #10MB max file size
            'backupCount': 5,  
            'encoding': 'utf-8'
        },
        'errors_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{BASE_DIR}/logs/errors.log',
            'filters': ['ignore_requests'],
            'formatter': 'verbose',
            'level': 'ERROR',   #only ERROR and CRITICAL are logged
            'maxBytes': 10*1024*1024,   #10MB max file size
            'backupCount': 5,
            'encoding': 'utf-8'
        }
    },
    'filters': {
        'ignore_requests': {
            '()': RequestsFilter,
        },
        'django_q_filter': {
            '()': DjangoQFilter,
        },
    },
    #configure loggers
    'loggers': {
        #configure root logger
        '': {  
            'handlers': ['console', 'general_file', 'errors_file'],
            'level': 'WARNING',  
            'propagate': False,
        },

        #configure django's logger 
        'django': { 
            'handlers': ['console', 'general_file', 'errors_file'],
            'level': 'WARNING', 
            'propagate': False,
        },

        'django.request': {
            'handlers': ['console', 'general_file', 'errors_file'],
            # 'filters': ['ignore_requests'],   #no need; it's activated globally
            'level': 'WARNING',
            'propagate': False,
        },

        #configure Django-Q's logger
        'django-q': {   
            'handlers': ['console', 'general_file', 'errors_file'],
            'filters': ['django_q_filter'],
            'level': 'INFO', 
            'propagate': False,
        },

        #override logger for core module
        'core': {
            'handlers': ['console', 'general_file', 'errors_file'],
            'filters': ['django_q_filter'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


#Check whether to use swagger (remove later and switch to dev.py)
ENABLE_SWAGGER = os.getenv('ENABLE_SWAGGER', 'False') == 'True'
if ENABLE_SWAGGER:
    REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'
    INSTALLED_APPS += ['drf_spectacular']
    #Swagger settings
    SPECTACULAR_SETTINGS = {
        'TITLE': 'API Endpoints',
        'VERSION': '1.0.0',
        'DESCRIPTION': 'API docs',
        'SERVE_INCLUDE_SCHEMA': False,
        'SECURITY': [
            {'BearerAuth': []}
        ],
        'TAGS': [
            {'name': 'Auth', 'description': 'JWT Authentication endpoints'},
            {'name': 'Users', 'description': 'User management'},
            {'name': 'Dashboard', 'description': 'Dashboard analytics and metrics'},
            {'name': 'Clients', 'description': 'Client management'},
            {'name': 'Units', 'description': 'Unit management'},
            {'name': 'Payment Plans', 'description': 'Payments and payment plans management'},
            {'name': 'Invoices', 'description': 'Invoices management'},
            {'name': 'Approvals', 'description': 'Unit approval management'},
            {'name': 'Audit Logs', 'description': 'System audit trails and logging'},
        ],
        'COMPONENT_SPLIT_REQUEST': True,
        'SORT_OPERATION_PARAMETERS': False, 
        'POSTPROCESSING_HOOKS': [
            'core.swagger.response_structure_postprocessing_hook',
        ],
        'ENUM_NAME_OVERRIDES': {
            'StatusChoicesEnum': 'core.models.Unit.UnitStatusChoices', 
            'FloorChoicesEnum': 'core.models.Unit.FloorChoices', 
            'ActivityChoicesEnum': 'core.models.Unit.UnitActivities',
        },
        'COMPONENTS': {
            'securitySchemes': {
                'BearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                    'description': 'JWT Authorization token (paste token directly).\nFormat: <access_token> ',
                },
            }
        },
    }


