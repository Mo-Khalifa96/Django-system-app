import json
from django.db.models import Sum
from django.db import transaction
from rest_framework import serializers
from .general import DATE_INPUT_FORMATS
from core.utils import extend_schema_field
from core.mixins import UserPermissionsMixin
from core.validators import validate_phone_number
from core.models import Installment, Unit, Invoice
from django.utils.translation import gettext_lazy as _


#General-Purpose Installments Serializer   #NOTE -> May require edits based on the clients/id/edit/ page
class InstallmentSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    dueDate = serializers.DateField(format='%b %d, %Y', required=False, read_only=True) 
    paidAt = serializers.DateTimeField(format='%b %d, %Y', required=False, allow_null=True, read_only=True)

    class Meta:
        model = Installment
        fields = ['id', 'dueDate', 'description', 'amount', 'paid', 'paidAt', 'status']
        read_only_fields = ['id', 'dueDate', 'description', 'amount', 'paid', 'paidAt', 'status']
    
    @extend_schema_field(serializers.CharField)
    def get_description(self, obj):
        description = obj.description
        month = description.rsplit(' - ')[-1] if '- Month' in description else None 
        if not obj.installmentType or not month:
            return description
        return f'{obj.installmentType} - {month}'


#Serializer for listing payment plans  
class ListPaymentPlanSerializer(serializers.ModelSerializer):
    client = serializers.CharField(source='client.name', read_only=True)
    unit = serializers.SerializerMethodField()
    paidAmount = serializers.SerializerMethodField()
    paymentProgress = serializers.SerializerMethodField()
    installments = InstallmentSerializer(many=True, source='unit_installments', read_only=True)
    total_installments = serializers.SerializerMethodField()
    total_paid_installments = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = ['unit', 'status', 'client', 'totalPrice', 'paidAmount', 'paymentProgress',
                  'total_installments', 'total_paid_installments', 'installments']
        extra_kwargs = {'totalPrice': {'read_only': True}}


    @extend_schema_field(serializers.CharField)
    def get_unit(self, obj):
        return obj.get_code()
    
    @extend_schema_field(serializers.FloatField)
    def get_paidAmount(self, obj):
        return obj.unit_installments.filter(paid=True).aggregate(totalPaid=Sum('amount'))['totalPaid'] or 0 
    
    @extend_schema_field(serializers.FloatField)
    def get_paymentProgress(self, obj):
        paid_amount = self.get_paidAmount(obj) 
        total_amount = obj.unit_installments.aggregate(totalAmount=Sum('amount'))['totalAmount'] or 0
        total_price = obj.totalPrice or 0
        total_required = max(total_amount, total_price)
        if total_required == 0:
            return 0
        return round((paid_amount / total_required) * 100, 2)
    
    @extend_schema_field(serializers.IntegerField)
    def get_total_installments(self, obj):
        return obj.unit_installments.count()
    
    @extend_schema_field(serializers.IntegerField)
    def get_total_paid_installments(self, obj):
        return obj.unit_installments.filter(paid=True).count()


#Installment payment update serializer 
class InstallmentPaidUpdateSerializer(serializers.ModelSerializer):
    paidAt = serializers.DateTimeField(format='%d/%m/%Y %H:%M:%S', read_only=True)

    class Meta:
        model = Installment
        fields = ['id', 'paid', 'paidAt']

    def validate_paid(self, value):
        if self.instance and self.instance.paid and value is True:
            raise serializers.ValidationError(_('Installment is already marked as paid'))
        if value is False:
            raise serializers.ValidationError(_('Cannot mark installment as unpaid once it has been paid'))
        return value


#Nested serializer for invoice issuer
class InvoiceIssuedBySerializer(serializers.Serializer):
    company = serializers.CharField()
    phone = serializers.CharField(validators=[validate_phone_number])
    email = serializers.EmailField()
    address = serializers.CharField()

#Nested serializer for invoice receiver
class InvoiceIssuedToSerializer(serializers.Serializer):
    clientName = serializers.CharField()
    clientPhone = serializers.CharField(validators=[validate_phone_number])
    clientEmail = serializers.EmailField()


