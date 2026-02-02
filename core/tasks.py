import logging
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import Installment, AuditLog

#Initiate logger 
logger = logging.getLogger('django-q')

#Define task to update overdue installments
def update_overdue_installments():
    '''Daily task to update payment status to OVERDUE for unpaid installments past the due date.'''

    try:
        with transaction.atomic():
            #Today's date (timezone-aware)
            today = timezone.now()
            logger.info(f"Processing overdue installments for date: {today.strftime('%d/%m/%Y %I:%M %p')}")
            
            #Find installments that are overdue (and marked as pending)
            overdue_installments = Installment.objects.filter(
                dueDate__lt=today.date(),
                status=Installment.PaymentStatusChoices.PENDING
                )
            
            #Update installments status
            updated_count = overdue_installments.update(
                status=Installment.PaymentStatusChoices.OVERDUE,
                updatedAt=timezone.now()
                )

            #Log task results
            if updated_count > 0:
                logger.info(f"Updated {updated_count} unpaid installments to OVERDUE.")
            else:
                logger.info('No overdue installments found.')
            
    except Exception as exc:
        logger.error(f"Error updating overdue installments: {str(exc)}")
        raise  #raise the exception for Django-Q2's retry mechanism


#Define task to cleanup old logs 
def cleanup_audit_logs():
    '''Quarterly task to delete audit logs older than 3 months.'''

    try:
        with transaction.atomic():
            #Calculate the cutoff date (3 months ago)
            three_months_ago = timezone.now() - relativedelta(months=3)
            
            #Delete logs older than 3 months 
            deleted_logs = AuditLog.objects.filter(createdAt__lt=three_months_ago).delete()

            #Log task results
            logger.info(f"Audit Logs cleanup successful. Deleted {deleted_logs[0]} audit logs.")
            
    except Exception as exc:
        logger.error(f"Error cleaning up audit logs: {str(exc)}")
        raise  #raise the exception for Django-Q2's retry mechanism

