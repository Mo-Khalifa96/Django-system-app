import calendar
from datetime import date
from decimal import Decimal
from django.db.models import Count
from django.conf import settings
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth


#Utility functions
#Calculate percentages 
def calculate_percentage(vals, total):
    if total == 0:
        return [0 for _ in range(len(vals))] if isinstance(vals, list) else 0
    if isinstance(vals, (int, float, Decimal)):
        return round((vals / total) * 100, 2)
    else:
        return [round((val / total) * 100, 2) for val in vals]


#Calculate yearly growth (by count)
def calculate_yearly_growth(Model):
    today = date.today()
    start_date = today - relativedelta(months=12)

    results = []
    for i in range(12):
        target_date = start_date + relativedelta(months=i)
        month = target_date.month
        year = target_date.year

        count = Model.objects.only('createdAt').filter(createdAt__year=year, createdAt__month=month).count()
        results.append({
            'month': calendar.month_name[month],
            'count': count
        })
    
    return results


#Calculate yearly growth (by count)
def calculate_yearly_growth(Model):
    date_today = date.today()
    start_month = (date_today.replace(day=1) - relativedelta(months=11))

    #Group counts by month 
    queryset = (
        Model.objects
        .filter(createdAt__gte=start_month)
        .annotate(month=TruncMonth('createdAt'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    #Build a lookup dictionary {YYYY-MM-01: count}
    month_counts_dict = {item['month']: item['count'] for item in queryset}

    #Build result list in chronological order
    results = []
    for i in range(12):
        target_date = start_month + relativedelta(months=i)
        key = target_date.replace(day=1)
        results.append({
            'month': key.strftime('%B'),  
            'count': month_counts_dict.get(key, 0)
        })

    return results


#Custom function to determine installment config type 
def determine_installment_type(every):
    type_dict = {1: 'Monthly', 2: 'Bi-Monthly', 3: 'Quarterly', 6: 'Semi-Annual', 12: 'Annual'}
    return type_dict.get(every, f'Every {every} months')


#Custom function to format installment descriptions
def format_description(installment):
    month = str(installment.get('month'))
    description = installment['description']
    if month.isdigit() and '- Month' not in description:
        return f'{description} - Month {month}'
    return description


#Custom function for extracting floor number
def get_floor_num(floor):
    try:
        return int(floor.split()[-1])
    except:
        return 'G'



DEBUG = True  #TODO - remove

if DEBUG:   #TODO - apply this later: settings.DEBUG 
    from drf_spectacular.utils import (
        extend_schema_view,
        extend_schema_field,
        extend_schema_serializer,
        extend_schema,
        OpenApiExample
    )
else:
    #Use no-op functions in production
    def extend_schema_view(*args, **kwargs):
        def no_op_decorator(func):
            return func
        return no_op_decorator
    def extend_schema_field(*args, **kwargs):
        def no_op_decorator(func):
            return func
        return no_op_decorator
    
    def extend_schema_serializer(*args, **kwargs):
        def no_op_decorator(cls):
            return cls
        return no_op_decorator
    
    def extend_schema(*args, **kwargs):
        def no_op_decorator(func):
            return func
        return no_op_decorator
    
    class OpenApiExample:
        """No-op OpenApiExample class"""
        def __init__(self, *args, **kwargs):
            pass
        
        def __repr__(self):
            return f"<NoOpOpenApiExample>"
