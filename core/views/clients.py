from core.models import Client
from rest_framework import generics
from users.permissions import SystemUserPermissions
from core.serializers.clients import ClientSerializer, CreateClientSerializer, ListClientSerializer, RetrieveClientSerializer, UpdateClientSerializer
from core.mixins import AuditCreateMixin, AuditDeleteMixin, AuditUpdateMixin
from rest_framework.filters import SearchFilter, OrderingFilter
from core.utils import extend_schema


#CLIENT VIEWS 
#List all clients API view
@extend_schema(tags=['Clients'])
class ListClientsAPIView(generics.ListAPIView):
    queryset = Client.objects.prefetch_related('client_units').all()
    serializer_class = ListClientSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Clients Data Table'
    ordering = ['-createdAt']  #default order of fields
    search_fields = ['name']   #search fields
    ordering_fields = ['name', 'createdAt']  #sorting fields 
    filter_backends = [SearchFilter, OrderingFilter]


#Create new clients API view
@extend_schema(tags=['Clients'])
class CreateClientAPIView(AuditCreateMixin, generics.CreateAPIView):
    queryset = Client.objects.all()
    serializer_class = CreateClientSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Create New Clients'


#Retrieve client API view 
@extend_schema(tags=['Clients'])
class RetrieveClientAPIView(generics.RetrieveAPIView): 
    queryset = Client.objects.all()
    serializer_class = RetrieveClientSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Client Details'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'


#Update client API view 
@extend_schema(tags=['Clients'])
class UpdateClientAPIView(AuditUpdateMixin, generics.RetrieveUpdateAPIView):
    queryset = Client.objects.all()
    permission_classes = [SystemUserPermissions]
    required_permission = 'Update Client'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ClientSerializer
        else:
            return UpdateClientSerializer


#Delete client API view 
@extend_schema(tags=['Clients'])
class DeleteClientAPIView(AuditDeleteMixin, generics.DestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Delete Client'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
