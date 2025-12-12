import json
from django.db.models import Sum
from rest_framework import serializers
from .general import DATE_INPUT_FORMATS
from .clients import NewClientSerializer
from core.mixins import UserPermissionsMixin
from django.utils.translation import gettext_lazy as _
from core.utils import calculate_percentage, extend_schema_field
from core.models import Client, Unit, Installment, InstallmentConfiguration


#SERIALIZERS FOR UNITS APIs 
#Serializer for listing units 
class ListUnitSerializer(serializers.ModelSerializer):
    client = serializers.SerializerMethodField()
    holdDetails = serializers.SerializerMethodField()

    class Meta:
        model = Unit 
        fields = ['id', 'building', 'floor', 'unitCode', 'activity', 'indoorSize', 
                  'outdoorSize', 'totalPrice', 'client', 'status', 'holdDetails']
    
    @extend_schema_field({'type': 'object', 'properties': 
    {'id': {'type': 'string', 'format': 'uuid'},'name': {'type': 'string'}}})
    def get_client(self, obj):
        if obj.client:
            return {'id': obj.client.id, 'name': obj.client.name}
        return None

    @extend_schema_field({'type': 'object', 'properties': 
    {'holdDeposite':{'type': 'number'},'holdExpiryDate':{'type': 'string'}}})
    def get_holdDetails(self, obj):
        if obj.holdDeposit or obj.holdExpiryDate:
            return {'holdDeposite': obj.holdDeposit, 
                    'holdExpiryDate': obj.holdExpiryDate.strftime('%d-%m-%Y') if obj.holdExpiryDate else None
                    }
        return None 


#Serializer for unit installments configurations
class CreateInstallmentConfigSerializer(serializers.ModelSerializer):    
    startDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False)
    
    class Meta:
        model = InstallmentConfiguration
        fields = ['id', 'every', 'startingMonth', 'repetitions', 'amount', 'startDate', 'description']

    def validate(self, data):
        if self.context.get('enablePaymentPlan'):
            required_fields = ['every', 'startingMonth', 'repetitions', 'amount', 'startDate']
            missing_fields = [field for field in required_fields if data.get(field) in [None, '']]
            if missing_fields:
                raise serializers.ValidationError(
                    {field: _('This field is required to make a payment plan.') for field in missing_fields}
                )
            if data.get('startingMonth') < 1:
                raise serializers.ValidationError({'startingMonth': _('Starting month must be 1 or higher.')})
        return data

#Serializer for unit payments schedule (for preview table)
class CreateUnitPaymentScheduleSerializer(serializers.ModelSerializer):
    month = serializers.IntegerField(required=False, allow_null=True)
    dueDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False)

    class Meta: 
        model = Installment
        fields = ['id', 'month', 'dueDate', 'description', 'amount']
        extra_kwargs = {'id': {'read_only': True}, 'status': {'required': True}, 'amount': {'required': False}, 'description': {'required': False}}

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        month = str(instance.description.split()[-1]) 
        rep['month'] = int(month) if month.isdigit() else None 
        return {field: rep[field] for field in self.fields if field in rep}

