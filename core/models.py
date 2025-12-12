import os 
import uuid 
from decimal import Decimal
from django.db import models
from django.db import transaction
from django.utils import timezone
from django.forms.models import model_to_dict
from django.core.validators import MinValueValidator
from django.core.serializers.json import DjangoJSONEncoder
from core.validators import validate_phone_number, file_validators
from core.utils import get_floor_num, determine_installment_type, format_description
from django.contrib.postgres.fields import ArrayField


#CLIENTS MODEL 
class Client(models.Model):
    #Client fields 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)  
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, validators=[validate_phone_number])
    companyName = models.CharField(max_length=255, blank=True, null=True)
    jobTitle = models.CharField(max_length=120, blank=True, null=True)
    address = models.CharField(max_length=300, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    zipcode = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    createdAt = models.DateField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    #Has reverse relations to the Unit model: units = Unit.objects.filter(client=self)
    #Accessible via client.client_units.all() (given the parameter, related_name='client_units')
    
    AUDIT_FIELDS = ['name', 'email', 'phone']

    class Meta: 
        db_table = 'Clients'
        verbose_name_plural = 'Clients'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.phone}'


#UNITS MODEL 
class Unit(models.Model):
    #Text choices for choice fields
    class UnitStatusChoices(models.TextChoices):
        AVAILABLE = 'AVAILABLE'
        SOLD = 'SOLD'
        HOLD = 'HOLD'
        RESERVED = 'RESERVED'
        PENDING = 'PENDING'

    class UnitActivities(models.TextChoices):
        RESIDENTIAL = 'RESIDENTIAL'
        COMMERCIAL = 'COMMERCIAL'
        LUXURY = 'LUXURY'
        VILLAS = 'VILLAS'

    class FloorChoices(models.TextChoices):
        Ground_Floor = 'Ground Floor'
        Floor_1 = 'Floor 1'
        Floor_2 = 'Floor 2'
        Floor_3 = 'Floor 3'
        Floor_4 = 'Floor 4'
        Floor_5 = 'Floor 5'
        Floor_6 = 'Floor 6'

    #Unit-related fields 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unitCode = models.CharField(max_length=100)
    status = models.CharField(max_length=25, choices=UnitStatusChoices.choices, default=UnitStatusChoices.AVAILABLE, db_index=True)
    building = models.CharField(max_length=100)  #bulding code
    floor = models.CharField(max_length=100, choices=FloorChoices.choices)   

    #Property details
    activity = models.CharField(max_length=25, choices=UnitActivities.choices, default=UnitActivities.RESIDENTIAL)
    indoorSize = models.FloatField(blank=True, null=True)
    outdoorSize = models.FloatField(blank=True, null=True)
    areaPrice = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)    
    totalPrice = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])  

    #Client, contract, price, deposit
    #Many-to-One relationship to the Client model (i.e., many units, one client)
    client = models.ForeignKey(Client, blank=True, null=True, on_delete=models.SET_NULL, db_index=True, related_name='client_units')  #related_name is the name used for reverse lookups --> e.g. client.cleint_units.all() to get units for a single client
    contractType = models.CharField(max_length=120, blank=True, null=True)
    contract = models.FileField(upload_to='contracts/', blank=True, null=True, validators=file_validators)
    enablePaymentPlan = models.BooleanField(default=False, blank=True, null=True)
    holdDeposit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)]) 
    holdExpiryDate = models.DateField(blank=True, null=True)

    #other fields 
    isApproved = models.BooleanField(default=False)
    requestedStatus = models.CharField(max_length=25, choices=UnitStatusChoices.choices, blank=True, null=True, db_index=True)
    notes = models.TextField(blank=True, null=True)
    createdAt = models.DateField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)    
    updatedBy = models.CharField(max_length=50, blank=True, null=True)

    #Has reverse relationships to InstallmentConfiguration and Installment 
    #Accessible via unit.unit_configs.all() (given the parameter, related_name='unit_configs')
     # or, unit.unit_installments.all() (given the parameter, related_name='unit_installments')

    AUDIT_FIELDS = ['unitCode', 'building', 'floor', 'status', 'activity', 'totalPrice', 'client__name', 
                    'contract', 'enablePaymentPlan', 'holdDeposit', 'holdExpiryDate', 
                    'installment_count', 'total_installments', 'total_amount']

    class Meta:
        db_table = 'Units'
        verbose_name_plural = 'Units'
        ordering = ['-createdAt']  
        unique_together = ['unitCode', 'building', 'floor']

    def __str__(self):
        return f'{self.building}-{get_floor_num(self.floor)}-{self.unitCode} ({self.client.name if self.client else 'no client'})'

    def get_code(self):
        return f'{self.building}-{get_floor_num(self.floor)}-{self.unitCode}'
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        #Replace contract file name with uuid identifier
        if self.contract and self.contract.name:
            filename = os.path.basename(self.contract.name)
            name_without_ext = os.path.splitext(filename)[0]
            if not all(c in '0123456789abcdef-' for c in name_without_ext.lower()):
                _, ext = os.path.splitext(self.contract.name)
                #Generate new UUID filename
                new_filename = f"{uuid.uuid4()}{ext}"
                self.contract.name = new_filename
        
        #Handle status changes 
        if self.pk and kwargs.pop('status_changed', False):
            self.requestedStatus = self.status 
            self.status = 'PENDING'
        super().save(*args, **kwargs)
        
    
    @transaction.atomic
    def change_approval(self, approve_changes):  
        if not self.isApproved:
            if approve_changes:
                #approve requested status  
                self.status = self.requestedStatus
                self.requestedStatus = None 
                self.isApproved = True 
                self.save(update_fields=['isApproved', 'status', 'requestedStatus'])
            else:
                if not self.isApproved:
                    #discard requested status 
                    self.requestedStatus = None   
                    self.save(update_fields=['requestedStatus'])
        return True

    #@transaction.atomic  #not needed if applying @transaction.atomic on the request
    #Update client-related details if status changes 
    def cascade_status_change(self):  
        self.client = None
        self.contractType = None
        self.contract.delete(save=False)
        self.contract = None
        self.holdDeposit = None
        self.holdExpiryDate = None
        return True 


