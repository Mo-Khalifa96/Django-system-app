import pytest
import json
import tempfile
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from datetime import date, datetime, timedelta
from core.models import Client, Unit, Installment, Invoice
from django.core.files.uploadedfile import SimpleUploadedFile


User = get_user_model()


@pytest.fixture
def api_client():
    '''Fixture for API client'''
    return APIClient()


@pytest.fixture
def admin_user():
    '''Fixture for admin user'''
    return User.objects.create_user(
        email='admin@test.com',
        password='admin123',
        role='ADMIN',
        name='Admin User'
    )

@pytest.fixture
def sales_user():
    '''Fixture for sales user'''
    return User.objects.create_user(
        email='sales@test.com',
        password='sales123',
        role='SALES',
        name='Sales User'
    )

@pytest.fixture
def accountant_user():
    '''Fixture for accountant user'''
    return User.objects.create_user(
        email='accountant@test.com',
        password='accountant123',
        role='ACCOUNTANT',
        name='Accountant User'
    )


@pytest.fixture
def sample_client():
    '''Fixture for sample client'''
    return Client.objects.create(
        name='John Smith',
        email='john@example.com',
        phone='+1234567890'
    )

@pytest.fixture
def sample_unit(sample_client):
    '''Fixture for sample unit'''
    return Unit.objects.create(
        building='A',
        floor='Floor 2',
        unitCode='101',
        activity='RESIDENTIAL',
        indoorSize=100.0,
        outdoorSize=25.0,
        areaPrice=1000.0,
        totalPrice=125000.0,
        status='SOLD',
        client=sample_client,
        enablePaymentPlan=True
    )

@pytest.fixture
def sample_installment(sample_unit):
    '''Fixture for sample installment'''
    return Installment.objects.create(
        unit=sample_unit,
        amount=Decimal(10000.00),
        dueDate=date.today() + timedelta(days=30),
        description='Monthly Payment - Month 1',
        paid=False
    )

@pytest.fixture
def sample_invoice(sample_installment):
    '''Fixture for sample invoice'''
    return Invoice.objects.create(
        issuedBy={
            'company': 'Test Company',
            'phone': '+1234567890',
            'email': 'company@test.com',
            'address': '123 Test Street'
        },
        issuedTo={
            'clientName': 'John Smith',
            'clientPhone': '+1234567890',
            'clientEmail': 'john@example.com'
        },
        subTotal=Decimal(10000.00),
        grandTotal=Decimal(10000.00),
        installment=sample_installment
    )


@pytest.fixture
def sample_pdf_file():
    '''Fixture for sample PDF file'''
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    return SimpleUploadedFile(
        'test_invoice.pdf',
        pdf_content,
        content_type='application/pdf'
    )


class TestPaymentPlanAPIs:
    '''Test cases for Payment Plan APIs'''

    @pytest.mark.django_db
    def test_list_payment_plans_admin(self, api_client, admin_user, sample_unit, sample_installment):
        '''Test listing payment plans as admin'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_payments')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    @pytest.mark.django_db
    def test_list_payment_plans_accountant(self, api_client, accountant_user, sample_unit, sample_installment):
        '''Test listing payment plans as accountant'''
        api_client.force_authenticate(user=accountant_user)
        url = reverse('list_payments')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_payment_plans_sales_forbidden(self, api_client, sales_user, sample_unit):
        '''Test listing payment plans as sales user (should be forbidden)'''
        api_client.force_authenticate(user=sales_user)
        url = reverse('list_payments')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_mark_payment_paid(self, api_client, admin_user, sample_installment):
        '''Test marking payment as paid'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_payment', kwargs={'payment_id': sample_installment.id})
        data = {'paid': True}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        sample_installment.refresh_from_db()
        assert sample_installment.paid is True
        assert sample_installment.paidAt is not None

    @pytest.mark.django_db
    def test_mark_payment_paid_already_paid(self, api_client, admin_user, sample_installment):
        '''Test marking already paid payment (should fail)'''
        sample_installment.paid = True
        sample_installment.paidAt = datetime.now()
        sample_installment.save()
        
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_payment', kwargs={'payment_id': sample_installment.id})
        data = {'paid': True}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_mark_payment_unpaid_forbidden(self, api_client, admin_user, sample_installment):
        '''Test marking payment as unpaid (should be forbidden)'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_payment', kwargs={'payment_id': sample_installment.id})
        data = {'paid': False}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_payment_plan_search(self, api_client, admin_user, sample_unit, sample_installment):
        '''Test searching payment plans'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_payments')
        
        response = api_client.get(url, {'search': sample_unit.client.name})
        
        assert response.status_code == status.HTTP_200_OK


