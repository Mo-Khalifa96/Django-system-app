import uuid 
from django.db import models
from core.validators import validate_phone_number
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField

#Define user manager 
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        #normalize email (i.e., lowercase, etc.)
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)        
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)

#USERS MODEL 
class User(AbstractBaseUser, PermissionsMixin):
    class UserRoles(models.TextChoices):
        ADMIN = 'ADMIN'
        SALES = 'SALES'
        ACCOUNTANT = 'ACCOUNTANT'

    #User account fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, validators=[validate_phone_number])
    role = models.CharField(max_length=10, choices=UserRoles.choices)
    userPermissions = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdAt = models.DateField(auto_now_add=True)

    USERNAME_FIELD = 'email'

    #fields for superusers 
    REQUIRED_FIELDS = ['name', 'phone', 'role']

    #Dictionary breaking down permissions by category 
    USER_PERMISSIONS_DICT = {
        #Users permissions
        'users': (
            'View Users Data Table',
            'Create New Users',
            'Update User',
            'Delete User',
        ),  
        #Clients permissions
        'clients': (
            'View Clients Data Table',
            'View Client Details',
            'Create New Clients',
            'Update Client',
            'Delete Client',
        ),

        #Units Permissions 
        'units': (
            'View Units Data Table',
            'View Unit Details',
            'Create Unit',
            'Update Unit',
            'Delete Unit',
        ),
        #Payments permissions
        'payment-plans': (
            'View Payment Plans Data Table',
            'Update Payment',
            'Create Invoice',
            'View Invoices'
        ),
        
        #Approvals permissions
        'approvals': (
            'View Approvals',
            'Approve Pending Units',
        ),
        #Default sidebar permissions 
        'sidebar': (
            'View Users Data Table',
            'View Clients Data Table',
            'View Units Data Table',
            'View Payment Plans Data Table',
            'View Approvals',
        )
    }

    #User permissions tuple 
    USER_PERMISSIONS = tuple(
        perm for category, permissions in USER_PERMISSIONS_DICT.items() 
        if category != 'sidebar'
        for perm in permissions
    )

    #Default permissions for each role
    DEFAULT_ROLE_PERMISSIONS = {
        'ADMIN': list(USER_PERMISSIONS),  #Admin gets all permissions
        'SALES': [
            perm for perm in USER_PERMISSIONS 
            if perm not in ('View Users Data Table', 'Create New Users', 'Update User', 'Delete User',
                            'Delete Unit', 'View Payment Plans Data Table', 'Update Payment', 
                            'Create Invoice', 'View Invoices', 'View Approvals', 'Approve Pending Units')
            ],
        'ACCOUNTANT': [
            perm for perm in USER_PERMISSIONS
            if perm not in ('View Users Data Table', 'Create New Users', 'Update User', 'Delete User',
                            'Delete Unit', 'View Approvals', 'Approve Pending Units')
            ],
    }


    objects = UserManager()

    all_objects = models.Manager()    

    class Meta:
        db_table = 'Users_table'
        verbose_name_plural = 'Users'
        ordering = ['name']

    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        #Set default permissions based on role if userPermissions is empty
        if not self.userPermissions and self.role:
            self.userPermissions = self.DEFAULT_ROLE_PERMISSIONS.get(self.role, [])

        elif self.userPermissions and isinstance(self.userPermissions, list):
            self.userPermissions = self.format_array(self.userPermissions)

        super().save(*args, **kwargs)

    @staticmethod
    def format_array(array):
        if not array:
            return '{}'
        array = [f'"{val}"' for val in array]  
        return '{' + ','.join(array) + '}'
    
    def has_special_permission(self, permission):
        '''Check if user has a specific custom permission'''
        if self.role == 'ADMIN':
            return True
        return permission in self.userPermissions

    def get_user_permissions(self, perm_category=None):
        '''Get user permissions (by category) for API responses'''
        if not perm_category:
            perm_category = 'sidebar'
        available_permissions = list(self.USER_PERMISSIONS_DICT['sidebar']) + list(self.USER_PERMISSIONS_DICT[perm_category])
        available_permissions = list(dict.fromkeys(available_permissions))
        return {permission: permission in self.userPermissions 
                for permission in available_permissions
            }

