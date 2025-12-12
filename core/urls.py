from django.urls import path
from core.views.general import DashboardAPIView, ListAuditLogsAPIView
from core.views.approvals import ListUnitsForApprovalAPIView, PreviewApproveUnitAPIView, ApproveUnitAPIVIew
from core.views.units import ListUnitsAPIView, CreateUnitAPIView, RetrieveUnitAPView, UpdateUnitAPIView, DeleteUnitAPIView
from core.views.clients import ListClientsAPIView, CreateClientAPIView, RetrieveClientAPIView, UpdateClientAPIView, DeleteClientAPIView
from core.views.payments import (ListPaymentsAPIView, UpdatePaymentAPIView, CreateInstallmentInvoiceAPIView, UploadInvoiceAPIView, 
                                CreateCustomInvoiceAPIView, RetrieveInstallmentInvoiceAPIView)


urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    #path('notifications/', views.NotificationsAPIView.as_view(), name='notifications'),

    #Clients 
    path('clients/', ListClientsAPIView.as_view(), name='list_clients'),
    path('clients/new/', CreateClientAPIView.as_view(), name='create_client'),
    path('clients/<uuid:id>/view/', RetrieveClientAPIView.as_view(), name='view_client'),
    path('clients/<uuid:id>/edit/', UpdateClientAPIView.as_view(), name='update_client'),   
    path('clients/<uuid:id>/delete/', DeleteClientAPIView.as_view(), name='delete_client'),

    #Units
    path('units/', ListUnitsAPIView.as_view(), name='list_units'),
    path('units/new/', CreateUnitAPIView.as_view(), name='create_unit'),
    path('units/<uuid:id>/view/', RetrieveUnitAPView.as_view(), name='view_unit'),
    path('units/<uuid:id>/edit/', UpdateUnitAPIView.as_view(), name='update_unit'),
    path('units/<uuid:id>/delete/', DeleteUnitAPIView.as_view(), name='delete_unit'),
    
    #Payment Plans
    path('invoices/upload/', UploadInvoiceAPIView.as_view(), name='upload_invoice'),
    path('payment-plans/', ListPaymentsAPIView.as_view(), name='list_payments'),
    path('payment-plans/create-invoice/', CreateCustomInvoiceAPIView.as_view(), name='create_custom_invoice'),
    path('payment-plans/<uuid:payment_id>/mark-paid/', UpdatePaymentAPIView.as_view(), name='update_payment'),
    path('payment-plans/<uuid:payment_id>/invoice/create/', CreateInstallmentInvoiceAPIView.as_view(), name='create_installment_invoice'),
    path('payment-plans/<uuid:payment_id>/invoice/view/', RetrieveInstallmentInvoiceAPIView.as_view(), name='view_installment_invoice'),

    #Approvals 
    path('units/approvals/', ListUnitsForApprovalAPIView.as_view(), name='list_pending_units'),
    path('units/approvals/<uuid:unit_id>/approve/', ApproveUnitAPIVIew.as_view(), name='approve_pending_unit'),
    path('units/approvals/<uuid:unit_id>/view/', PreviewApproveUnitAPIView.as_view(), name='view_or_approve_pending_unit'), 

    #Audit Logs 
    path('audit-logs/', ListAuditLogsAPIView.as_view(), name='list_audit_logs')

]
