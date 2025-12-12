import re
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination, CursorPagination

#Define a custom page paginator
class CustomPageNumberPagination(PageNumberPagination):
    page_size = 25
    page_query_param = 'page'
    page_size_query_param = 'page_size' 
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'pagination': {
                'count': self.page.paginator.count,    
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'results': data
        })


class PageNumberPaginationWithPermissions(PageNumberPagination):
    page_size = 25
    page_query_param = 'page'
    page_size_query_param = 'page_size' 
    max_page_size = 100
    
    def get_category_from_url(self, request):
        """Extract permission category from URL path"""
        request_path = request.path
        
        category_patterns = {
            r'/units/approvals/': 'approvals',
            r'/payment-plans/': 'payment-plans',
            r'/units/': 'units', 
            r'/clients/': 'clients', 
            r'/users/': 'users',
        }
        
        for pattern, category in category_patterns.items():
            if re.search(pattern, request_path):
                return category
        return None

    def get_paginated_response(self, data):
        #Get user permissions
        user_permissions = 'N/A'
        if self.request and self.request.user:
            category = self.get_category_from_url(self.request)
            user_permissions = self.request.user.get_user_permissions(category)

        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'pagination': {
                'count': self.page.paginator.count,    
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'metadata': {
                'userPermissions': user_permissions
            },
            'results': data
        })

    
#Define a custom cursor paginator 
class AuditLogsPaginator(CursorPagination):
    page_size = 25 
    ordering = '-createdAt' 
    cursor_query_param = 'cursor'
