import os
import sys
import random
import django
from faker import Faker
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

#Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

#Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SystemApp.settings.dev')
django.setup()

from django.db import transaction
from django.utils import timezone
from core.models import Client, Unit, InstallmentConfiguration, Installment

#Instantiate faker
fake = Faker()


#Custom functions for data seeding
#Seed function for clients
def seed_clients(num_clients=50):
    '''Create fake clients'''
    
    clients = []
    for _ in range(num_clients):
        client = Client(
            name=fake.company(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],  #ensure it fits the max_length
        )
        clients.append(client)
    
    Client.objects.bulk_create(clients)
    return Client.objects.all()


#Seed function for units 
def seed_units(clients, num_units=100):
    '''Create fake units with proper relationships to clients and payment plan dependencies'''
    
    #Building codes for variety
    buildings = [f'B{i:03d}' for i in range(1, 21)]  #20 different buildings
    
    units = []
    units_needing_payment_plans = []  #track units that will need payment plans
    
    for i in range(num_units):
        #Generate unit code
        unit_code = f'U{fake.unique.random_int(min=1000, max=9999)}'
        
        #Determine if this unit will be available (40% chance) or have a client
        if random.random() < 0.4:
            status = Unit.UnitStatusChoices.AVAILABLE
            client = None
            enable_payment_plan = False
        else:
            #Non-available units must have clients
            status = random.choice([
                Unit.UnitStatusChoices.SOLD,
                Unit.UnitStatusChoices.RESERVED,
                Unit.UnitStatusChoices.HOLD,
                Unit.UnitStatusChoices.PENDING
            ])
            client = random.choice(clients)
            
            #For units with clients, ensure at least 70% have payment plans enabled
            enable_payment_plan = random.random() < 0.6
        
        #Generate realistic sizes and prices
        indoor_size = round(random.uniform(50, 300), 2)
        outdoor_size = round(random.uniform(0, 100), 2) if random.random() < 0.7 else None
        area_price = Decimal(str(round(random.uniform(1000, 5000), 2)))
        total_price = Decimal(str(round(indoor_size * float(area_price), 2)))
        
        #Contract type if client exists
        contract_type = None
        if client:
            contract_type = random.choice([
                'Purchase Agreement',
                'Lease Agreement', 
                'Installment Contract',
                'Cash Sale'
            ])
        
        #Hold deposit and expiry for HOLD status
        hold_deposit = None
        hold_expiry = None
        if status == Unit.UnitStatusChoices.HOLD:
            hold_deposit = Decimal(str(round(float(total_price) * 0.1, 2)))  #10% of total
            hold_expiry = fake.date_between(start_date='+1d', end_date='+90d')
        
        unit = Unit(
            unitCode=unit_code,
            status=status,
            building=random.choice(buildings),
            floor=random.choice(Unit.FloorChoices.choices)[0],
            activity=random.choice(Unit.UnitActivities.choices)[0],
            indoorSize=indoor_size,
            outdoorSize=outdoor_size,
            areaPrice=area_price,
            totalPrice=total_price,
            client=client,
            contractType=contract_type,
            enablePaymentPlan=enable_payment_plan,
            holdDeposit=hold_deposit,
            holdExpiryDate=hold_expiry,
            isApproved=random.choice([True, False]),
            requestedStatus=random.choice(Unit.UnitStatusChoices.choices)[0],
            notes=fake.text(max_nb_chars=200) if random.random() < 0.3 else None,
            updatedBy=fake.name() if random.random() < 0.5 else None
        )
        units.append(unit)
        
        #Track units that need payment plans
        if enable_payment_plan and client:
            units_needing_payment_plans.append(unit)
    
    Unit.objects.bulk_create(units)
    return Unit.objects.all(), units_needing_payment_plans


#Seed function for installments configurations 
def seed_installment_configurations(units_with_payment_plans, max_configs_per_unit=3):
    '''Create installment configurations for units with payment plans enabled'''
    
    configurations = []
    units_with_configs = []  #track which units actually get configurations
    
    for unit in units_with_payment_plans:
        #Create 1-3 configurations per unit that has payment plans enabled
        num_configs = random.randint(1, max_configs_per_unit)
        unit_has_configs = False
        
        for _ in range(num_configs):
            config = InstallmentConfiguration(
                unit=unit,
                every=random.randint(1, 6),  #Every 1-6 months
                startingMonth=random.randint(1, 12),
                repetitions=random.randint(6, 60),  #6 months to 5 years
                amount=Decimal(str(round(random.uniform(1000, 10000), 2))),
                startDate=fake.date_between(start_date='-30d', end_date='+30d'),
                description=fake.sentence(nb_words=6)
            )
            configurations.append(config)
            unit_has_configs = True
        
        if unit_has_configs:
            units_with_configs.append(unit)
    
    InstallmentConfiguration.objects.bulk_create(configurations)
    return configurations, units_with_configs


