import logging
from django.db import transaction
from rest_framework import generics
from core.utils import extend_schema
from django.db.models.functions import Concat
from django.db.models import Value, CharField
from core.filters import PaymentsFilter 
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from core.mixins import AuditUpdateMixin, PaymentsLogsMixin
from users.permissions import SystemUserPermissions
from core.models import Unit, Installment, Invoice
from core.serializers.payments import (ListPaymentPlanSerializer, InstallmentPaidUpdateSerializer, 
                                       InstallmentInvoiceSerializer, GetInstallmentInvoiceSerializer,
                                       CustomInvoiceSerializer, UploadInvoiceFileSerializer, GetInvoiceFileSerializer)

#PAYMENT PLANS VIEW 
#List payment plans API view
@extend_schema(tags=['Payment Plans'])
class ListPaymentsAPIView(generics.ListAPIView):
    serializer_class = ListPaymentPlanSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Payment Plans Data Table'
    filterset_class = PaymentsFilter
    ordering = ['-updatedAt']
    search_fields = ['unit', 'client__name']
    filter_backends = [DjangoFilterBackend, SearchFilter]

    def paginate_queryset(self, queryset):
        #use lower number of objects per page
        self.paginator.page_size = 15
        return super().paginate_queryset(queryset)
    
    def get_queryset(self):
        return Unit.objects.select_related('client')\
                .prefetch_related('unit_installments')\
                .filter(enablePaymentPlan=True)\
                .annotate(unit=Concat(
                        'building', Value('-'),'floor',Value('-'),'unitCode',
                         output_field=CharField())
                        )


#Update payment plans API view
@extend_schema(tags=['Payment Plans'])
class UpdatePaymentAPIView(AuditUpdateMixin, generics.UpdateAPIView):
    queryset = Installment.objects.all()
    serializer_class = InstallmentPaidUpdateSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Update Payment'
    lookup_field = 'id'
    lookup_url_kwarg = 'payment_id'



#Upload invoice PDF file API view
@extend_schema(tags=['Invoices'])
class UploadInvoiceAPIView(generics.CreateAPIView):
	queryset = Invoice.objects.all()
	serializer_class = UploadInvoiceFileSerializer
	permission_classes = [IsAuthenticated]


#Create custom invoice API view
@extend_schema(tags=['Invoices'])
class CreateCustomInvoiceAPIView(PaymentsLogsMixin, generics.CreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = CustomInvoiceSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Create Invoice'

    @transaction.atomic
    def perform_create(self, serializer):
        #Create invoice
        invoice = serializer.save()

        #Check if invoice is connected to a unit 
        paymentDetails = invoice.paymentDetails

        if paymentDetails:
            #instantiate logger
            logger = logging.getLogger('core')
            
            for payment in paymentDetails:
                if payment.get('unitCode'):
                    try:
                        unitCode = payment.get('unitCode')
                        unit, floor, building = unitCode.split('-')
                        unit = Unit.objects.filter(unitCode=unit, floor=f'Floor {floor}', building=building)
                        if unit.exists():
                            installment = Installment.objects.create(unit=unit,
                                                                    amount=payment.get('amount'),
                                                                    dueDate=payment.get('dueDate'),
                                                                    description=payment.get('description'))
                            if installment:
                                invoice.installment = installment
                                invoice.save(update_fields=['installment'])
                                                                
                        else:
                            logger.error(f'Installment could not be created. Unit ({unitCode}) does not exist.')

                    except Exception as exc:
                        logger.error(f'Installment could not be created. Possibly invalid data format for unitCode: {unitCode}')
                        logger.error(f'\n====Full error message:====\n{exc}\n\n========')

        #log custom invoice creation 
        self.log_custom_invoice_issued(invoice=invoice)


#Create invoice for installment API view
@extend_schema(tags=['Invoices'])
class CreateInstallmentInvoiceAPIView(PaymentsLogsMixin, generics.RetrieveAPIView, generics.CreateAPIView):
    queryset = Installment.objects.select_related('unit')\
      .prefetch_related('installment_invoice').all()
    permission_classes = [SystemUserPermissions]
    required_permission = 'Create Invoice'
    lookup_field = 'id'
    lookup_url_kwarg = 'payment_id'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InstallmentInvoiceSerializer
        elif self.request.method == 'GET':
           return GetInstallmentInvoiceSerializer
    
    def get_serializer_context(self):
      context = super().get_serializer_context()
      if self.lookup_url_kwarg in self.kwargs:
          context['installment'] = self.get_object()
      return context
    
    @transaction.atomic
    def perform_create(self, serializer):
        #Create invoice
        invoice = serializer.save()

        #log invoice creation 
        self.log_installment_invoice_issued(unit=invoice.installment.unit, invoice=invoice)


#View installment invoice API view 
@extend_schema(tags=['Invoices'])
class RetrieveInstallmentInvoiceAPIView(generics.RetrieveAPIView):
    queryset = Invoice.objects.select_related('installment').all()
    serializer_class = GetInvoiceFileSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Invoices'
    lookup_field = 'installment__id'
    lookup_url_kwarg = 'payment_id'

    # def get_object(self):
    #     try:
    #         return super().get_object()
    #     except:
    #         raise {'invoice_pdf': None}