#Serializer for creating new units 
class CreateUnitSerializer(serializers.ModelSerializer):
    STATUS_CHOICES = [('AVAILABLE', 'Available'), ('SOLD', 'Sold'), ('HOLD', 'On Hold'), ('RESERVED', 'Reserved')]

    #serializer fields 
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    newClient = NewClientSerializer(many=False, required=False)
    client_choices = serializers.ChoiceField(choices=[], required=False, allow_blank=True, allow_null=True) 
    installmentConfig = CreateInstallmentConfigSerializer(many=True, source='unit_configs', required=False) 
    paymentSchedule = CreateUnitPaymentScheduleSerializer(many=True, source='unit_installments', required=False)
    holdExpiryDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False, allow_null=True)
    contract = serializers.FileField(use_url=True, required=False, allow_null=True)

    class Meta:
        model = Unit  
        fields = ['id', 'building', 'floor', 'unitCode', 'indoorSize', 'outdoorSize', 'areaPrice', 'totalPrice', 
                  'enablePaymentPlan', 'installmentConfig', 'paymentSchedule', 'status', 'activity',
                  'holdDeposit', 'holdExpiryDate', 'newClient', 'client_choices', 'contract', 'notes'] 
        extra_kwargs = {'status': {'required': True}, 'activity': {'required': True}}

    def get_fields(self):
        fields = super().get_fields()
        #populate client names 
        client_names = Client.objects.values_list('name', flat=True)
        fields['client_choices'].choices = [(name, name) for name in client_names]
        fields['client_choices'].initial = None 
        return fields 

    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''
        data_preprocessed = {}

        for field in data: 
            if field not in ['installmentConfig', 'paymentSchedule', 'newClient']:
                if field in ['holdExpiryDate', 'contract'] and data[field] == '':
                    data_preprocessed[field] = None 
                else:
                    data_preprocessed[field] = data[field]
            else:
                if isinstance(data.get(field), str):
                    try:
                        data_preprocessed[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({field: 'Invalid JSON format'})
                else:
                    data_preprocessed[field] = data[field]

        #update child serializer context 
        self.context.update({'enablePaymentPlan': data_preprocessed.get('enablePaymentPlan', False)})
        return super().to_internal_value(data_preprocessed)

    #client validation 
    def validate_newClient(self, newClient):
        if any(newClient.values()):
            if not all(newClient.values()):
                raise serializers.ValidationError({'newClient': _('If creating a new client, all new client fields must be filled.')})
        return newClient
    
    #Serializer-level validation
    def validate(self, data):
        #validate status-related data 
        status = data.get('status')
        paymentSchedule = data.get('unit_installments')

        if status == 'HOLD':
            if not data.get('holdDeposit'):
                raise serializers.ValidationError({'holdDeposit': _("This field is required when unit status is set to 'On Hold'")})
            if not data.get('holdExpiryDate'):
                raise serializers.ValidationError({'holdExpiryDate': _("This field is required when unit status is set to 'On Hold'")})
        else:
            if data.get('holdDeposit'):
                raise serializers.ValidationError({'holdDeposit': _("Hold deposit cannot be set if unit status is not 'On Hold'")})
            if data.get('holdExpiryDate'):
                raise serializers.ValidationError({'holdExpiryDate': _("Hold expiry date cannot be set if unit status is not 'On Hold'")})

        #validate payment plan amount
        if data.get('enablePaymentPlan') and paymentSchedule:
            totalPrice = data.get('totalPrice')
            totalPayment = sum(installment.get('amount') for installment in paymentSchedule)
            if totalPrice and totalPayment:
                if totalPayment < totalPrice:
                    raise serializers.ValidationError({'totalPayment': _(f'Payment plan is inconsistent with unit price. Payment total ({totalPayment}) < unit price ({totalPrice})')})
                elif totalPayment > totalPrice:
                    raise serializers.ValidationError({'totalPayment': _(f'Payment plan is inconsistent with unit price. Payment total ({totalPayment}) > unit price ({totalPrice})')})

        #client validation 
        if status != 'AVAILABLE' and not data.get('newClient') and not data.get('client_choices'):
            raise serializers.ValidationError({'newClient': _(f"Client cannot be missing if unit status is changed from 'Available' to '{status.capitalize()}'")})
        elif status == 'AVAILABLE' and (data.get('newClient') or data.get('client_choices')):
            raise serializers.ValidationError({'status': _('Unit status cannot be available while associated with a client.')})
        
        #contract validation
        if status != 'AVAILABLE' and not data.get('contract'):
            raise serializers.ValidationError({'contract': _(f"Contract must be uploaded if unit status is changed from 'Available' to '{status.capitalize()}'")})
        return data 


#For GET request to get details 
class GetUnitChoicesSerializer(UserPermissionsMixin, serializers.Serializer):
    STATUS_CHOICES = [('AVAILABLE', 'Available'), ('SOLD', 'Sold'), ('HOLD', 'On Hold'), ('RESERVED', 'Reserved')]

    newClient = NewClientSerializer(many=False, read_only=True)
    client_choices = serializers.ChoiceField(choices=[], read_only=True)
    floor_choices = serializers.ChoiceField(choices=Unit.FloorChoices.choices, read_only=True)
    status_choices = serializers.ChoiceField(choices=STATUS_CHOICES, read_only=True)
    activity_choices = serializers.ChoiceField(choices=Unit.UnitActivities.choices, read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        client_names = Client.objects.values_list('name', flat=True)
        fields['client_choices'].choices = [(name, name) for name in client_names]
        return fields 


#Unit serializer for detail view (retrieve)
class RetrieveUnitSerializer(serializers.ModelSerializer):
    activity_perc = serializers.SerializerMethodField()
    propertyInformation = serializers.SerializerMethodField()
    clientDetails = serializers.SerializerMethodField()

    class Meta:
        model = Unit 
        fields = ['id', 'unitCode', 'building', 'floor', 'status', 'activity', 
                  'activity_perc', 'contract', 'propertyInformation', 'clientDetails']
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user = self.context.get('request').user if self.context.get('request') else None
        if (instance.status == 'AVAILABLE') or (user and getattr(user, 'role', None) != 'ADMIN'):
            rep.pop('contract', None)  #Remove contract if the property is available

        #add user permissions 
        rep['metadata'] = {
                'userPermissions': user.get_user_permissions()
            }
        return rep
    
    @extend_schema_field(serializers.FloatField)
    def get_activity_perc(self, obj):
        return calculate_percentage(vals=Unit.objects.filter(activity=obj.activity).count(), total=Unit.objects.count())
    
    @extend_schema_field({'type': 'object', 'properties': {'totalPrice': {'type': 'number'},
    'indoorSize': {'type': 'number'},'outdoorSize': {'type': 'number'}}})
    def get_propertyInformation(self, obj):
        return {'totalPrice': obj.totalPrice, 'indoorSize': obj.indoorSize, 'outdoorSize': obj.outdoorSize}
    
    @extend_schema_field({'type': 'object', 'properties': {'id': {'type': 'string', 'format': 'uuid'},
    'name': {'type': 'string'},'email': {'type': 'string'},'phone': {'type': 'string'}}})
    def get_clientDetails(self, obj):
        if obj.client:
            return {'id': obj.client.id, 'name': obj.client.name, 
                    'email': obj.client.email, 'phone': obj.client.phone}
        return None


#Nested serializers for updating unit installment configs and installments
class UpdateInstallmentConfigSerializer(serializers.ModelSerializer):
    startDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False)
    isEditable = serializers.BooleanField(required=False, read_only=True)

    PAYMENT_TYPES = {1: 'Monthly Payment', 2: 'Bi-Monthly Payment', 3: 'Quarterly Payment', 
                     6: 'Semi-Annual Payment', 12: 'Annual Payment'}
    
    class Meta:
        model = InstallmentConfiguration
        fields = ['id', 'every', 'startingMonth', 'repetitions', 'amount', 'startDate', 'description', 'isEditable']

    def determine_description(self, every, description):
        return description or self.PAYMENT_TYPES.get(every, f'Every {every} Months Payment')
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        paid_installments_lookup = self.context.get('paid_installments_lookup', {})
        rep['isEditable'] = (
                        self.determine_description(instance.every, instance.description), 
                        instance.startDate
                    ) not in paid_installments_lookup
        return rep 
        
    #validation
    def validate(self, data):
        paid_installments_lookup = self.context.get('paid_installments_lookup', {})
        isEditable = (self.determine_description(data.get('every'), data.get('description')), 
                      data.get('startDate')
                     ) not in paid_installments_lookup
        
        if isEditable:
            required_fields = ['every', 'startingMonth', 'repetitions', 'amount', 'startDate']
            missing_fields = [field for field in required_fields if data.get(field) in [None, '']]
            if missing_fields:
                raise serializers.ValidationError(
                    {field: _('This field is required to make a payment plan.') for field in missing_fields}
                )
            if data.get('startingMonth') < 1:
                raise serializers.ValidationError({'startingMonth': _('Starting month must be 1 or higher.')})
        return data

class UpdateUnitPaymentScheduleSerializer(serializers.ModelSerializer):
    month = serializers.IntegerField(required=False, allow_null=True)
    dueDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False)

    class Meta: 
        model = Installment
        fields = ['id', 'month', 'dueDate', 'description', 'amount', 'paid']
        extra_kwargs = {'status': {'required': True}, 'amount': {'required': False}, 'description': {'required': False}, 
                        'paid': {'read_only': True}}

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        month = str(instance.description.split()[-1]) 
        rep['month'] = int(month) if month.isdigit() else None 
        return {field: rep[field] for field in self.fields if field in rep}


