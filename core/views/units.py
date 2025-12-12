from django.db import transaction
from rest_framework import status
from rest_framework import generics
from rest_framework.response import Response
from django.forms.models import model_to_dict
from users.permissions import SystemUserPermissions
from core.utils import extend_schema, format_description
from core.models import Client, Unit, Installment, InstallmentConfiguration
from core.serializers.units import ListUnitSerializer, CreateUnitSerializer, GetUnitChoicesSerializer, RetrieveUnitSerializer, UpdateUnitSerializer
from core.mixins import AutoDispatchLogsMixin, BulkPaymentLogsMixin, AuditDeleteMixin
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from core.filters import UnitFilter


#UNIT VIEWS 
#List all units API view
@extend_schema(tags=['Units'])
class ListUnitsAPIView(generics.ListAPIView):
    serializer_class = ListUnitSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Units Data Table'
    filterset_class = UnitFilter
    ordering = ['-updatedAt']
    search_fields = ['unitCode', 'building', 'status']
    ordering_fields = ['unitCode', 'activity', 'indoorSize', 'outdoorSize', 'totalPrice', 'status']
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    def get_queryset(self):
        user = self.request.user
        if user and getattr(user, 'role', None) == 'SALES':
            return Unit.objects.select_related('client').filter(status='AVAILABLE')
        return Unit.objects.select_related('client').all()


