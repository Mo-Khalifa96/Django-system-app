from core.models import AuditLog
from django.utils import timezone
from collections import OrderedDict
from rest_framework import serializers
from core.utils import extend_schema_field
from django.contrib.humanize.templatetags.humanize import naturaltime
from core.mixins import UserPermissionsMixin

#Accepted date formats
DATE_INPUT_FORMATS = ['iso-8601', '%Y/%m/%d', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%b %d, %Y', '%b %-d, %Y', 
                      '%m/%d/%Y', '%d.%m.%Y', '%d/%m/%y %H:%M:%S', '%d/%m/%Y %H:%M:%S']


#SERIALIZERS FOR DASHBOARD 
class UnitTypePercentagesSerializer(serializers.Serializer):
    residential_perc = serializers.CharField()
    commercial_perc = serializers.CharField()

class UnitStatusPercentagesSerializer(serializers.Serializer):
    available_perc = serializers.CharField(required=False)
    sold_perc = serializers.CharField(required=False)
    hold_perc = serializers.CharField(required=False)
    reserved_perc = serializers.CharField(required=False)
    pending_perc = serializers.CharField(required=False)

class MonthCountSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()

class DashboardSerializer(UserPermissionsMixin, serializers.Serializer):
    totalUnits = serializers.IntegerField()
    totalClients = serializers.IntegerField()
    totalUsers = serializers.IntegerField()
    unitTypePercentages = UnitTypePercentagesSerializer()
    unitStatusPercentages = UnitStatusPercentagesSerializer()
    units_byMonth = MonthCountSerializer(many=True)
    clients_byMonth = MonthCountSerializer(many=True)


#AUDIT LOGS SERIALIZER
class AuditLogSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    entity = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['time', 'user', 'action', 'entity', 'changes']    
    
    @extend_schema_field({'type': 'object', 'properties': {
            'entityName': {'type':'string', 'description':'Name of the entity that was changed', 'example':'Unit'},
            'entityDetails': {'type': 'string', 'description':'Details/identifier of the specific entity instance', 'example':'B01-4-U02 (John Smith)'}
            }, 'required': ['entityName', 'entityDetails'], 'description': 'Information about the entity that was changed'})
    def get_entity(self, obj):
        return obj.entity
    
    @extend_schema_field({
        'type': 'object',
        'description': 'Dictionary with fields that changed',
        'additionalProperties': {
            'anyOf': [
                {
                    'type': 'object',
                    'properties': {
                        'from': {
                            'type': 'string',
                            'example': 'AVAILABLE'
                        },
                        'to': {
                            'type': 'string',
                            'example': 'RESERVED'
                        }
                    },
                    'required': ['from', 'to']
                },
                {
                    'type': 'object',
                    'properties': {
                        'additionalProp1': {
                            'type': 'string'
                        },
                        'additionalProp2': {
                            'type': 'string',
                        },
                        'additionalProp3': {
                            'type': 'string',
                            'format': 'decimal',
                        }
                    },
                    'additionalProperties': True
                },
                {
                    'type': 'string',
                    'description': 'A simple text description of the change.',
                    'example': 'Uploaded new contract'
                }
            ]
        },
        'example': {
            'status': {
                'from': 'AVAILABLE',
                'to': 'RESERVED'
            },
            'client': {
                'from': None,
                'to': 'John Smith'
            },
            'totalPrice': {
                'from': '7000000.00',
                'to': '7200000.00'
            },
            'paymentSchedule': {
                'summary': 'Created 4 new installments',
                'total_amount': '7200000.00',
            },
            'contract': 'Uploaded new contract',
        }
    })
    def get_changes(self, obj):
        return obj.changes
    
    @extend_schema_field(serializers.CharField)
    def get_time(self, obj):
        if int((timezone.now() - obj.createdAt).total_seconds()) > 90000: #25 hours
            return obj.createdAt.strftime('%d/%m/%y %I:%M %p')
        return naturaltime(obj.createdAt)


    def to_representation(self, instance):
        rep = super().to_representation(instance)
        changes = rep.get('changes')
        if not changes:
            return rep
        ordered_changes = {}
        for field, change in changes.items():
            if isinstance(change, dict):
                ordered_changes[field] = OrderedDict([
                    ('from', change.get('from')),('to', change.get('to'))
                ])
            else:
                ordered_changes[field] = change
        rep['changes'] = ordered_changes
        return rep