#INSTALLMENT CONFIGURATIONS MODEL 
class InstallmentConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    every = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    startingMonth = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    repetitions = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)]) 
    startDate = models.DateField(blank=True, null=True, db_index=True)
    description = models.TextField(max_length=120, blank=True, null=True)
    #One unit, many configurations 
    unit = models.ForeignKey(Unit, related_name='unit_configs', on_delete=models.CASCADE, db_index=True)

    AUDIT_FIELDS = ['amount', 'repetitions', 'startDate', 'description']
                    
    class Meta:
        db_table = 'InstallmentConfigurations'
        verbose_name_plural = 'InstallmentConfigurations'

    def __str__(self):
        return f'{determine_installment_type(self.every)} installment plan for unit {str(self.unit)}'

    @classmethod
    @transaction.atomic 
    def update_configurations(cls, user, unit, installmentConfig_before, installmentConfig_after, audit_logger=None):
        configs_before_dict = {config.id: config for config in installmentConfig_before}
        configs_after_ids = {config.get('id') for config in installmentConfig_after if config.get('id')}
        configs_to_delete = installmentConfig_before.exclude(id__in=configs_after_ids)

        #Delete discarded configs (if any)
        if audit_logger and configs_to_delete.exists():
            for config in configs_to_delete:
                audit_logger.add_log_config_deleted(user=user, unit=unit, config=config)
        configs_to_delete.delete()

        for config in installmentConfig_after:
            config_id = config.pop('id', None)
            #Create new installment configurations 
            #If no id or misleading ids 
            if not config_id or (config_id not in configs_before_dict):
                config.pop('isEditable', None)
                created_config = cls.objects.create(unit=unit, **config)
                #log results 
                if audit_logger:
                    audit_logger.add_log_config_created(user=user, config=created_config)
            else:
                #else, config has an existing id in DB
                if not config.get('isEditable'):
                    continue 
                config.pop('isEditable', None)
                
                config_before = configs_before_dict.get(config_id)
                
                #Check if it needs to be updated (i.e. field values don't match)
                if any(getattr(config_before, field) != config[field] 
                 for field in config.keys()):
                    
                    #convert old config data to dict for comparison and logging
                    config_before_data = model_to_dict(config_before)

                    #update and save current configurations 
                    for field, value in config.items():
                        setattr(config_before, field, value)
                    config_before.save()

                    #log updated config 
                    if audit_logger:
                        audit_logger.add_log_config_updated(user=user, config=config_before, old_data=config_before_data, new_data=config)