#Serializer for semi-automatic invoice creation
class InstallmentInvoiceSerializer(serializers.ModelSerializer):
    unit = serializers.SerializerMethodField()
    unitPrice = serializers.SerializerMethodField()
    issuedBy = InvoiceIssuedBySerializer(many=False)
    issuedTo = InvoiceIssuedToSerializer(many=False)
    installmentId = serializers.UUIDField(source='installment.id', read_only=True)
    installmentAmount = serializers.DecimalField(max_digits=10, decimal_places=2, source='subTotal', read_only=True)
    installmentDescription = serializers.CharField(source='installment.description', read_only=True)
    issuedAt = serializers.DateTimeField(format='%b %d, %Y %H:%M', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'issuedBy', 'issuedTo', 'installmentId', 'installmentAmount', 
                  'installmentDescription', 'unit', 'unitPrice', 'notes', 'issuedAt']

    @extend_schema_field(serializers.CharField)
    def get_unit(self, obj):
        return obj.installment.unit.get_code()

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_unitPrice(self, obj):
        return obj.installment.unit.totalPrice

    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''

        data_preprocessed = {}

        for field in data: 
            if field not in ['issuedBy', 'issuedTo']:
                data_preprocessed[field] = data[field]
            else:
                if isinstance(data.get(field), str):
                    try:
                        processed_field = json.loads(data[field])
                        if processed_field and not isinstance(processed_field, dict):
                            raise serializers.ValidationError({field: 'Field must be an object, not a string representation of other types.'})
                        data_preprocessed[field] = processed_field
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({field: 'Invalid JSON format'})
                else:
                    data_preprocessed[field] = data[field]

        return super().to_internal_value(data_preprocessed)
 

    @transaction.atomic
    def create(self, validated_data):
        #Get installment from context
        installment = self.context.get('installment')
        subTotal = installment.amount
        issuedBy = validated_data.get('issuedBy')
        issuedTo = validated_data.get('issuedTo')
        
        #Create and return invoice 
        invoice = Invoice.objects.create(issuedBy=issuedBy,
                                         issuedTo=issuedTo,
                                         subTotal=subTotal,
                                         installment=installment,
                                         notes=validated_data.get('notes')
                                        )
        return invoice

#Serializer to get default data for the create installment invoice endpoint
class GetInstallmentInvoiceSerializer(UserPermissionsMixin, serializers.ModelSerializer):
    issuedBy = serializers.SerializerMethodField()
    issuedTo = serializers.SerializerMethodField()
    installmentId = serializers.UUIDField(source='id')
    installmentAmount = serializers.DecimalField(max_digits=10, decimal_places=2, source='amount')
    installmentDescription = serializers.CharField(source='description')
    unit = serializers.SerializerMethodField()
    unitPrice = serializers.DecimalField(max_digits=10, decimal_places=2, source='unit.totalPrice')

    class Meta:
        model = Installment
        fields = ['issuedBy', 'issuedTo', 'installmentId', 'installmentAmount', 
                  'installmentDescription', 'unit', 'unitPrice']
    
    @extend_schema_field({'type': 'object', 'properties': {'company': {'type': 'string'},
        'phone': {'type': 'string'}, 'email': {'type': 'string'}, 'address': {'type': 'string'}}})
    def get_issuedBy(self, obj):
        return {
            'company': 'Default company name (editable)?',
            'phone': 'Default company phone (editable)',
            'email': 'Default company email (editable)',
            'address': 'Default company address (editable)'
        }

    @extend_schema_field({'type': 'object', 'properties': {'clientName': {'type': 'string'},
        'clientPhone': {'type': 'string'}, 'clientEmail': {'type': 'string'}}})
    def get_issuedTo(self, obj):
        return {
            'clientName': obj.unit.client.name,
            'clientPhone': obj.unit.client.phone,
            'clientEmail': obj.unit.client.email
        }

    @extend_schema_field(serializers.CharField)
    def get_unit(self, obj):
        return obj.unit.get_code()

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_unitPrice(self, obj):
        return obj.unit.totalPrice


#Nested serializer for payment details (units, amounts, etc.)
class PaymentDetailSerializer(serializers.Serializer):
    unitCode = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    dueDate = serializers.DateField(format='%b %d, %Y', input_formats=DATE_INPUT_FORMATS, required=True)
    paymentType = serializers.CharField(required=False)
    description = serializers.CharField(required=False)

