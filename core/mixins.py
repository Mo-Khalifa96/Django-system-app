import json
from core.models import AuditLog
from django.db import transaction
from django.forms.models import model_to_dict


#Permissions mixin for serializers 
class UserPermissionsMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.method == 'GET':
            data['metadata'] = {
                'userPermissions': request.user.get_user_permissions()
            }
        return data


#Base Mixin for Audit Logs 
class AuditMixin:
    @staticmethod
    def resolve_attr(instance, nested_field):
        """
        Resolve nested attributes like 'client__name'.\n

        Example:'n
         If attrs = 'client__organization__name', the lookup proceeds as: \n

            attrs = ['client', 'organization', 'name']\n
            value = instance  # assume instance is a Unit model\n
            
            for attr in attrs:
             • round 1: attr = 'client'  → value = getattr(unit, 'client', None)
             • round 2: attr = 'organization'  → value = getattr(unit.client, 'organization', None)
             • round 3: attr = 'name'  → value = getattr(unit.client.organization, 'name', None)

        """
        attrs = nested_field.split('__')
        value = instance
        for attr in attrs:
            value = getattr(value, attr, None)
        return value

    def get_user(self, user):
        '''Returns user's name and role.'''
        return f'{user.name} ({user.role.capitalize()})'

    def get_entity(self, instance):
        '''Returns model name and description.'''
        model_name = instance.__class__.__name__
        return {
            'entityName': model_name,
            'entityDetails': str(instance)
        }

    def get_changes(self, instance, old_data, new_data, summary=None):
        '''Return a dict of changed fields (filtered by AUDIT_FIELDS if set).'''
        
        changes = {}
        audit_fields = getattr(instance, 'AUDIT_FIELDS')

        for field in audit_fields:
            if '__' in field:
                old_value = self.resolve_attr(instance.__class__.objects.get(pk=instance.pk), field)
                new_value = self.resolve_attr(instance, field)
            else:
                old_value, new_value = old_data.get(field), new_data.get(field)           

            if old_value != new_value:
                changes[field] = {'from': old_value, 'to': new_value} if field != 'contract' else new_value
         
        if summary:
            changes['summary'] = summary
        return changes


    def log_audit(self, *, user, action, instance, old_data=None, new_data=None, summary=None, use_summary=None, deleted=None):
        '''Creates an AuditLog entry.'''
        
        if use_summary:
            changes = {'summary': summary} 
        elif deleted:
            changes = {f'{str(instance)}': 'All data removed.'}
        else:
            changes = self.get_changes(instance, old_data, new_data, summary=summary)
            if not changes:
                return
        
        #change to JSON serializable format 
        changes = json.loads(json.dumps(changes, default=str))

        #Create new audit log 
        AuditLog.objects.create(
            action=action,
            changes=changes,
            user=self.get_user(user),
            entity=self.get_entity(instance)
        )


#For POST requests
class AuditCreateMixin(AuditMixin):
    @transaction.atomic
    def perform_create(self, serializer):
        #Call any existing perform_create() logic
        super().perform_create(serializer)

        instance = serializer.instance
        self.log_audit(
            user=self.request.user,
            action='Created',
            instance=instance,
            old_data={},
            new_data=model_to_dict(instance))

#For PUT/PATCH requests
class AuditUpdateMixin(AuditMixin):
    @transaction.atomic
    def perform_update(self, serializer):
        instance = self.get_object()
        old_data = model_to_dict(instance)  

        #Call any existing perform_update() logic
        super().perform_update(serializer)

        #get updated data 
        updated_instance = serializer.instance 
        new_data = model_to_dict(updated_instance)

        self.log_audit(
            user=self.request.user,
            action='Updated',
            instance=updated_instance,
            old_data=old_data, 
            new_data=new_data)

#For DELETE requests
class AuditDeleteMixin(AuditMixin):
    @transaction.atomic
    def perform_destroy(self, instance):
        self.log_audit(
            user=self.request.user,
            action='Deleted',
            instance=instance,
            deleted=True)
        
        #Call parent's perform_destroy 
        super().perform_destroy(instance)

