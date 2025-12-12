from django.conf import settings

#For drf-spectacular documentation
if True:   #TODO - change to this: settings.DEBUG
    import re 
    from users.models import User
    from rest_framework import filters
    from django_filters import ChoiceFilter
    from django_filters.rest_framework import DjangoFilterBackend
    from drf_spectacular.extensions import OpenApiFilterExtension

    class ChoicesFilterExtension(OpenApiFilterExtension):
        '''Extension for handling ChoiceFilter with dynamic choices'''
        target_class = 'django_filters.rest_framework.DjangoFilterBackend'
        priority = 3
        
        def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
            '''Override to handle choice filters with dynamic choices'''
            
            parameters = []
            
            #Get the filterset class
            if hasattr(auto_schema.view, 'filterset_class'):
                filterset_class = auto_schema.view.filterset_class
            else:
                filter_backend = DjangoFilterBackend()
                filterset_class = filter_backend.get_filterset_class(
                    auto_schema.view, 
                    auto_schema.view.get_queryset()
                )
            
            if filterset_class:
                #Create filterset instance to access dynamic choices
                try:
                    filterset_instance = filterset_class(queryset=auto_schema.view.get_queryset())
                except:
                    filterset_instance = filterset_class()
                
                for filter_name, filter_field in filterset_instance.filters.items():
                    parameter = self._get_filter_parameter(filter_name, filter_field)
                    if parameter:
                        parameters.append(parameter)
            
            return parameters
        
        def _get_filter_parameter(self, filter_name, filter_field):
            '''Convert a django-filter field to an OpenAPI parameter'''
            
            #Handle ChoiceFilter with dynamic choices
            if isinstance(filter_field, ChoiceFilter):
                choices = []
                
                #Get choices from the field
                if hasattr(filter_field.field, 'choices') and filter_field.field.choices:
                    if callable(filter_field.field.choices):
                        try:
                            choices = list(filter_field.field.choices())
                        except:
                            choices = []
                    else:
                        choices = list(filter_field.field.choices)
                
                #Extract choice values
                enum_values = [str(choice[0]) for choice in choices if choice[0]] if choices else None
                description = f'<b>Filter by {filter_name}</b>'
                
                if choices and len(choices) <= 6:
                    choice_descriptions = [f'* `{choice[0]}` - {choice[1]}' for choice in choices if choice[0]]
                    if choice_descriptions:
                        description += f'\n\n{chr(10).join(choice_descriptions)}'

                return {
                    'name': filter_name,
                    'in': 'query',
                    'schema': {
                        'type': 'string',
                        'enum': enum_values,
                    },
                    'description': description,
                    'required': getattr(filter_field.field, 'required', False)
                }
            
            #For non-choice filters, return None to use default behavior
            return None


    class SearchFilterExtension(OpenApiFilterExtension):
        '''Extension for handling SearchFilter with better descriptions'''
        target_class = 'rest_framework.filters.SearchFilter'
        priority = 2
        
        def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
            '''Override to provide better search parameter description'''
            if not hasattr(auto_schema.view, 'search_fields'):
                return []
            
            search_fields = getattr(auto_schema.view, 'search_fields', [])
            if not search_fields:
                return []
            
            #Clean up field names (remove lookup prefixes)
            clean_fields = [field.split('__')[0] for field in search_fields]
            search_fields_str = ', '.join(set(clean_fields)) 
            
            filter_backend = filters.SearchFilter()
            
            return [{
                'name': filter_backend.search_param,
                'in': 'query',
                'schema': {'type': 'string'},
                'description': f'Search by fields: {search_fields_str}',
                'required': False
            }]


    class OrderingFilterExtension(OpenApiFilterExtension):
        '''Extension for handling OrderingFilter with better descriptions'''
        target_class = 'rest_framework.filters.OrderingFilter'
        priority = 1
        
        def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
            '''Override to provide better ordering parameter description'''
            if not hasattr(auto_schema.view, 'ordering_fields'):
                return []
            
            ordering_fields = getattr(auto_schema.view, 'ordering_fields', [])
            if not ordering_fields:
                return []
            
            ordering_fields_str = ', '.join(ordering_fields)
            filter_backend = filters.OrderingFilter()
            
            return [{
                'name': filter_backend.ordering_param,
                'in': 'query',
                'schema': {'type': 'string'},
                'description': f'Order by fields: {ordering_fields_str}.<br>Use \'-\' for descending order (e.g., -createdAt)',
                'required': False
            }]


    #Define postprocessing hook 
    def response_structure_postprocessing_hook(result, generator, request, public):
        for path, methods in result['paths'].items():
            for method, operation in methods.items():
                if 'responses' in operation:
                    has_pagination = operation.get('parameters',None) and str(operation['operationId']).endswith('_list')
                    has_page_pagination = has_pagination and any(param.get('name') == 'page' for param in operation.get('parameters',[]))  
                    
                    excluded_patterns = [
                        '/invoice/view',
                    ]

                    #Define exclusion criteria
                    exclusion_condition = (
                        (method.upper() != 'GET')
                        or
                        any([re.search(pattern, path) for pattern in excluded_patterns])
                        or
                        (has_pagination and any(param.get('name') == 'cursor' for param in operation.get('parameters',[])))
                        )
                    
                    #determine output type
                    if exclusion_condition:
                        continue

                    if has_page_pagination:
                        _wrap_paginated_responses_with_metadata(path, result, operation)
                    else:
                        _wrap_responses_with_metadata(result, operation)
        
        return result


    def _wrap_responses_with_metadata(result, operation):
        '''Hook to include userPermissions metadata in all relevant responses'''
    
        for status_code, response in operation['responses'].items():
            if 200 <= int(status_code) < 300 and 'content' in response:
                for media_type, content in response['content'].items():
                    if 'schema' in content:
                        original_schema = content['schema']
                        schema_name = original_schema['$ref'].split('/')[-1]
                        resolved_schema = result['components']['schemas'][schema_name]
                        resolved_schema = resolved_schema['properties']
                        resolved_schema['metadata'] = {
                            'type': 'object',
                            'readOnly': True,
                            'properties': {
                            'userPermissions': {
                                'type': 'object',
                                'description': 'Dictionary with string keys and boolean values',
                                'properties': {
                                        'View Users Data Table': {'type': 'boolean'},
                                        'View Clients Data Table': {'type': 'boolean'},
                                        'View Units Data Table': {'type': 'boolean'},
                                        'View Payment Plans Data Table': {'type': 'boolean'},
                                        'View Approvals': {'type': 'boolean'}
                                    },
                                },
                            }
                        }
                        content['schema'] = {
                            'type': 'object',
                            'properties': resolved_schema
                            }
        return result


    def _wrap_paginated_responses_with_metadata(path, result, operation):
        '''Hook to include userPermissions metadata in all paginated list responses'''

        perm_category = _get_category_from_path(path)
        user_permissions = list(User.USER_PERMISSIONS_DICT['sidebar']) + list(User.USER_PERMISSIONS_DICT[perm_category])
        user_permissions = list(dict.fromkeys(user_permissions))
        properties = {item: {'type': 'boolean'} for item in user_permissions}

        for status_code, response in operation['responses'].items():
            if 200 <= int(status_code) < 300 and 'content' in response:
                for media_type, content in response['content'].items():
                    if 'schema' in content:
                        original_schema = content['schema']

                        #Create paginated response structure
                        content['schema'] = {
                            'type': 'object',
                            'properties': {
                                'links': {
                                    'type': 'object',
                                    'properties': {
                                        'next': {'type': 'string', 'nullable': True, 'format': 'uri'},
                                        'previous': {'type': 'string', 'nullable': True, 'format': 'uri'}
                                    }
                                },
                                'pagination': {
                                    'type': 'object',
                                    'properties': {
                                        'count': {'type': 'integer', 'description': 'Total number of items'},
                                        'total_pages': {'type': 'integer', 'description': 'Total number of pages'},
                                        'current_page': {'type': 'integer', 'description': 'Current page number'},
                                        'page_size': {'type': 'integer', 'description': 'Items per page'},
                                        'has_next': {'type': 'boolean', 'description': 'Has next page'},
                                        'has_previous': {'type': 'boolean', 'description': 'Has previous page'}
                                    }
                                },
                                'metadata': {
                                    'type': 'object',
                                    'properties': {
                                        'userPermissions': {
                                        'type': 'object',
                                        'description': 'Dictionary with string keys and boolean values',
                                        'properties': properties
                                        }
                                    }
                                },
                                'results': {
                                    'type': 'array',
                                    'items': _extract_item_schema_from_reference(original_schema, result)
                                }
                            }
                        }

        return result


    def _extract_item_schema_from_reference(original_schema, result):
        """Extract the item schema from response reference"""
        
        if isinstance(original_schema, dict) and '$ref' in original_schema:
            ref_path = original_schema['$ref']
            
            #Extract schema name from #/components/schemas/PaginatedBaseUserList
            if ref_path.startswith('#/components/schemas/'):
                schema_name = ref_path.split('/')[-1]
                
                #Look up in components
                if ('components' in result and 
                    'schemas' in result['components'] and 
                    schema_name in result['components']['schemas']):
                    
                    resolved_schema = result['components']['schemas'][schema_name]
                    
                    #Extract the items schema from the paginated schema
                    if (isinstance(resolved_schema, dict) and 
                        'properties' in resolved_schema and
                        'results' in resolved_schema['properties'] and
                        'items' in resolved_schema['properties']['results']):
                        return resolved_schema['properties']['results']['items']
                    
        return original_schema


    def _get_category_from_path(path):
        category_patterns = {
            r'/units/approvals/': 'approvals',
            r'/payment-plans/': 'payment-plans',
            r'/units/': 'units', 
            r'/clients/': 'clients', 
            r'/users/': 'users',
        }
        
        for pattern, category in category_patterns.items():
            if re.search(pattern, path):
                return category
        return None

