from core.models import Unit 
from django_filters.rest_framework import FilterSet, ChoiceFilter


#Units filter 
class UnitFilter(FilterSet):
    building = ChoiceFilter()
    status = ChoiceFilter(choices=Unit.UnitStatusChoices.choices)
    activity = ChoiceFilter(choices=Unit.UnitActivities.choices)

    class Meta:
        model = Unit
        fields = ['building', 'status', 'activity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Initialize building choices for choice filter
        buildings = Unit.objects.values_list('building', flat=True).distinct().order_by('building')
        self.filters['building'].field.choices = [(building, building) for building in buildings if building]


#Payments filter
class PaymentsFilter(FilterSet):
    status = ChoiceFilter(choices=Unit.UnitStatusChoices.choices)
    building = ChoiceFilter()

    class Meta: 
        model = Unit 
        fields = ['status', 'building']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Initialize building choices
        buildings = Unit.objects.values_list('building', flat=True).distinct().order_by('building')
        self.filters['building'].field.choices = [(building, building) for building in buildings if building]
