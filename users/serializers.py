import json
from users.models import User
from django.db import transaction
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from core.utils import extend_schema_serializer, OpenApiExample


#Base user serializer 
class BaseUserSerializer(serializers.ModelSerializer):
    createdAt = serializers.DateField(format='%d/%m/%Y', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'createdAt']


#Create user serializer
class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    createdAt = serializers.DateField(format='%d/%m/%Y', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'password', 'password2', 'createdAt']
        extra_kwargs = {'id': {'read_only': True}, 'createdAt': {'read_only': True}}
    
    def get_fields(self):
        fields = super().get_fields() 
        request = self.context.get('request')
        if getattr(request.user, 'role', None) != 'ADMIN':
            fields.pop('role', None)
        return fields 
    
    def validate(self, data):
        '''Validates passwords during user creation.'''
        password = data.get('password')
        password2 = data.get('password2')

        if not password or not password2:
            raise serializers.ValidationError({'password2': _('Both password fields are required.')})
        if password != password2:
            raise serializers.ValidationError({'password2': _('Passwords do not match.')})
        try:
            #validate password 
            validate_password(password)
        except ValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        
        return data 

    @transaction.atomic 
    def create(self, validated_data):
        #handle user's password 
        password = validated_data.pop('password', None)   #get password
        validated_data.pop('password2', None)   #Remove password 2 

        #Create new user 
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user 


#Nested serializer for user permissions
class UserPermissionsSerializer(serializers.Serializer):
    permission = serializers.CharField(required=True)
    enabled = serializers.BooleanField(required=True)

#Update user serializer
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Admin Request',
            request_only=True,
            description='Request with role and permissions (admin only)',
            value={
                'name': 'John Smith',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'role': 'SALES',
                'password': 'newpassword123',
                'permissions': [
                        {"permission": "View Users Data Table","enabled": True},
                        {"permission": "Create New Users","enabled": False},
                        {"permission": "Update User","enabled": True},
                        {"permission": "Delete User","enabled": False},
                        {"permission": "Create New Clients","enabled": True},
                        {"permission": "View Client Details","enabled": True},
                        {"permission": "Update Client","enabled": True},
                        {"permission": "Delete Client","enabled": True},
                        {"permission": "View Units Data Table","enabled": True},
                        {"permission": "View Unit Details","enabled": True},
                        {"permission": "Create Unit","enabled": True},
                        {"permission": "Update Unit","enabled": True},
                        {"permission": "Delete Unit","enabled": False},
                        {"permission": "View Payment Plans Data Table","enabled": True},
                        {"permission": "Update Payment","enabled": False},
                        {"permission": "Create Invoice","enabled": False},
                        {"permission": "View Invoice","enabled": False},
                        {"permission": "View Approvals","enabled": False},
                        {"permission": "Approve Pending Units","enabled": False}
                ]
            }
        ),
        OpenApiExample(
            name='Non-Admin Request', 
            request_only=True,
            description='Request without role and permissions fields (non-admin users)',
            value={
                'name': 'John Smith',
                'email': 'john@example.com', 
                'phone': '+1234567890',
                'password': 'newpassword123'
            }
        ),
        OpenApiExample(
            name='Response',
            response_only=True,
            description='Response',
            value={
                'id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'name': 'John Smith',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'role': 'SALES',
                'permissions': [
                        {"permission": "View Users Data Table","enabled": True},
                        {"permission": "Create New Users","enabled": False},
                        {"permission": "Update User","enabled": True},
                        {"permission": "Delete User","enabled": False},
                        {"permission": "Create New Clients","enabled": True},
                        {"permission": "View Client Details","enabled": True},
                        {"permission": "Update Client","enabled": True},
                        {"permission": "Delete Client","enabled": True},
                        {"permission": "View Units Data Table","enabled": True},
                        {"permission": "View Unit Details","enabled": True},
                        {"permission": "Create Unit","enabled": True},
                        {"permission": "Update Unit","enabled": True},
                        {"permission": "Delete Unit","enabled": False},
                        {"permission": "View Payment Plans Data Table","enabled": True},
                        {"permission": "Update Payment","enabled": False},
                        {"permission": "Create Invoice","enabled": False},
                        {"permission": "View Invoice","enabled": False},
                        {"permission": "View Approvals","enabled": False},
                        {"permission": "Approve Pending Units","enabled": False}
                ]
            }
        ),
    ]
)
class UpdateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    permissions = UserPermissionsSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'permissions', 'password']
        extra_kwargs = {'id': {'read_only': True}, 'name': {'required': False}, 'email': {'required': False}, 
                        'phone': {'required': False}, 'role': {'required': False}}
    
    def get_fields(self):
        fields = super().get_fields() 
        request = self.context.get('request')
        if getattr(request.user, 'role', None) != 'ADMIN':
            fields.pop('role', None)
            fields.pop('permissions', None)
        return fields 

    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''
        data_preprocessed = {}
        for field in data:
            #Non-admins should not be able to pass permissions or role
            if getattr(self.context.get('request').user, "role", None) != "ADMIN" and field in ('role', 'permissions'):
                continue 

            if field != 'permissions':
                data_preprocessed[field] = data[field]
            else:
                if isinstance(data.get(field), str):
                    try:
                        data_preprocessed[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({field: 'Invalid JSON format'})
                else:
                    data_preprocessed[field] = data[field]
        return super().to_internal_value(data_preprocessed)


    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['permissions'] = [
            {'permission': permission,
                'enabled': permission in instance.userPermissions,
            } for permission in User.USER_PERMISSIONS
        ]
        return rep 
    
    
    #validate user password 
    def validate_password(self, password):
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise serializers.ValidationError(exc.messages)
        return password 
    

    @transaction.atomic 
    def update(self, instance, validated_data):
        #Single out password and user permissions and update the rest
        password = validated_data.pop('password', None)
        assigned_permissions = validated_data.pop('permissions', None)

        #Track fields to update 
        update_fields = []
        
        #Update basic fields
        for field, value in validated_data.items():
            if hasattr(instance, field) and value:
                setattr(instance, field, value)
                update_fields.append(field)

        #Hash password (if updated)
        if password:
            instance.set_password(password)
            update_fields.append('password')
  
        #Handle user permission updates
        if assigned_permissions:
            user_permissions_lst = instance.userPermissions
            allowed_permissions = {perm.get('permission') for perm in assigned_permissions if perm.get('enabled')}
            disallowed_permissions = {perm.get('permission') for perm in assigned_permissions if not perm.get('enabled')}

            #Determine added and removed permissions
            added_permissions = allowed_permissions.difference(set(user_permissions_lst))
            removed_permissions = set(user_permissions_lst).intersection(disallowed_permissions)

            #Add new allowed permissions 
            if added_permissions:
                instance.userPermissions = user_permissions_lst + list(added_permissions)
                update_fields.append('userPermissions')

            #remove disallowed permissions 
            if removed_permissions:
                instance.userPermissions = list(set(user_permissions_lst).difference(removed_permissions))
                if 'userPermissions' not in update_fields:
                    update_fields.append('userPermissions')
        
        #save user 
        instance.save(update_fields=update_fields)
        return instance 


@extend_schema_serializer(   #TODO - no need for this separation; it's a Get request
    examples=[
        OpenApiExample(
            name='Admin Response',
            response_only=True,
            description='Response with role and permissions (admin only)',
            value={
                'id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'name': 'John Smith',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'role': 'SALES',
                'permissions': [
                        {"permission": "View Users Data Table","enabled": True},
                        {"permission": "Create New Users","enabled": False},
                        {"permission": "Update User","enabled": True},
                        {"permission": "Delete User","enabled": False},
                        {"permission": "Create New Clients","enabled": True},
                        {"permission": "View Client Details","enabled": True},
                        {"permission": "Update Client","enabled": True},
                        {"permission": "Delete Client","enabled": True},
                        {"permission": "View Units Data Table","enabled": True},
                        {"permission": "View Unit Details","enabled": True},
                        {"permission": "Create Unit","enabled": True},
                        {"permission": "Update Unit","enabled": True},
                        {"permission": "Delete Unit","enabled": False},
                        {"permission": "View Payment Plans Data Table","enabled": True},
                        {"permission": "Update Payment","enabled": False},
                        {"permission": "Create Invoice","enabled": False},
                        {"permission": "View Invoice","enabled": False},
                        {"permission": "View Approvals","enabled": False},
                        {"permission": "Approve Pending Units","enabled": False}
                ],
                'metadata': {
                    'userPermissions': {
                        "View Users Data Table": True,
                        "View Clients Data Table": True,
                        "View Units Data Table": True,
                        "View Payment Plans Data Table": True,
                        "View Approvals": True,
                        "Create New Users": True,
                        "Update User": True,
                        "Delete User": True
                    }
                }
            }
        ),
        OpenApiExample(
            name='Non-Admin Response', 
            response_only=True,
            description='Response without role and permissions fields (non-admin users)',
            value={
                'id': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'name': 'John Smith',
                'email': 'john@example.com', 
                'phone': '+1234567890',
                'password': 'newpassword123',
                'metadata': {
                    'userPermissions': {
                        "View Users Data Table": False,
                        "View Clients Data Table": True,
                        "View Units Data Table": True,
                        "View Payment Plans Data Table": False,
                        "View Approvals": False,
                        "Create New Users": False,
                        "Update User": False,
                        "Delete User": False
                    }
                }
            }
        )
    ]
)
class GetUserDetailSerializer(serializers.ModelSerializer):
    permissions = UserPermissionsSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'permissions']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        rep['permissions'] = [
            {'permission': permission,
                'enabled': permission in instance.userPermissions,
            } for permission in User.USER_PERMISSIONS
        ]
        rep['metadata'] = {
                'userPermissions': request.user.get_user_permissions()
            }
        return rep