#Audit mixin for tracking payments
class PaymentsLogsMixin(AuditMixin):

    def log_installments_creation(self, unit, paymentSchedule):
        '''Logs the creation of installments for a unit'''

        self.log_audit(
            user=self.request.user,
            action='Payment Plan Created',
            instance=unit,
            old_data={'enablePaymentPlan': False,
                      'total_installments': None, 
                      'total_amount': None
                      },
            new_data={
                'enablePaymentPlan': True,
                'total_installments': len(paymentSchedule),
                'total_amount': sum(schedule['amount'] for schedule in paymentSchedule)
                },
            summary=f'Created {len(paymentSchedule)} installments'
        )

    def log_installments_extended(self, unit, created_count, paymentSchedule):
        '''Logs new installments added to existing plan'''

        self.log_audit(
            user=self.request.user, 
            action='Installments Created',
            instance=unit, 
            use_summary=True,
            summary={
                    'summary': f'Created {created_count} new installments',
                    'total_amount': sum(schedule['amount'] for schedule in paymentSchedule)
                    }
        )

    def log_installments_updated(self, unit, updated_count): 
        '''Logs bulk installment updates'''

        self.log_audit(
            user=self.request.user,
            action='Payment Plan Updated',
            instance=unit,
            use_summary=True,
            summary=f'Updated {updated_count} installments'
        )

    def add_log_installments_deleted(self, unit, delete_count):
        '''Logs bulk installment deletes'''

        self.log_audit(
            user=self.request.user,
            action='Installments Deleted',
            instance=unit,
            use_summary=True,
            summary=f'Deleted {delete_count} installments'
        )
    
    def log_installments_disabled(self, unit, deleted_count): 
        '''Logs installments removal when payment plan is disabled'''

        self.log_audit(
            user=self.request.user,
            action='Payment Plan Disabled',
            instance=unit,
            old_data={'enablePaymentPlan': True},
            new_data={'enablePaymentPlan': False},
            summary=f'Payment plan disabled. Removed {deleted_count} installments'
        )

    def log_config_created(self, config):
        '''Logs creation of a new unit installment configuration instance'''

        config_data = model_to_dict(config, exclude=['id'])
        self.log_audit(
            user=self.request.user,
            action='Created',
            instance=config,
            old_data={},
            new_data=config_data,
        )
    
    def log_config_updated(self, config, old_data, new_data):  
        '''Logs updates to a unit installment configuration instance'''

        self.log_audit(
            user=self.request.user,
            action='Updated',
            instance=config,
            old_data=old_data,
            new_data=new_data,
        )
    
    def log_config_deleted(self, unit, config):    
        '''Logs deletion of a unit installment configuration instance'''

        self.log_audit(
            user=self.request.user,
            action='Deleted',
            instance=unit,
            use_summary=True,
            summary={str(config): 'All data removed.'}
        )
    
    def log_config_disabled(self, unit, deleted_count):
        '''Logs bulk deletion of unit installment configurations after disabling payment plan'''

        self.log_audit(
            user=self.request.user,
            action='Installment Configuration(s) Removed',
            instance=unit, 
            deleted=True, 
            summary=f'Removed {deleted_count} installment configurations'
        )
    

    def log_installment_invoice_issued(self, unit, invoice):
        '''Logs the issuing of an installment-related invoice.'''

        self.log_audit(
            user=self.request.user,
            action='Invoice Issued',
            instance=unit,
            use_summary=True,
            summary=f'Invoice #{invoice.id} issued for unit {invoice.installment.unit.get_code()}'
        )

    def log_custom_invoice_issued(self, invoice):
        '''Logs the issuing of a custom invoice.'''

        self.log_audit(
            user=self.request.user,
            action='Invoice Issued',
            instance=invoice,
            use_summary=True,
            summary=f'Invoice #{invoice.id} issued to {invoice.issuedTo.get('clientName')} at {invoice.issuedAt.strftime('%b %d, %Y %H:%M:%S')}'
        )