#Create new unit API view 
@extend_schema(tags=['Units'])
class CreateUnitAPIView(AutoDispatchLogsMixin, BulkPaymentLogsMixin, generics.GenericAPIView):
    queryset = Unit.objects.select_related('client').all()
    permission_classes = [SystemUserPermissions]
    required_permission = 'Create Unit'
    parser_classes = [MultiPartParser, FormParser, JSONParser]


    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateUnitSerializer
        return GetUnitChoicesSerializer
    

    def get(self, request, *args, **kwargs):
        #Create an empty instance to get the choices
        serializer = self.get_serializer()
        
        #Get the choices data
        choices_data = {
            'newClient': {'name': None, 'email': None, 'phone': None},  
            'client_choices': [choice for choice in serializer.fields['client_choices'].choices],
            'floor_choices': [choice for choice in serializer.fields['floor_choices'].choices],
            'status_choices': [choice for choice in serializer.fields['status_choices'].choices],
            'activity_choices': [choice for choice in serializer.fields['activity_choices'].choices]
        }
        
        return Response(choices_data, status=status.HTTP_200_OK)
    

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        user = self.request.user
        if serializer.is_valid():
            #Get validated data from serializer 
            validated_data = serializer.validated_data

            #Retrieve and remove client and payment information (if any)
            new_client = validated_data.pop('newClient', None)
            new_client_choice = validated_data.pop('client_choices', None)
            installmentConfigs = validated_data.pop('unit_configs', [])
            paymentSchedule = validated_data.pop('unit_installments', [])
 
            #Create Unit object 
            unit = Unit.objects.create(**validated_data)

            #save new client if status changed from available
            if validated_data.get('status') != 'AVAILABLE':
                if new_client: 
                    unit.client = Client.objects.create(**new_client)
                elif new_client_choice:
                    unit.client = Client.objects.get(name=new_client_choice)
                unit.save(update_fields=['client'])

            #add audit log for new unit created
            created_data = model_to_dict(unit)
            if unit.contract:
                created_data['contract'] = 'Uploaded' 
            self.add_log(
                user=user, 
                action='Created',
                instance=unit,
                old_data={},
                new_data=created_data
            )

            if validated_data.get('enablePaymentPlan'):
                #Create new installment configurations 
                for config in installmentConfigs:
                    created_config = InstallmentConfiguration.objects.create(unit=unit, **config)
                    #log new configurations 
                    self.add_log_config_created(user=user, config=created_config)
                
                #Bulk created new installments from schedule 
                installments_to_create = [
                        Installment(unit=unit,
                                    amount=installment['amount'],
                                    dueDate=installment['dueDate'],
                                    description=format_description(installment)
                                ) for installment in paymentSchedule
                    ]
                
                #create and log new installments
                if installments_to_create:
                    Installment.objects.bulk_create(installments_to_create)           
                    self.add_log_installments_creation(user=user, unit=unit, paymentSchedule=paymentSchedule)

                
                #Refresh unit instance and return response
                unit.refresh_from_db()
                data = self.get_serializer(unit, context=self.get_serializer_context()).data
                return Response({'message': 'Unit and installments created successfully', 'data': data}, status=status.HTTP_201_CREATED)

            unit.refresh_from_db()
            data = self.get_serializer(unit, context=self.get_serializer_context()).data
            return Response({'message': 'Unit created successfully', 'data': data}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#Unit retrieve API view  
@extend_schema(tags=['Units'])
class RetrieveUnitAPView(generics.RetrieveAPIView):
    queryset = Unit.objects.select_related('client').all()
    serializer_class = RetrieveUnitSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Unit Details'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'



#Unit update API view 
@extend_schema(tags=['Units'])
class UpdateUnitAPIView(AutoDispatchLogsMixin, BulkPaymentLogsMixin, generics.RetrieveAPIView, generics.GenericAPIView):
    queryset = Unit.objects.select_related('client')\
        .prefetch_related('unit_configs', 'unit_installments').all()
    serializer_class = UpdateUnitSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Update Unit'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'


    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.lookup_url_kwarg in self.kwargs:
            unit = self.get_object()
            context['unit'] = unit 
            context['paid_installments_lookup'] = {(description.rsplit(' - ', 1)[0], due_date) 
                                                   for description,due_date in 
                                                   unit.unit_installments.filter(paid=True)\
                                                   .values_list('description', 'dueDate')}
        return context

    @transaction.atomic 
    def put(self, request, *args, **kwargs):
        unit = self.get_object()
        user = self.request.user 
        old_unit = model_to_dict(unit)

        #serialize data and return data validated 
        serializer = self.get_serializer(unit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        #remove non-model field
        totalPayment = validated_data.pop('totalPayment', None)

        #determine if payment plan is enabled
        if 'enablePaymentPlan' not in validated_data:
            validated_data['enablePaymentPlan'] = unit.enablePaymentPlan
        
        #Update fields without special conditions 
        fields_to_update = ['building', 'floor', 'unitCode', 'indoorSize', 'outdoorSize', 'areaPrice', 'totalPrice', 
                            'enablePaymentPlan', 'activity', 'holdDeposit', 'holdExpiryDate', 'notes']

        for field, value in validated_data.items():
            if field in fields_to_update:
                setattr(unit, field, value)
        
        #Update contract (and delete old one if found) 
        contract = validated_data.get('contract', None)
        reuploaded_contract = False
        if contract and contract != unit.contract: 
            if unit.contract:
                # old_unit['contract'] = 'Deleted'
                unit.contract.delete(save=False)    #remove old contract
            unit.contract = contract 
            reuploaded_contract = True 

        #Update fields based on special conditions
        if validated_data.get('status') != 'AVAILABLE':
            current_client = unit.client 
            new_client = validated_data.pop('newClient', None)
            new_client_choice = validated_data.pop('clientsBase_choices', None)

            #Update client with new or existing one (if changed)
            if current_client and (new_client or new_client_choice):
                if new_client and current_client.name != new_client.get('name'):                        
                    unit.client = Client.objects.create(**new_client)
                elif new_client_choice and new_client_choice != current_client.name:
                    unit.client = Client.objects.get(name=new_client_choice)       
        else:
            #else status was changed to available by the admin remove client information
            if unit.status != 'AVAILABLE' and self.request.user.role == 'ADMIN':
                old_status = unit.status
                unit.status = validated_data.get('status')  #save new status 
                unit.cascade_status_change()  #remove client info (if any)
                #log unit change 
                self.add_log(
                    user=self.request.user,
                    action='Updated',
                    instance=unit,
                    old_data={'status': old_status},
                    new_data={'status': 'AVAILABLE', 
                              'note': 'Client details automatically removed'}
                    )
            else:
                #else, leave it to the admin to do the approval
                unit.requestedStatus = validated_data.get('status')
                unit.status = 'PENDING'


        #Update payment plan if changed 
        installmentConfig_before = unit.unit_configs.all()
        installmentConfig_after = validated_data.pop('unit_configs', [])    
        paymentSchedule_before = unit.unit_installments.only('id', 'amount', 'dueDate', 'paid', 'description') 
        paymentSchedule_after = validated_data.pop('unit_installments', [])
                        
        #if payment plan is enabled handle updates to unit installments 
        if validated_data.get('enablePaymentPlan'):
            #Handle unit installment configuration updates
            InstallmentConfiguration.update_configurations(
                                                        user=user, 
                                                        unit=unit, 
                                                        installmentConfig_before=installmentConfig_before, 
                                                        installmentConfig_after=installmentConfig_after, 
                                                        audit_logger=self
                                                    )
            
            #Handle unit payment plan updates 
            Installment.update_installments(
                                        user=user,
                                        unit=unit, 
                                        paymentSchedule_before=paymentSchedule_before,
                                        paymentSchedule_after=paymentSchedule_after,
                                        audit_logger=self
                                    )

        else:
            #if payment plan was disabled, delete unit configs and installments 
            if installmentConfig_before or paymentSchedule_before:
                deleted_configs = installmentConfig_before.delete()
                self.add_log_config_disabled(user=user, unit=unit, deleted_count=deleted_configs[0])

                deleted_installments = paymentSchedule_before.filter(paid=False).delete()
                self.add_log_installments_disabled(user=user, unit=unit, deleted_count=deleted_installments[0])

        
        #Add reference to the user updating the unit and track status changes
        unit.updatedBy = f'{self.request.user.name} ({self.request.user.role})'
        status_changed = True if old_unit.get('status') != validated_data.get('status') else False 

        #save unit changes 
        unit.save(status_changed=status_changed)
        updated_unit = model_to_dict(unit)
        
        #normalize file field before logging (contract)
        if reuploaded_contract:
            updated_unit['contract'] = 'Uploaded new contract'

        #log overall unit changes 
        self.add_log(
            user=self.request.user,
            action='Updated',
            instance=unit,
            old_data=old_unit,
            new_data=updated_unit
        )

        #refresh unit with latest db updates
        unit.refresh_from_db()
        serialized_response = self.get_serializer(unit, context=self.get_serializer_context()).data
        serialized_response.pop('totalPayment', None)

        #attach client name (if found)
        if unit.client:
            serialized_response = {**serialized_response, 'client': unit.client.name}

        #NOTE - Remove when arranged with frontend
        if validated_data.get('enablePaymentPlan') and not totalPayment:  
            serialized_response['WARNING'] = 'totalPayment was not returned (required for validation)!'
        ####

        return Response(serialized_response, status=status.HTTP_200_OK)



#Unit delete API view 
@extend_schema(tags=['Units'])
class DeleteUnitAPIView(AuditDeleteMixin, generics.DestroyAPIView):
    queryset = Unit.objects.all()
    serializer_class = UpdateUnitSerializer 
    permission_classes = [SystemUserPermissions] 
    required_permission = 'Delete Unit'
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

