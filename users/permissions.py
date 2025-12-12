from rest_framework.permissions import BasePermission


class AdminOnly(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated: 
            if request.user.role != 'ADMIN':
                return False 
            else:
                return True
        else:
            return False 
    
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated: 
            if request.user.role != 'ADMIN':
                return False 
            else:
                return True
        else:
            return False 

class AdminOrAccountant: 
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated: 
            if request.user.role == 'SALES':
                return False 
            else: 
                return True 
        else:
            return False 
    
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated: 
            if request.user.role == 'SALES':
                return False 
            else: 
                return True 
        else:
            return False 


#System user-specific permission class with view-level permission mapping
class SystemUserPermissions(BasePermission):
    '''
    Generic permission class that gets the required permission from the view and checks
    it against user assigned permissions
    '''
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        elif request.user.role == 'ADMIN':
            return True 
    
        #Get required permission from view (if any)
        required_permission = getattr(view, 'required_permission', None)
        if required_permission:
            return request.user.has_special_permission(required_permission)
        return False 
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