#INSTALLMENTS MODEL 
class Installment(models.Model):
    class InstallmentTypes(models.TextChoices):
        DOWN_PAYMENT = 'Down Payment'
        MONTHLY = 'Monthly Payment'
        BI_MONTHLY = 'Bi-Monthly Payment'
        QUARTERLY = 'Quarterly Payment'
        SEMI_ANNUAL = 'Semi-Annual Payment'
        ANNUAL = 'Annual Payment'

    class PaymentStatusChoices(models.TextChoices):
        PENDING = 'PENDING'
        PAID = 'PAID'
        OVERDUE = 'OVERDUE'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]) 
    dueDate = models.DateField(db_index=True)
    paid = models.BooleanField(default=False, db_index=True)
    paidAt = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=PaymentStatusChoices.choices, default=PaymentStatusChoices.PENDING, db_index=True)
    installmentType = models.CharField(max_length=25, choices=InstallmentTypes.choices, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    createdAt = models.DateField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True) 
    #Many-to-One relationship to the Unit model (i.e., many installments, one unit)
    unit = models.ForeignKey(Unit, related_name='unit_installments', on_delete=models.CASCADE, db_index=True)
    
    AUDIT_FIELDS = ['unit__unitCode', 'amount', 'dueDate', 'status', 'paid', 'paidAt']

    class Meta:
        db_table = 'Installments'
        verbose_name_plural = 'Installments'
        ordering = ['-updatedAt']
        unique_together = ['unit', 'amount', 'dueDate', 'description']

    def __str__(self):
        return f'{self.description.capitalize()} - unit {str(self.unit)}'

    @transaction.atomic 
    def save(self, *args, **kwargs):
        if self._state.adding and self.description:
            if self.description.split(' - ')[0] in [choice[0] for choice in self.InstallmentTypes.choices]:
                self.installmentType = self.description.split(' - ')[0] 

        if self.paid and not self.paidAt:
            self.paidAt = timezone.now()
            self.status = 'PAID'        
        super().save(*args, **kwargs)

    
    @classmethod
    @transaction.atomic    
    def update_installments(cls, user, unit, paymentSchedule_before, paymentSchedule_after, audit_logger=None):
        installments_before_dict = {installment.id: installment for installment in paymentSchedule_before}
        installments_after_ids = {installment.get('id') for installment in paymentSchedule_after if installment.get('id')}
        deleted_installments = paymentSchedule_before.exclude(id__in=installments_after_ids).delete()

        #Delete discarded installments (if any)
        if audit_logger and deleted_installments[0] > 1:
            audit_logger.add_log_installments_deleted(user=user, unit=unit, delete_count=deleted_installments[0])
        
        installments_to_created = []
        installments_to_update = []
        for installment in paymentSchedule_after:
            installment_id = installment.pop('id', None)

            #Create new installments from payment schedule 
            #if no id or misleading ids 
            if not installment_id or (installment_id not in installments_before_dict):
                installments_to_created.append(
                    cls(unit=unit, 
                        amount=installment['amount'],
                        dueDate=installment['dueDate'],
                        description=format_description(installment) 
                        )
                )
            else:
                #else, config has an existing id in DB
                installment_before = installments_before_dict.get(installment_id)

                if installment_before.paid:
                    continue 

                if any(getattr(installment_before, field) != installment[field] 
                 for field in installment.keys()):
                    for field, value in installment.items():
                        setattr(installment_before, field, value)
                    installments_to_update.append(installment_before)
        
        #Bulk create (and log) new installments
        if installments_to_created:
            cls.objects.bulk_create(installments_to_created)
            if audit_logger:
                audit_logger.add_log_installments_extended(user=user, 
                                                           unit=unit,
                                                           created_count=len(installments_to_created),
                                                           paymentSchedule=paymentSchedule_after
                                                        )
        #Bulk update (and log) new installments
        if installments_to_update:
            cls.objects.bulk_update(installments_to_update)
            if audit_logger:
                audit_logger.add_log_installments_updated(user=user, unit=unit, updated_count=len(installments_to_update))