#Seed function for payment plans 
def seed_payment_plans(units_with_configs, payments_per_unit_range=(5, 20)):
    '''Create payment plans for units that have installment configurations'''
    
    payments = []
    for unit in units_with_configs:
        #create payment plans for units that have both clients AND configurations
        if not unit.client:
            continue
            
        num_installments = random.randint(*payments_per_unit_range)
        
        #Create a mix of payment types
        total_amount = float(unit.totalPrice)
        remaining_amount = total_amount
        
        for i in range(num_installments):
            #Determine payment type
            if i == 0:
                amount = round(total_amount * random.uniform(0.1, 0.3), 2)  #10-30% down payment
            elif i == num_installments - 1 and remaining_amount > 0:
                amount = round(remaining_amount, 2)  #Final payment
            else:
                max_amount = min(remaining_amount, total_amount * 0.2)  #Max 20% per installment
                amount = round(random.uniform(1000, max_amount), 2) if max_amount > 1000 else round(remaining_amount, 2)
            
            remaining_amount -= amount
            if remaining_amount < 0:
                remaining_amount = 0
            
            #Generate due date
            due_date = fake.date_between(
                start_date='-180d' if i == 0 else '+1d',
                end_date='+365d'
            )
            
            #Determine if payment is paid (past payments more likely to be paid)
            is_paid = False
            paid_at = None
            status = Installment.PaymentStatusChoices.PENDING
            
            if due_date < datetime.now().date():
                #Past due dates
                if random.random() < 0.8:  #80% chance of being paid
                    is_paid = True
                    paid_at = fake.date_time_between(
                        start_date=due_date,
                        end_date=min(due_date + timedelta(days=30), datetime.now().date())
                    )
                    status = Installment.PaymentStatusChoices.PAID
                else:
                    status = Installment.PaymentStatusChoices.OVERDUE
            elif due_date <= datetime.now().date() + timedelta(days=7):
                #Due soon
                if random.random() < 0.3:  #30% chance of early payment
                    is_paid = True
                    paid_at = timezone.now()
                    status = Installment.PaymentStatusChoices.PAID
            
            payment = Installment(
                unit=unit,
                amount=Decimal(str(amount)),
                dueDate=due_date,
                paid=is_paid,
                paidAt=paid_at,
                status=status,
                description=f'Installment for {unit.unitCode}'
            )
            payments.append(payment)
    
    Installment.objects.bulk_create(payments)
    return payments


#Main seeding function
@transaction.atomic 
def run_seed(num_clients=50, num_units=200):
    '''Run the complete seeding process with proper dependency management'''
    print('Starting data seeding process...\n')
    
    #Clear existing data (optional - if you want to start fresh)
    print('Clearing existing data...')
    Installment.objects.all().delete()
    InstallmentConfiguration.objects.all().delete()
    Unit.objects.all().delete()
    Client.objects.all().delete()
    
    #Seed data in dependency order with proper relationship management
    clients = seed_clients(num_clients)
    units, units_with_payment_plans = seed_units(clients, num_units)
    configurations, units_with_configs = seed_installment_configurations(units_with_payment_plans)
    payments = seed_payment_plans(units_with_configs)
    
    print('\n', '='*45, '\n')
    print('Seeding completed successfully!')
    print(f'Summary:')
    print(f'- Clients: {Client.objects.count()}')
    print(f'- Units: {Unit.objects.count()}')
    print(f'- Units with payment plans enabled: {Unit.objects.filter(enablePaymentPlan=True).count()}')
    print(f'- Units with clients: {Unit.objects.filter(client__isnull=False).count()}')
    print(f'- Installment Configurations: {InstallmentConfiguration.objects.count()}')
    print(f'- Payment Plans: {Installment.objects.count()}')
    print('\n', '='*45, '\n')
    

#Execute script 
if __name__ == '__main__':
    while True:
        try:
            run_seed(num_clients=50, num_units=200)
            break 
        except Exception as exc:
            print(f"\nError seedings: {exc}.\n\nTrying seeding again...")
            print('\n', '='*45, '\n')
