from django.core.management.base import BaseCommand
from core.schedules import setup_scheduled_tasks  

class Command(BaseCommand):
    help = 'Set up Django-Q2 scheduled tasks for payment updates and audit log cleanup'

    def handle(self, *args, **kwargs):
        try:
            setup_scheduled_tasks()
            self.stdout.write(self.style.SUCCESS('Scheduled tasks set up successfully!'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Error setting up scheduled tasks: {str(exc)}'))


#NOTE: to run at the start: 
    # echo "Setting up system's scheduled tasks..."
    # python manage.py setup_scheduled_tasks 
    # echo "Starting the Django-Q2 cluster"
    # python manage.py qcluster
