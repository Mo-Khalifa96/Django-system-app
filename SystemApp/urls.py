import os 
from django.conf import settings 
from django.urls import path, include 
from django.http import HttpResponse
from django.conf.urls.static import static 


#url patterns 
urlpatterns = [
    path('api/', include('users.urls')),
    path('api/', include('core.urls')),
    path('', lambda request: HttpResponse('HOME')),
    path('health/', lambda request: HttpResponse('OK')),
]

if settings.DEBUG: 
    import debug_toolbar 
    # from drf_spectacular.views import (
    #     SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
    # )

    #development paths 
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),  
        path('silk/', include('silk.urls', namespace='silk')),
        # path('swagger/schema/', SpectacularAPIView.as_view(), name='schema'),
        # path('swagger/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        # path('swagger/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  
    ]



####
#Check whether to use swagger
ENABLE_SWAGGER = os.getenv('ENABLE_SWAGGER', 'False') == 'True'
if ENABLE_SWAGGER:
    from drf_spectacular.views import (
        SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
    )

    urlpatterns += [
        path('swagger/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('swagger/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('swagger/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
####


#Serve media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