#Audit Mixins for bulk audit logging
#Bulk logging for all data except payments
class BulkAuditMixin(AuditMixin):
    '''Mixin for general bulk logging'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._audit_logs_list = []
    
    def add_log(self, *, user, action, instance, old_data=None, new_data=None, summary=None, use_summary=False, deleted=None):
        '''Add to logs list instead of immediate save.'''

        if not hasattr(self, '_audit_logs_list'):
            self._audit_logs_list = []
            
        self._audit_logs_list.append({
            'user': user,
            'action': action,
            'instance': instance,
            'old_data': old_data,
            'new_data': new_data,
            'use_summary': use_summary, 
            'deleted': deleted,
            'summary': summary
        })
    
    def bulk_audit_log(self):
        '''Bulk create all saved audit logs at once.'''
        if not hasattr(self, '_audit_logs_list') or not self._audit_logs_list:
            return
            
        audit_logs = []
        for log in self._audit_logs_list:
            
            if log.get('use_summary'): 
                changes = {'summary': log.get('summary')} if isinstance(log.get('summary'), str) else log.get('summary')
            elif log.get('deleted'):
                    changes = {f'{str(log['instance'])}': 'All data removed.'}
            else:
                changes = self.get_changes(log['instance'], log['old_data'], log['new_data'], log.get('summary'))
                if not changes:
                    continue
            
            #change to JSON serializable format 
            changes = json.loads(json.dumps(changes, default=str))

            audit_logs.append(
                AuditLog(
                    action=log['action'],
                    changes=changes,
                    user=self.get_user(log['user']),
                    entity=self.get_entity(log['instance'])
                ))
        
        if audit_logs:
            AuditLog.objects.bulk_create(audit_logs)
        
        self._audit_logs_list = []


#Bulk logging methods for payment changes 
class BulkPaymentLogsMixin(AuditMixin):
    '''Mixin for bulk logging for payment operations only'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._audit_logs_list = []
    
    def add_log_installments_creation(self, user, unit, paymentSchedule):
        '''Logs the creation of installments for a unit'''
        
        self.add_log(
            user=user, 
            action='Payment Plan Created',
            instance=unit, 
            old_data={'enablePaymentPlan': False,
                      'total_installments': None, 
                      'total_amount': None
                      },
            new_data={
                'enablePaymentPlan': True,
                'total_installments': len(paymentSchedule),
                'total_amount': sum(schedule['amount'] for schedule in paymentSchedule)
                },
            summary=f'Created {len(paymentSchedule)} installments'
        )

    def add_log_installments_extended(self, user, unit, created_count, paymentSchedule):
        '''Logs new installments added to existing plan'''

        self.add_log(
            user=user, 
            action='Installments Created',
            instance=unit, 
            use_summary=True,
            summary={
                    'summary': f'Created {created_count} new installments',
                    'total_amount': sum(schedule['amount'] for schedule in paymentSchedule)
                    }
        )

    def add_log_installments_updated(self, user, unit, updated_count):
        '''Logs bulk installment updates'''

        self.add_log(
            user=user,
            action='Installments Updated',
            instance=unit,
            use_summary=True,
            summary=f'Updated {updated_count} installments'
        )

    def add_log_installments_deleted(self, user, unit, delete_count):
        '''Logs bulk installment deletes'''

        self.add_log(
            user=user,
            action='Installments Deleted',
            instance=unit,
            use_summary=True,
            summary=f'Deleted {delete_count} installments'
        )

    def add_log_installments_disabled(self, user, unit, deleted_count):
        '''Logs installments removal when payment plan is disabled'''

        self.add_log(
            user=user,
            action='Payment Plan Disabled',
            instance=unit,
            old_data={'enablePaymentPlan': True},
            new_data={'enablePaymentPlan': False},
            summary=f'Payment plan disabled. Removed {deleted_count} installments'
        )

    def add_log_config_created(self, user, config):
        '''Logs creation of a new unit installment configuration instance'''

        config_data = model_to_dict(config, exclude=['id'])
        self.add_log(
            user=user,
            action='Created',
            instance=config,
            old_data={},
            new_data=config_data,
        )
    
    def add_log_config_updated(self, user, config, old_data, new_data):
        '''Logs updates to a unit installment configuration instance'''

        self.add_log(
            user=user,
            action='Updated',
            instance=config,
            old_data=old_data,
            new_data=new_data,
        )
    
    def add_log_config_deleted(self, user, unit, config):
        '''Logs deletion of a unit installment configuration instance'''

        self.add_log(
            user=user,
            action='Deleted',
            instance=unit,
            use_summary=True,
            summary={str(config): 'All data removed.'}
        )

    def add_log_config_disabled(self, user, unit, deleted_count):
        '''Logs bulk deletion of unit installment configurations after disabling payment plan'''

        self.add_log(
            user=user,
            action='Installment Configuration(s) Removed',
            instance=unit,
            deleted=True,
            summary=f'Removed {deleted_count} installment configurations'
        )


#Mixin for executing bulk audit loggings (via dispatch method)
class AutoDispatchLogsMixin(BulkAuditMixin):
    '''Automatically bulk creates audit logs at the end of request.'''
    @transaction.atomic
    def dispatch(self, request, *args, **kwargs):
        try:
            response = super().dispatch(request, *args, **kwargs)
            #Auto dispatch logs after successful request
            if 200 <= response.status_code < 300:
                self.bulk_audit_log()
            else:
                if hasattr(self, '_audit_logs_list'):
                    self._audit_logs_list = []   #Clear logs response is not successful
            return response

        except Exception as exc:
            if hasattr(self, '_audit_logs_list'):
                self._audit_logs_list = []  #Clear audit logs on error
            raise exc