#INVOICES MODEL
class Invoice(models.Model):
    #invoice-installment fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issuedBy = models.JSONField()   #should include company name, address, phone, email
    issuedTo = models.JSONField() #models.ForeignKey(Client, related_name='client_invoices', on_delete=models.SET_NULL)
    subTotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    installment = models.OneToOneField(Installment, related_name='installment_invoice', on_delete=models.CASCADE, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    issuedAt = models.DateTimeField(auto_now_add=True)
    invoice_pdf = models.FileField(upload_to='invoices/', blank=True, null=True, validators=file_validators)
    
    #custom invoice fields
    currency = models.CharField(max_length=50, blank=True, null=True)
    paymentDetails = ArrayField(models.JSONField(encoder=DjangoJSONEncoder), default=list, blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, validators=[MinValueValidator(0)])
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, validators=[MinValueValidator(0)])
    grandTotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    # invoiceType = models.CharField()

    AUDIT_FIELDS = ['issuedBy', 'issuedTo', 'subTotal', 'grandTotal', 'issuedAt']

    class Meta:
        db_table = 'Invoices'
        verbose_name_plural = 'Invoices'
        ordering = ['-issuedAt']

    def __str__(self):
        if self.installment:
            return f'Invoice #{self.id} - unit {str(self.installment.unit)}'
        return f'Invoice #{self.id}'
    
    @transaction.atomic 
    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.installment:
                if not self.issuedTo:
                    self.issuedTo = {
                            'clientName': self.installment.unit.client.name,
                            'clientPhone': self.installment.unit.client.phone,
                            'clientEmail': self.installment.unit.client.email
                        }
                
                if not self.subTotal:
                    self.subTotal = self.installment.amount

                if not self.grandTotal:
                    self.grandTotal = Invoice.calculate_grandTotal(self.subTotal, self.vat, self.discount)

                #Check if total due is not the same as installment amount
                if self.grandTotal != self.installment.amount or (self.grandTotal - self.installment.amount > 1.0):
                    #adjust installment amount
                    self.installment.amount = self.grandTotal
                    self.installment.save()
            else:
                if self.subTotal:
                    self.grandTotal = self.subTotal
            
        #Handle pdf invoices - replace file name with uuid identifier
        if self.invoice_pdf and self.invoice_pdf.name:
            filename = os.path.basename(self.invoice_pdf.name)
            name_without_ext = os.path.splitext(filename)[0]
            if not all(c in '0123456789abcdef-' for c in name_without_ext.lower()):
                _, ext = os.path.splitext(self.invoice_pdf.name)
                #Generate new UUID filename
                new_filename = f"{uuid.uuid4()}{ext}"
                self.invoice_pdf.name = new_filename

        super().save(*args, **kwargs)

    @staticmethod
    def calculate_subtotal(quantity, unitPrice):
        return round(quantity * unitPrice, 2)
    
    @staticmethod
    def calculate_discount_from_perc(discount_perc, subtotal):
        return round(discount_perc*subtotal / 100, 2)
    
    def calculate_subtotalAfterDiscount(subtotal, discount):
        return round(subtotal + discount, 2)

    @staticmethod
    def calculate_grandTotal(subtotal, vat=0.0, discount=0.0):
        vat, discount = Decimal(vat), Decimal(discount)
        return round((subtotal + vat) - discount, 2)        


#AUDITLOGS MODEL
class AuditLog(models.Model):
    #Audit log fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=100, db_index=True)
    action = models.CharField(max_length=50)
    entity = models.JSONField(db_index=True)  
    changes = models.JSONField(db_index=True) 
    createdAt = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'AuditLogs'
        verbose_name_plural = 'AuditLogs'
        ordering = ['-createdAt']

    def __str__(self):
        return f'{self.action} by {self.user} on {self.entity} at {self.createdAt}'

