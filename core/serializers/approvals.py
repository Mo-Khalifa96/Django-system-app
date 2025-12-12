from core.models import Unit 
from rest_framework import serializers
from core.utils import extend_schema_field
from core.mixins import UserPermissionsMixin


#SERIALIZERS FOR APPROVALS APIs 
#Serializer for units awaiting approval 
class ListUnitsForApprovalSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    currentStatus = serializers.CharField(source='status', max_length=50, read_only=True)
    updatedAt = serializers.DateTimeField(format='%d/%m/%Y %I:%M %p', read_only=True)

    class Meta: 
        model = Unit 
        fields = ['id', 'code', 'client', 'currentStatus', 'requestedStatus', 'totalPrice', 'updatedBy', 'updatedAt']

    @extend_schema_field(serializers.CharField)
    def get_code(self, obj):
        return obj.get_code()
    
    @extend_schema_field({'type': 'object', 'properties': 
    {'id': {'type':'string','format':'uuid'},'name':{'type':'string'}}})
    def get_client(self, obj):
        if obj.client:
            return {'id': obj.client.id, 'name': obj.client.name}
        return None 


#Serializer for approving unit changes 
class ApproveUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit 
        fields = ['isApproved']


#Serializer for previewing or approving unit changes 
class PreviewApproveUnitSerializer(UserPermissionsMixin, serializers.ModelSerializer):   #NOTE -> i don't have access yet 
    code = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    currentStatus = serializers.CharField(source='status', max_length=50, read_only=True)
    updatedAt = serializers.DateTimeField(format='%d/%m/%Y %I:%M %p', read_only=True)
    
    class Meta: 
        model = Unit 
        fields = ['id', 'code', 'client', 'currentStatus', 'requestedStatus', 'activity', 
                  'totalPrice', 'isApproved', 'updatedBy', 'updatedAt', 'contract']
        read_only_fields = ['id', 'code', 'client', 'currentStatus', 'requestedStatus', 
                            'activity', 'totalPrice', 'updatedBy', 'updatedAt', 'contract']

    @extend_schema_field(serializers.CharField)
    def get_code(self, obj):
        return obj.get_code()
    
    @extend_schema_field({'type': 'object', 'properties': 
    {'id':{'type':'string','format':'uuid'},'name':{'type':'string'}}})
    def get_client(self, obj):
        if obj.client:
            return {'id': obj.client.id, 'name': obj.client.name}
        return None 