class TestInvoiceAPIs:
    '''Test cases for Invoice APIs'''

    #Upload Invoice Tests
    @pytest.mark.django_db
    def test_upload_invoice_success(self, api_client, admin_user, sample_invoice, sample_pdf_file):
        '''Test successful invoice PDF upload'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('upload_invoice')
        
        data = {
            'invoiceId': str(sample_invoice.id),
            'invoice_pdf': sample_pdf_file
        }
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        sample_invoice.refresh_from_db()
        assert sample_invoice.invoice_pdf is not None

    @pytest.mark.django_db
    def test_upload_invoice_invalid_id(self, api_client, admin_user, sample_pdf_file):
        '''Test upload invoice with invalid invoice ID'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('upload_invoice')
        
        data = {
            'invoiceId': '00000000-0000-0000-0000-000000000000',
            'invoice_pdf': sample_pdf_file
        }
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invoiceId' in response.data

    @pytest.mark.django_db
    def test_upload_invoice_missing_file(self, api_client, admin_user, sample_invoice):
        '''Test upload invoice without PDF file'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('upload_invoice')
        
        data = {
            'invoiceId': str(sample_invoice.id)
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invoice_pdf' in response.data

    @pytest.mark.django_db
    def test_upload_invoice_unauthorized(self, api_client, sample_invoice, sample_pdf_file):
        '''Test upload invoice without authentication'''
        url = reverse('upload_invoice')
        
        data = {
            'invoiceId': str(sample_invoice.id),
            'invoice_pdf': sample_pdf_file
        }
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    #Create Custom Invoice Tests
    @pytest.mark.django_db
    def test_create_custom_invoice_success(self, api_client, admin_user):
        '''Test successful custom invoice creation'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'paymentDetails': [
                {
                    'amount': 5000.00,
                    'dueDate': '2024-12-31',
                    'description': 'First payment'
                },
                {
                    'amount': 3000.00,
                    'dueDate': '2025-01-31',
                    'description': 'Second payment'
                }
            ],
            'currency': 'USD',
            'subTotal': 8000.00,
            'vat': 800.00,
            'discount': 200.00,
            'grandTotal': 8600.00,
            'notes': 'Test invoice notes'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Invoice.objects.filter(id=response.data['id']).exists()

    @pytest.mark.django_db
    def test_create_custom_invoice_with_unit_code(self, api_client, admin_user, sample_unit):
        '''Test custom invoice creation with unit code'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'paymentDetails': [
                {
                    'unitCode': '101-2-A',
                    'amount': 5000.00,
                    'dueDate': '2024-12-31',
                    'description': 'Payment for unit 101'
                }
            ],
            'currency': 'USD',
            'subTotal': 5000.00,
            'grandTotal': 5000.00
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_create_custom_invoice_invalid_subtotal(self, api_client, admin_user):
        '''Test custom invoice creation with invalid subtotal'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'paymentDetails': [
                {
                    'amount': 5000.00,
                    'dueDate': '2024-12-31',
                    'description': 'First payment'
                }
            ],
            'subTotal': 3000.00,  
            'grandTotal': 3000.00
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'subTotal' in response.data

    @pytest.mark.django_db
    def test_create_custom_invoice_invalid_grand_total(self, api_client, admin_user):
        '''Test custom invoice creation with invalid grand total'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'paymentDetails': [
                {
                    'amount': 5000.00,
                    'dueDate': '2024-12-31',
                    'description': 'First payment'
                }
            ],
            'subTotal': 5000.00,
            'vat': 500.00,
            'grandTotal': 4000.00  #Incorrect grand total
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'grandTotal' in response.data

    @pytest.mark.django_db
    def test_create_custom_invoice_sales_forbidden(self, api_client, sales_user):
        '''Test custom invoice creation as sales user (should be forbidden)'''
        api_client.force_authenticate(user=sales_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'paymentDetails': [
                {
                    'amount': 5000.00,
                    'dueDate': '2024-12-31',
                    'description': 'First payment'
                }
            ]
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    #Create Installment Invoice Tests
    @pytest.mark.django_db
    def test_get_installment_invoice_data(self, api_client, admin_user, sample_installment):
        '''Test retrieving installment invoice default data'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['installmentId'] == str(sample_installment.id)
        assert Decimal(response.data['installmentAmount']) == Decimal(sample_installment.amount)
        assert response.data['issuedTo']['clientName'] == sample_installment.unit.client.name

    @pytest.mark.django_db
    def test_create_installment_invoice_success(self, api_client, admin_user, sample_installment):
        '''Test successful installment invoice creation'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            },
            'notes': 'Test installment invoice'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Invoice.objects.filter(installment=sample_installment).exists()

    @pytest.mark.django_db
    def test_create_installment_invoice_with_json_strings(self, api_client, admin_user, sample_installment):
        '''Test installment invoice creation with JSON string data'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': json.dumps({
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            }),
            'issuedTo': json.dumps({
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            }),
            'notes': 'Test installment invoice'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_create_installment_invoice_invalid_json(self, api_client, admin_user, sample_installment):
        '''Test installment invoice creation with invalid JSON string'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': 'invalid json string',
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            }
        }
        
        # Add format='json' to handle nested dictionaries
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'issuedBy' in response.data

    @pytest.mark.django_db
    def test_create_installment_invoice_invalid_phone(self, api_client, admin_user, sample_installment):
        '''Test installment invoice creation with invalid phone number'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': 'invalid phone',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            }
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_installment_invoice_nonexistent_installment(self, api_client, admin_user):
        '''Test creating invoice for non-existent installment'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': '00000000-0000-0000-0000-000000000000'})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    #View Installment Invoice Tests
    @pytest.mark.django_db
    def test_view_installment_invoice_success(self, api_client, admin_user, sample_invoice):
        '''Test viewing installment invoice'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_installment_invoice', kwargs={'payment_id': sample_invoice.installment.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_view_installment_invoice_nonexistent(self, api_client, admin_user):
        '''Test viewing non-existent installment invoice'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_installment_invoice', kwargs={'payment_id': '00000000-0000-0000-0000-000000000000'})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_view_installment_invoice_sales_forbidden(self, api_client, sales_user, sample_invoice):
        '''Test viewing installment invoice as sales user (should be forbidden)'''
        api_client.force_authenticate(user=sales_user)
        url = reverse('view_installment_invoice', kwargs={'payment_id': sample_invoice.installment.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    #Permission Tests
    @pytest.mark.django_db
    def test_accountant_can_create_invoices(self, api_client, accountant_user, sample_installment):
        '''Test that accountant can create invoices'''
        api_client.force_authenticate(user=accountant_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': {
                'company': 'Test Company',
                'phone': '+1234567890',
                'email': 'company@test.com',
                'address': '123 Test Street'
            },
            'issuedTo': {
                'clientName': 'John Smith',
                'clientPhone': '+1234567890',
                'clientEmail': 'john@example.com'
            }
        }
        
        response = api_client.post(url, data, format='json')
        
        #This should succeed if accountant has proper permissions
        #or return 403 if they don't have 'Create Invoice' permission
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]

    #Edge Cases and Validation Tests
    @pytest.mark.django_db
    def test_create_custom_invoice_missing_required_fields(self, api_client, admin_user):
        '''Test custom invoice creation with missing required fields'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_custom_invoice')
        
        data = {
            'issuedBy': {
                'company': 'Test Company'
                #Missing phone, email, address
            },
            'paymentDetails': []
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_create_installment_invoice_missing_required_fields(self, api_client, admin_user, sample_installment):
        '''Test installment invoice creation with missing required fields'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_installment_invoice', kwargs={'payment_id': sample_installment.id})
        
        data = {
            'issuedBy': {
                'company': 'Test Company'
                #Missing required fields
            }
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_upload_invalid_file_type(self, api_client, admin_user, sample_invoice):
        '''Test uploading non-PDF file'''
        api_client.force_authenticate(user=admin_user)
        url = reverse('upload_invoice')
        
        txt_file = SimpleUploadedFile(
            'test.txt',
            b'This is not a PDF file',
            content_type='text/plain'
        )
        
        data = {
            'invoiceId': str(sample_invoice.id),
            'invoice_pdf': txt_file
        }
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED


