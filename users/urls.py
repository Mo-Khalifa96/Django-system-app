from users import views 
from django.urls import path
from djoser.views import UserViewSet 
from core.utils import extend_schema_view, extend_schema
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView, 
                                            TokenVerifyView, TokenBlacklistView)



@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Obtain JWT Token Pair',
        description='Login to obtain access and refresh tokens'
    )
)
class TokenObtainPairView(TokenObtainPairView):
    pass

@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Refresh JWT Access Token',
        description='Refresh access token using refresh token'
    )
)
class TokenRefreshView(TokenRefreshView):
    pass

@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Verify JWT Token',
        description='Verify JWT token validity'
    )
)
class TokenVerifyView(TokenVerifyView):
    pass

@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Blacklist JWT Token',
        description='Blacklist refresh token (logout)'
    )
)
class TokenBlacklistView(TokenBlacklistView):
    pass


urlpatterns = [
    #JWT authentication urls
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),  
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='logout'), 

    #Account management urls
    # path('users/password-change/', UserViewSet.as_view({'post': 'set_password'}), name='password_change'),     #used by logged in users 
    # path('users/password-reset/', UserViewSet.as_view({'post': 'reset_password'}), name='password_reset'),   #used by logged out users (requires email)
    # path('users/reset-password/<uidb64>/<token>/', UserViewSet.as_view({'post': 'reset_password_confirm'}), name='password_reset_confirm'),

    #List/Create/Update/ Viewing and CRUD User urls 
    path('users/', views.ListUsersAPIView.as_view(), name='list_users'),
    path('users/new/', views.CreateUserAPIView.as_view(), name='create_user'),
    path('users/<uuid:id>/edit/', views.UpdateUserAPIView.as_view(), name='update_user'),
    path('users/<uuid:id>/delete/', views.DeleteUserAPIView.as_view(), name='delete_user')

]