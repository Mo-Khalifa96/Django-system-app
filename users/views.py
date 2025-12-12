from users.models import User 
from rest_framework import generics 
from core.utils import extend_schema
from users.permissions import SystemUserPermissions
from rest_framework.filters import SearchFilter, OrderingFilter
from users.serializers import BaseUserSerializer, CreateUserSerializer, UpdateUserSerializer, GetUserDetailSerializer


#List all users API view
@extend_schema(tags=['Users'])
class ListUsersAPIView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = BaseUserSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Users Data Table'
    ordering = ['-createdAt']
    search_fields = ['name']
    ordering_fields = ['name']
    filter_backends = [SearchFilter, OrderingFilter]


#Create new user API view
@extend_schema(tags=['Users'])
class CreateUserAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Update User'


#Update user API view
@extend_schema(tags=['Users'])
class UpdateUserAPIView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [SystemUserPermissions]
    required_permission = 'Update User'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return GetUserDetailSerializer
        else:
            return UpdateUserSerializer


#Delete user API view 
@extend_schema(tags=['Users'])
class DeleteUserAPIView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = BaseUserSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Delete User'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
