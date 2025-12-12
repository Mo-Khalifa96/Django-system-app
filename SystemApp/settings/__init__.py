import os

#Select environment
ENV = os.environ.get('DJANGO_SETTINGS_MODULE', 'SystemApp.settings.dev')   

#Import settings from the selected environment file
if ENV == 'SystemApp.settings.prod':
    from .prod import *
elif ENV == 'SystemApp.settings.dev':
    from .dev import *
else:
    #fallback or raise an error for unknown settings module
    raise ImportError(f"Unknown DJANGO_SETTINGS_MODULE: {ENV}")

#additional validation 
if os.environ.get('DJANGO_SETTINGS_MODULE') == 'SystemApp.settings.prod':
    if not ALLOWED_HOSTS:
        raise Exception("ALLOWED_HOSTS must be set in production!")