#Serializer for creating custom invoices 
class CustomInvoiceSerializer(serializers.ModelSerializer):
    issuedBy = InvoiceIssuedBySerializer(many=False)
    issuedTo = InvoiceIssuedToSerializer(many=False)
    paymentDetails = PaymentDetailSerializer(many=True)
    subtotalAfterDiscount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, write_only=True)
    issuedAt = serializers.DateTimeField(format='%b %d, %Y %H:%M', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'issuedBy', 'issuedTo', 'paymentDetails', 'currency', 'subTotal',
                  'subtotalAfterDiscount', 'discount', 'vat', 'grandTotal', 'notes', 'issuedAt']
        extra_kwargs = {'discount': {'required': False}, 'vat': {'required': False}, 'subTotal': {'required': False}, 
                        'grandTotal': {'required': False}, 'notes': {'required': False}}

    @extend_schema_field(serializers.DecimalField(max_digits=10, decimal_places=2))
    def get_subtotalAfterDiscount(self, obj):
        return Invoice.calculate_subtotalAfterDiscount(obj.subtotal, obj.discount)


    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''
        
        data_preprocessed = {}

        for field in data: 
            if field not in ['issuedBy', 'issuedTo', 'paymentDetails']:
                data_preprocessed[field] = data[field]
            else:
                if isinstance(data.get(field), str):
                    try:
                        processed_field = json.loads(data[field])
                        if processed_field and not isinstance(processed_field, dict):
                            raise serializers.ValidationError({field: 'Field must be an object, not a string representation of other types.'})
                        data_preprocessed[field] = processed_field
                    except json.JSONDecodeError:
                        raise serializers.ValidationError({field: 'Invalid JSON format'})
                else:
                    data_preprocessed[field] = data[field]

        return super().to_internal_value(data_preprocessed)

    
    #Validate data 
    def validate(self, data):
        paymentDetails = data.get('paymentDetails')
        subTotal = data.get('subTotal')
        grandTotal = data.get('grandTotal')

        #Validate subtotal and grandTotal  #TODO - for debugging only 
        if paymentDetails:
            if subTotal:
                subTotal_from_payments = sum([payment.get('amount',0) for payment in paymentDetails])
                if subTotal != subTotal_from_payments or abs(subTotal_from_payments - subTotal) > 1.0:
                    raise serializers.ValidationError({'subTotal': f'subTotal was calculated incorrectly.\nSubmitted subtotal ({subTotal}) != subtotal from payment amounts in table ({subTotal_from_payments})'})
            else:
                subTotal = sum([payment.get('amount',0) for payment in paymentDetails])
                data['subTotal'] = subTotal
            
            if grandTotal:
                grandTotal_submitted = round(float(grandTotal), 3)
                grandTotal_actual = round(float(subTotal + data.get('vat', 0) - data.get('discount', 0)), 3)
                if grandTotal_submitted > grandTotal_actual:
                    raise serializers.ValidationError({'grandTotal': f'Grand total is calculated incorrectly. Grand total submitted ({grandTotal_submitted}) > actual grand total ({grandTotal_actual})'})
                elif grandTotal_submitted < grandTotal_actual:
                    raise serializers.ValidationError({'grandTotal': f'Grand total is calculated incorrectly. Grand total submitted ({grandTotal_submitted}) < actual grand total ({grandTotal_actual})'})
            else:
                data['grandTotal'] = subTotal + data.get('vat', 0) - data.get('discount', 0)

        return data 


#Serializer for uploading invoice file
class UploadInvoiceFileSerializer(serializers.ModelSerializer):
    invoiceId = serializers.UUIDField(required=True, source='id')
    invoice_pdf = serializers.FileField(use_url=True, required=True)
    issuedAt = serializers.DateTimeField(format='%b %d, %Y %H:%M:%S', read_only=True)

    class Meta:
        model = Invoice
        fields = ['invoiceId', 'invoice_pdf', 'issuedAt']
        extra_kwargs = {'invoice_pdf': {'required': True}}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'GET':
            self.fields.pop('invoiceId', None)
            self.fields.pop('issuedAt', None)

    def to_internal_value(self, data):
        '''Parses nested serializers data if passed as JSON strings.'''
        data_preprocessed = {}
        for field in data: 
            if field == 'invoice_pdf' and data[field] == '':
                    data_preprocessed[field] = None
            else:
                data_preprocessed[field] = data[field]
        return super().to_internal_value(data_preprocessed)


    def validate_invoiceId(self, invoiceId):
        try:
            Invoice.objects.get(id=invoiceId)
        except Invoice.DoesNotExist:
            raise serializers.ValidationError('Incorrect invoice id. Submitted invoice id does not match any invoice in the database.')
        return invoiceId
    

    @transaction.atomic
    def create(self, validated_data):
        #Get current invoice
        invoice = Invoice.objects.get(id=validated_data['id'])
        
        #upload pdf file 
        invoice.invoice_pdf = validated_data['invoice_pdf']
        invoice.save(update_fields=['invoice_pdf'])

        return invoice
    
#Serializer for retrieving invoice file
class GetInvoiceFileSerializer(serializers.ModelSerializer):
    invoice_pdf = serializers.FileField(use_url=True, required=True)
    class Meta:
        model = Invoice
        fields = ['invoice_pdf']