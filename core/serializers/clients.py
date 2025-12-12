from django.db.models import Sum
from rest_framework import serializers
from core.utils import calculate_percentage
from core.serializers.payments import InstallmentSerializer
from core.models import Client, Unit, Installment 
from django.db.models import Case, When, IntegerField, Min
from core.utils import extend_schema_field, extend_schema_serializer, OpenApiExample
from core.mixins import UserPermissionsMixin


#SERIALIZERS FOR CLIENTS APIs
#General purpose client serializer 
class NewClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone']
        extra_kwargs = {'name': {'required': False}, 'email': {'required': False}, 'phone': {'required': False}}


#General-purpose client serializer
class ClientSerializer(UserPermissionsMixin, serializers.ModelSerializer):
    createdAt = serializers.DateField(format='%d/%m/%Y', read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'createdAt']

#Client serializer for creating new clients
class CreateClientSerializer(UserPermissionsMixin, serializers.ModelSerializer):
    createdAt = serializers.DateField(format='%d/%m/%Y', read_only=True)

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'companyName', 'jobTitle', 'address', 
                  'city', 'state', 'zipcode', 'notes', 'createdAt']
        
        extra_kwargs = {
                'companyName': {'required': False}, 'jobTitle': {'required': False}, 'address': {'required': False}, 
                'city': {'required': False}, 'state': {'required': False}, 'zipcode': {'required': False}, 
                'notes': {'required': False}
                        }
        

#Client serializer for client listing clients
class ListClientSerializer(serializers.ModelSerializer):
    unitCount = serializers.SerializerMethodField() 
    paymentStatus = serializers.SerializerMethodField()
    createdAt = serializers.DateField(format='%d/%m/%Y', read_only=True)
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'unitCount', 'paymentStatus', 'createdAt']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method == 'POST':
            fields.pop('unitCount', None)
            fields.pop('paymentStatus', None)
        return fields 

    @extend_schema_field(serializers.IntegerField)
    def get_unitCount(self, obj):
        return obj.client_units.count()
    
    @extend_schema_field(serializers.CharField)   
    def get_paymentStatus(self, obj):
        priority = obj.client_units.aggregate(
                priority_byMin=Min(
                    Case(
                        When(unit_installments__status='OVERDUE', then=1),
                        When(unit_installments__status='PENDING', then=2), 
                        When(unit_installments__status='PAID', then=3),
                        output_field=IntegerField()
                    )
                ))['priority_byMin']
        
        if priority == 3:
            return 'PAID'
        elif priority == 2:
            return 'PENDING'
        elif priority == 1:
            return 'OVERDUE'
        else:
            return None 
    

#Retrieve client serializer 
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Admin Response",
            response_only=True,
            summary="Response for admin users (includes financial summary)",
            description="Admin users get all client data including financial information",
            value={
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Smith",
                "email": "john@example.com", 
                "phone": "+1234567890",
                "clientUnits": {
                    "totalUnits": 2,
                    "units": [
                        {"id": "456e7890-e89b-12d3-a456-426614174001", "code": "A-2-101"},
                        {"id": "456e7890-e89b-12d3-a456-426614174001", "code": "A-2-102"}
                    ]
                },
                "financialSummary": {
                    "totalPrice": 250000.00,
                    "totalPaid": 125000.00,
                    "paymentProgress": 50.0
                },
                "metadata": {
                    "userPermissions": {
                        "View Users Data Table": True,
                        "View Clients Data Table": True,
                        "View Units Data Table": True,
                        "View Payment Plans Data Table": True,
                        "View Approvals": True,
                        "View Client Details": True,
                        "Create New Clients": True,
                        "Update Client": True,
                        "Delete Client": True
                    }
                }
            }
        ),
        OpenApiExample(
            name="Non-Admin Response",
            response_only=True,
            summary="Response for regular users (no financial summary)",
            description="Regular users get client data without financial information",
            value={
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Smith",
                "email": "john@example.com",
                "phone": "+1234567890", 
                "clientUnits": {
                    "totalUnits": 2,
                    "units": [
                        {"id": "456e7890-e89b-12d3-a456-426614174001", "code": "A-2-101"}
                    ]
                },
                "metadata": {
                    "userPermissions": {
                        "View Users Data Table": False,
                        "View Clients Data Table": True,
                        "View Units Data Table": True,
                        "View Payment Plans Data Table": False,
                        "View Approvals": False,
                        "View Client Details": True,
                        "Create New Clients": True,
                        "Update Client": True,
                        "Delete Client": False
                    }
                }
            }
        )
    ]
)
class RetrieveClientSerializer(UserPermissionsMixin, serializers.ModelSerializer):  
    clientUnits = serializers.SerializerMethodField() 
    financialSummary = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'clientUnits', 'financialSummary']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request.user, 'role', None) != 'ADMIN':
            self.fields.pop('financialSummary')    

    @extend_schema_field({'type': 'object','properties': {'totalUnits':{'type':'integer'},'units':{'type':'array',
    'items': {'type': 'object','properties': {'id': {'type':'string','format':'uuid'},'code':{'type':'string'}}}}}})
    def get_clientUnits(self, obj):
        units = [{'id': unit.id, 'code': unit.get_code()} for unit in obj.client_units.all()] 
        return {'totalUnits': obj.client_units.count(),
                'units': units}    
    

    @extend_schema_field({'type': 'object', 'properties':{'totalPrice':{'type':'number'},
    'totalPaid':{'type':'number'},'paymentProgress':{'type':'number'}}})
    def get_financialSummary(self, obj):
        totalPrice = obj.client_units.aggregate(totalPrice=Sum('totalPrice'))['totalPrice'] or 0
        totalPaid = Installment.objects.filter(unit__client=obj, paid=True)\
                     .aggregate(totalPaid=Sum('amount'))['totalPaid'] or 0
        paymentProgress = calculate_percentage(vals=totalPaid, total=totalPrice)
    
        return {'totalPrice': totalPrice, 
                'totalPaid': totalPaid,   
                'paymentProgress': paymentProgress}   


#Update client serializer 
class UpdateClientSerializer(serializers.ModelSerializer):  #NOTE -> will likely require edits based on the clients/id/edit/ page
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone']


#Nested serializer for client units 
class ClientUnitSerializer(serializers.ModelSerializer): 
    code = serializers.SerializerMethodField()
    contract = serializers.FileField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = Unit
        fields = ['id', 'code', 'activity', 'status', 'totalPrice', 'contract']

    @extend_schema_field(serializers.CharField)
    def get_code(self, obj):
        return obj.get_code()

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method not in ['PUT', 'PATCH'] or (getattr(request.user, 'role', None) != 'ADMIN'):  #instead of request.user.role
                fields.pop('contract')
        return fields 
    

#Client serializer for updating client (prototype - not in use)
class OptionalUpdateClientSerializer(serializers.ModelSerializer):
    clientUnits = ClientUnitSerializer(many=True, read_only=False, source='client_units', required=False) 
    clientPayments = InstallmentSerializer(many=True, required=False)  

    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'clientUnits', 'clientPayments']

