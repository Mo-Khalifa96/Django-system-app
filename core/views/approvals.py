from core.models import Unit
from django.db import transaction
from rest_framework import generics
from core.utils import extend_schema
from core.mixins import AuditMixin
from rest_framework.filters import SearchFilter
from django.db.models.functions import Concat
from django.db.models import Value, CharField
from users.permissions import SystemUserPermissions
from core.serializers.approvals import (ListUnitsForApprovalSerializer, 
                                        PreviewApproveUnitSerializer, 
                                        ApproveUnitSerializer)



#APPROVALS VIEWS
#List all units awaiting approval or approve changes APIV View 
@extend_schema(tags=['Approvals'])
class ListUnitsForApprovalAPIView(generics.ListAPIView):
    serializer_class = ListUnitsForApprovalSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'View Approvals'
    ordering = ['-updatedAt']
    search_fields = ['code', 'client__name', 'updatedBy']
    filter_backends = [SearchFilter]

    def get_queryset(self):
        return Unit.objects.filter(status='PENDING', isApproved=False)\
                .annotate(code=Concat(
                        'building', Value('-'),'floor',Value('-'),'unitCode',
                         output_field=CharField())
                        )


#Approve unit API view
@extend_schema(tags=['Approvals'])
class ApproveUnitAPIVIew(AuditMixin, generics.UpdateAPIView):
    queryset = Unit.objects.filter(status='PENDING', isApproved=False)
    serializer_class = ApproveUnitSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Approve Pending Units'
    lookup_field = 'id'
    lookup_url_kwarg = 'unit_id'

    @transaction.atomic
    def perform_update(self, serializer):
        unit = self.get_object()
        old_data = {'status': unit.status, 'isApproved': unit.isApproved}

        if serializer.validated_data['isApproved']:
            if unit.requestedStatus == 'Available':
                unit.cascade_status_change()
            unit.change_approval(approve_changes=True)
            new_data = {'status': unit.status, 'isApproved': unit.isApproved}
        else:
            unit.change_approval(approve_changes=False)
            new_data = None
        
        #refresh serializer instance with updated data 
        serializer.instance.refresh_from_db()

        #log changes (if any)
        if new_data:
            self.log_audit(
                user=self.request.user, 
                action='Updated',
                instance=unit, 
                old_data=old_data, 
                new_data=new_data
            )        


#Preview unit detail and/or approve changes API VIew
@extend_schema(tags=['Approvals'])
class PreviewApproveUnitAPIView(AuditMixin, generics.RetrieveUpdateAPIView):  #NOTE -> don't have access yet
    queryset = Unit.objects.filter(status='PENDING', isApproved=False)
    serializer_class = PreviewApproveUnitSerializer
    permission_classes = [SystemUserPermissions]
    required_permission = 'Approve Pending Units'
    lookup_field = 'id'
    lookup_url_kwarg = 'unit_id'

    @transaction.atomic
    def perform_update(self, serializer):
        unit = self.get_object()
        old_data = {'status': unit.status, 'isApproved': unit.isApproved}

        if serializer.validated_data['isApproved']:
            if unit.requestedStatus == 'Available':
                unit.cascade_status_change()
            unit.change_approval(approve_changes=True)
            new_data = {'status': unit.status, 'isApproved': unit.isApproved}
        else:
            unit.change_approval(approve_changes=False)
            new_data = None
        
        #refresh serializer instance with updated data 
        serializer.instance.refresh_from_db()

        #log changes (if any)
        if new_data:
            self.log_audit(
                user=self.request.user, 
                action='Updated',
                instance=unit, 
                old_data=old_data, 
                new_data=new_data
            )        
