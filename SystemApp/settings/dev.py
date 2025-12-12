import os
from .base import *
from datetime import timedelta

#Development Security Key
SECRET_KEY = os.environ['DEV_SECRET_KEY']

#DEBUG mode enabled 
DEBUG = True

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

SITE_PROTOCOL = 'http'
SITE_DOMAIN = 'localhost:8000'


#Flag to check if application is dockerized or not 
IS_DOCKERIZED = os.getenv('IS_DOCKERIZED', 'false').lower() == 'true'


#Apps and middleware used only in development 
INSTALLED_APPS += [
                    'debug_toolbar', 
                    # 'drf_spectacular',
                    'silk', 
                    ]

MIDDLEWARE += [
               'debug_toolbar.middleware.DebugToolbarMiddleware', 
               'silk.middleware.SilkyMiddleware',
               ]

# REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'


#Internal IPS for Debug Toolbar
INTERNAL_IPS = [
    '127.0.0.1',   
]

#Development database 
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',   
        'NAME': os.environ['DB_NAME'], 
        'USER': os.environ['DB_USER'], 
        'PASSWORD': os.environ['DB_PASSWORD'], 
        'HOST': 'postgres' if IS_DOCKERIZED else 'localhost',
        'PORT': os.environ['DB_PORT'],
        'CONN_MAX_AGE': 60,  
        'CONN_HEALTH_CHECKS': True, 
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}


#Simple JWT configuration
SIMPLE_JWT = {
            'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
            'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
            'ROTATE_REFRESH_TOKENS': False,  
            'BLACKLIST_AFTER_ROTATION': False, 
            'UPDATE_LAST_LOGIN': True, 
            'AUTH_HEADER_TYPES': ('Bearer', ), 
        }


#CORS configuration for development 
CORS_ALLOW_ALL_ORIGINS = True

#Disable timezone support in development
USE_TZ = False 




# #Swagger settings
# SPECTACULAR_SETTINGS = {
#     'TITLE': 'API Endpoints',
#     'VERSION': '1.0.0',
#     'DESCRIPTION': 'API docs',
#     'SERVE_INCLUDE_SCHEMA': False,
#     'SECURITY': [
#         {'BearerAuth': []}
#     ],
#     'TAGS': [
#         {'name': 'Auth', 'description': 'JWT Authentication endpoints'},
#         {'name': 'Users', 'description': 'User management'},
#         {'name': 'Dashboard', 'description': 'Dashboard analytics and metrics'},
#         {'name': 'Clients', 'description': 'Client management'},
#         {'name': 'Units', 'description': 'Unit management'},
#         {'name': 'Payment Plans', 'description': 'Payments and payment plans management'},
#         {'name': 'Invoices', 'description': 'Invoices management'},
#         {'name': 'Approvals', 'description': 'Unit approval management'},
#         {'name': 'Audit Logs', 'description': 'System audit trails and logging'},
#     ],
#     'COMPONENT_SPLIT_REQUEST': True,
#     'SORT_OPERATION_PARAMETERS': False, 
#     'POSTPROCESSING_HOOKS': [
#         'core.swagger.response_structure_postprocessing_hook',
#     ],
#     'ENUM_NAME_OVERRIDES': {
#         'StatusChoicesEnum': 'core.models.Unit.UnitStatusChoices', 
#         'FloorChoicesEnum': 'core.models.Unit.FloorChoices', 
#         'ActivityChoicesEnum': 'core.models.Unit.UnitActivities',
#     },
#     'COMPONENTS': {
#         'securitySchemes': {
#             'BearerAuth': {
#                 'type': 'http',
#                 'scheme': 'bearer',
#                 'bearerFormat': 'JWT',
#                 'description': 'JWT Authorization token (paste token directly).\nFormat: <access_token> ',
#             },
#         }
#     },
# }