#Update unit serializer 
class UpdateUnitSerializer(serializers.ModelSerializer): 
    STATUS_CHOICES = [('AVAILABLE', 'Available'), ('SOLD', 'Sold'), ('HOLD', 'On Hold'), ('RESERVED', 'Reserved')]   

    #serializer fields 
    newClient = NewClientSerializer(many=False, required=False)  
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False, allow_blank=True, allow_null=True)
    client_choices = serializers.ChoiceField(choices=[], required=False, allow_blank=True, allow_null=True) 
    installmentConfig = UpdateInstallmentConfigSerializer(many=True, source='unit_configs', required=False)
    paymentSchedule = UpdateUnitPaymentScheduleSerializer(many=True, source='unit_installments', required=False)
    totalPayment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    holdExpiryDate = serializers.DateField(format='%d/%m/%Y', input_formats=DATE_INPUT_FORMATS, required=False, allow_null=True)
    contract = serializers.FileField(use_url=True, required=False, allow_null=True)
    clientInformation = serializers.SerializerMethodField()  #read-only

    class Meta: 
        model = Unit 
        fields = ['id', 'building', 'floor', 'unitCode', 'indoorSize', 'outdoorSize', 'areaPrice', 'totalPrice',
                  'enablePaymentPlan', 'installmentConfig', 'paymentSchedule', 'totalPayment', 'status', 
                  'activity', 'holdDeposit', 'holdExpiryDate', 'newClient', 'client_choices', 'clientInformation', 
                  'contract', 'notes']
        extra_kwargs = {'id': {'read_only': True}, 'status': {'required': False}, 'activity': {'required': False}, 'totalPrice': {'required': False},
                        'building': {'required': False}, 'floor': {'required': False}, 'unitCode': {'required': False}}
    
    @extend_schema_field({'type': 'object', 'properties': 
    {'name': {'type': 'string'},'email': {'type': 'string'},'phone': {'type': 'string'}}})
    def get_clientInformation(self, obj):
        if obj.client:  #read only
            return {'name': obj.client.name, 'email': obj.client.email, 'phone': obj.client.phone}
        return None

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        unit = self.context.get('unit')

        #remove choice fields that won't be used 
        if request and request.method in ['PUT', 'PATCH']:
            fields.pop('clientInformation', None)

        #populate client names 
        client_names = Client.objects.values_list('name', flat=True)
        fields['client_choices'].choices = [(name, name) for name in client_names]

        if not unit:  #for swagger
            return fields 
        
        if unit.status == 'AVAILABLE':
            fields.pop('clientInformation', None)
        else:
            fields['client_choices'].initial = unit.client.name if unit.client else None 
   
        if request.user and getattr(request.user, 'role', None) == 'SALES' and unit.status != 'AVAILABLE':
            fields.pop('paymentSchedule', None)
            fields.pop('totalPayment', None)
        else:
            fields['totalPayment'].initial = unit.unit_installments.aggregate(total=Sum('amount'))['total'] or 0
        
        return fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method in ['POST', 'PATCH']:
            self.fields['newClient'].write_only = True 
            self.fields['client_choices'].write_only = True 
            self.fields['totalPayment'].write_only = True 

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.method == 'GET':
            rep['totalPayment'] = self.fields['totalPayment'].initial
            rep['newClient'] = {'name': None, 'email': None, 'phone': None}
            rep['client_choices'] = self.fields['client_choices'].choices
            rep['floor_choices'] = self.fields['floor'].choices
            rep['status_choices'] = dict(self.STATUS_CHOICES)
            rep['activity_choices'] = self.fields['status'].choices
            rep['metadata'] = {
                'userPermissions': request.user.get_user_permissions()
            }

        ordered_fields = ('building', 'floor', 'floor_choices', 'unitCode', 'indoorSize', 'outdoorSize', 'areaPrice', 'totalPrice',
                          'enablePaymentPlan', 'installmentConfig', 'paymentSchedule', 'totalPayment', 'status', 'status_choices', 
                          'activity', 'activity_choices', 'holdDeposit', 'holdExpiryDate', 'newClient', 'client_choices', 
                          'clientInformation', 'contract', 'notes', 'metadata')
        
        return {field: rep[field] for field in ordered_fields if field in rep}


    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''
        data_preprocessed = {}

        for field in data: 
            if field not in ['installmentConfig', 'paymentSchedule', 'newClient']:
                if field in ['holdExpiryDate', 'contract'] and data[field] == '':
                    data_preprocessed[field] = None 
                else:
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

    #Validations 
    def validate_newClient(self, newClient):
        if any(newClient.values()):
            if not all(newClient.values()):
                raise serializers.ValidationError(_('If creating a new client, all new client fields must be filled.'))
        return newClient

    def validate_paymentSchedule(self, paymentSchedule):      
        paid_installments = {installment.id: installment for installment in self.instance.unit_installments.filter(paid=True).only('id', 'amount', 'dueDate')}
        for installment in paymentSchedule:
            installment_id = installment.get('id')
            if installment_id in paid_installments:
              installment_before = paid_installments[installment_id]
              if (installment['amount'] != installment_before.amount) or (installment['dueDate'] != installment_before.dueDate):
                  raise serializers.ValidationError(_("Cannot edit an installment that's already paid"))
        return paymentSchedule 

    #Serializer-level validation
    def validate(self, data):
        old_unit = self.instance 
        contract = data.get('contract')
        totalPayment = data.get('totalPayment')
        current_status = data.get('status') or old_unit.status
        totalPrice = data.get('totalPrice') or old_unit.totalPrice 
        paymentSchedule = data.get('unit_installments')
        

        #validate contract
        #if no contract upload but status isn't available, return existing contract
        if not contract and current_status != 'AVAILABLE':
                data['contract'] = old_unit.contract

        #validate unit price payment details (NOTE -> total calculation must be arranged with frontend)
        if data.get('enablePaymentPlan') and paymentSchedule:
            totalPayment = totalPayment if totalPayment else (sum(installment['amount'] for installment in paymentSchedule))
            if totalPayment < totalPrice:
                raise serializers.ValidationError({'totalPayment': _(f'Payment plan is inconsistent with unit price. Payment total ({totalPayment}) < unit price ({totalPrice})')})
            elif totalPayment > totalPrice:
                raise serializers.ValidationError({'totalPayment': _(f'Payment plan is inconsistent with unit price. Payment total ({totalPayment}) > unit price ({totalPrice})')})

        #validate status-related data 
        if current_status == 'HOLD':
            holdDeposit = data.get('holdDeposit') or old_unit.holdDeposit
            holdExpiryDate = data.get('holdExpiryDate') or old_unit.holdExpiryDate
            if not holdDeposit:
                raise serializers.ValidationError({'holdDeposit': _("This field is required when unit status is set to 'On Hold'")})
            if not holdExpiryDate:
                raise serializers.ValidationError({'holdExpiryDate': _("This field is required when unit status is set to 'On Hold'")})
        else:
            if data.get('holdDeposit'):
                raise serializers.ValidationError({'holdDeposit': _("Hold deposit cannot be set if unit status is not 'On Hold'")})
            if data.get('holdExpiryDate'):
                raise serializers.ValidationError({'holdExpiryDate': _("Hold expiry date cannot be set if unit status is not 'On Hold'")})

        #Validate client
        if current_status != 'AVAILABLE' and (not old_unit.client and (not data.get('newClient') or not data.get('client_choices'))):
            raise serializers.ValidationError({'newClient': _(f"Client cannot be missing if unit status is changed from 'Available' to '{current_status.capitalize()}'")})
        
        #Validate contract
        if old_unit.status == 'AVAILABLE' and current_status != 'AVAILABLE' and not contract:
            raise serializers.ValidationError({'contract': _(f"Contract must be uploaded if unit status is changed from 'Available' to '{current_status.capitalize()}'")})
        
        return data 

