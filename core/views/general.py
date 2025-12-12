from rest_framework import status
from rest_framework import generics
from django.db.models import Count, Q
from rest_framework.response import Response
from core.utils import calculate_percentage, calculate_yearly_growth
from core.serializers.general import DashboardSerializer, MonthCountSerializer, AuditLogSerializer
from rest_framework.permissions import IsAuthenticated
from core.models import Client, Unit, AuditLog
from core.pagination import AuditLogsPaginator
from users.permissions import AdminOnly
from core.utils import extend_schema
from users.models import User


#Dashboard API View 
@extend_schema(tags=['Dashboard'])
class DashboardAPIView(generics.GenericAPIView):
    serializer_class = DashboardSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get(self, request, *args, **kwargs):
        #General statistics 
        #Aggregate unit queries into one query
        unit_aggregates = Unit.objects.aggregate(
            total_units=Count('id'),
            total_residential_units=Count('id', filter=Q(activity='RESIDENTIAL')),
            total_commercial_units=Count('id', filter=Q(activity='COMMERCIAL')),
            available_units=Count('id', filter=Q(status='AVAILABLE')),
            sold_units=Count('id', filter=Q(status='SOLD')),
            hold_units=Count('id', filter=Q(status='HOLD')),
            reserved_units=Count('id', filter=Q(status='RESERVED')),
            pending_units=Count('id', filter=Q(status='PENDING')),
        )
        #total units and commercial perc
        total_units = unit_aggregates['total_units']
        commercial_units_perc = calculate_percentage(vals=unit_aggregates['total_commercial_units'], total=total_units)
        residential_units_perc = (100 - commercial_units_perc) if commercial_units_perc > 0 \
            else calculate_percentage(vals=unit_aggregates['total_residential_units'], total=total_units)
        
        #Prepare unit status stats
        unit_status_keys = list(unit_aggregates.keys())[2:] 
        unit_status_vals = calculate_percentage(vals=[unit_aggregates[key] for key in unit_status_keys], total=total_units)

        data = {
            'totalUnits': total_units,
            'totalClients': Client.objects.count(),
            'totalUsers': User.objects.count(),
            'unitTypePercentages': {
                'residential_perc': f'{residential_units_perc}%',
                'commercial_perc': f'{commercial_units_perc}%'
                },
            'unitStatusPercentages': {f'{key.replace('_units', '')}_perc':f'{val}%' for key,val in zip(unit_status_keys, unit_status_vals) if val > 0},
            'units_byMonth': MonthCountSerializer(calculate_yearly_growth(Unit), many=True).data,
            'clients_byMonth': MonthCountSerializer(calculate_yearly_growth(Client), many=True).data
        }
        
        #Serializer data and return response 
        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)



#AUDIT LOGS VIEW 
@extend_schema(tags=['Audit Logs'])
class ListAuditLogsAPIView(generics.ListAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [AdminOnly]
    filter_backends = []
    pagination_class = AuditLogsPaginator
    ordering = ['-createdAt']
