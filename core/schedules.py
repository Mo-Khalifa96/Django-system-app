from datetime import timedelta
from django.utils import timezone
from django_q.models import Schedule


#Function to setup scheduled tasks
def setup_scheduled_tasks():
    #Schedule daily task at midnight (00:00)
    daily_schedule, created = Schedule.objects.get_or_create(
        name='Update Overdue Payments',
        defaults={
            'func': 'core.tasks.update_overdue_installments',  
            'schedule_type': Schedule.CRON,
            'cron': '0 0 * * *',  #runs daily at midnight
            'repeats': -1  #repeats indefinitely
        }
    )

    #feedback
    if created:
        print(f"Created task: {daily_schedule.name}")
    else:
        print(f"Task already exists: {daily_schedule.name}")
    
    #Schedule quarterly task (every 3 months) 
    quarterly_schedule, created = Schedule.objects.get_or_create(
        name='Cleanup Audit Logs',
        defaults={
            'func': 'core.tasks.cleanup_audit_logs',  
            'schedule_type': Schedule.QUARTERLY,
            'next_run': timezone.now() + timedelta(days=90),  #runs every 3 months
            'repeats': -1   #repeats indefinitely
        }
    )

    #feedback
    if created:
        print(f"Created task: {quarterly_schedule.name}")
    else:
        print(f"Task already exists: {quarterly_schedule.name}")


