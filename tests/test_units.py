import json
import pytest
from django.urls import reverse
from rest_framework import status
from datetime import date, timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Client, Unit, Installment
from django.core.files.uploadedfile import SimpleUploadedFile


User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture for API client"""
    return APIClient()


@pytest.fixture
def admin_user():
    """Fixture for admin user"""
    return User.objects.create_user(
        email='admin@test.com',
        password='admin123',
        role='ADMIN',
        name='Admin User'
    )

@pytest.fixture
def sales_user():
    """Fixture for sales user"""
    return User.objects.create_user(
        email='sales@test.com',
        password='sales123',
        role='SALES',
        name='Sales User'
    )

@pytest.fixture
def accountant_user():
    """Fixture for accountant user"""
    return User.objects.create_user(
        email='accountant@test.com',
        password='accountant123',
        role='ACCOUNTANT',
        name='Accountant User'
    )


@pytest.fixture
def sample_client():
    """Fixture for sample client"""
    return Client.objects.create(
        name='John Smith',
        email='john@example.com',
        phone='+1234567890'
    )


@pytest.fixture
def sample_unit(sample_client):
    """Fixture for sample unit"""
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
    """Fixture for sample installment"""
    return Installment.objects.create(
        unit=sample_unit,
        amount=10000.0,
        dueDate=date.today() + timedelta(days=30),
        description='Monthly Payment - Month 1',
        paid=False
    )


@pytest.fixture
def contract_file():
    """Fixture for contract file upload"""
    return SimpleUploadedFile(
        "contract.pdf",
        b"file_content",
        content_type="application/pdf"
    )


class TestUnitAPIs:
    """Test cases for Unit APIs"""

    @pytest.mark.django_db
    def test_list_units_admin(self, api_client, admin_user, sample_unit):
        """Test listing units as admin (sees all units)"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_units')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    @pytest.mark.django_db
    def test_list_units_sales(self, api_client, sales_user):
        """Test listing units as sales (only available units)"""
        api_client.force_authenticate(user=sales_user)
        Unit.objects.create(
            building='B',
            floor='Floor 1',
            unitCode='102',
            activity='COMMERCIAL',
            indoorSize=50.0,
            totalPrice=75000.0,
            status='AVAILABLE'
        )
        url = reverse('list_units')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        #Sales user should only see available units
        for unit in response.data['results']:
            assert unit['status'] == 'AVAILABLE'

    @pytest.mark.django_db
    def test_create_unit_get_choices(self, api_client, admin_user):
        """Test getting choices for unit creation form"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'status_choices' in response.data
        assert 'activity_choices' in response.data
        assert 'floor_choices' in response.data

    @pytest.mark.django_db
    def test_create_unit_available_status(self, api_client, admin_user):
        """Test creating unit with available status"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        data = {
            'building': 'C',
            'floor': 'Floor 3',
            'unitCode': '201',
            'activity': 'RESIDENTIAL',
            'indoorSize': 120.0,
            'outdoorSize': 30.0,
            'areaPrice': 1200.0,
            'totalPrice': 180000.0,
            'status': 'AVAILABLE',
            'enablePaymentPlan': False
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['building'] == 'C'

    @pytest.mark.django_db
    def test_create_unit_sold_with_client(self, api_client, admin_user, contract_file):
        """Test creating unit with sold status and new client"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        data = {
            'building': 'D',
            'floor': 'Floor 1',
            'unitCode': '101',
            'activity': 'COMMERCIAL',
            'indoorSize': 80.0,
            'totalPrice': 120000.0,
            'status': 'SOLD',
            'enablePaymentPlan': True,
            'newClient': json.dumps({
                'name': 'New Client',
                'email': 'new@example5.com',
                'phone': '+1234567895'
            }),
            'contract': contract_file,
            'installmentConfig': json.dumps([{
                'every': 1,
                'startingMonth': 1,
                'repetitions': 12,
                'amount': 10000.0,
                'startDate': '01/01/2024',
                'description': 'Monthly Payment'
            }]),
            'paymentSchedule': json.dumps([
                {'month': 1, 'dueDate': '2024-01-02', 'amount': 10000, 'description': 'Monthly Payment - Month 1'},
                {'month': 2, 'dueDate': '2024-02-02', 'amount': 10000, 'description': 'Monthly Payment - Month 2'},
                {'month': 3, 'dueDate': '2024-03-02', 'amount': 10000, 'description': 'Monthly Payment - Month 3'},
                {'month': 4, 'dueDate': '2024-04-02', 'amount': 10000, 'description': 'Monthly Payment - Month 4'},
                {'month': 5, 'dueDate': '2024-05-02', 'amount': 10000, 'description': 'Monthly Payment - Month 5'},
                {'month': 6, 'dueDate': '2024-06-02', 'amount': 10000, 'description': 'Monthly Payment - Month 6'},
                {'month': 7, 'dueDate': '2024-07-02', 'amount': 10000, 'description': 'Monthly Payment - Month 7'},
                {'month': 8, 'dueDate': '2024-08-02', 'amount': 10000, 'description': 'Monthly Payment - Month 8'},
                {'month': 9, 'dueDate': '2024-09-02', 'amount': 10000, 'description': 'Monthly Payment - Month 9'},
                {'month': 10, 'dueDate': '2024-10-02', 'amount': 10000, 'description': 'Monthly Payment - Month 10'},
                {'month': 11, 'dueDate': '2024-11-02', 'amount': 10000, 'description': 'Monthly Payment - Month 11'},
                {'month': 12, 'dueDate': '2024-12-02', 'amount': 10000, 'description': 'Monthly Payment - Month 12'}
            ])
        }
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Client.objects.filter(name='New Client').exists()

    @pytest.mark.django_db
    def test_create_unit_validation_errors(self, api_client, admin_user):
        """Test unit creation validation errors"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        
        #Test sold status without client
        data = {
            'building': 'E',
            'floor': 'Floor 1',
            'unitCode': '101',
            'activity': 'RESIDENTIAL',
            'totalPrice': 100000.0,
            'status': 'SOLD'  #Sold without client should fail
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_retrieve_unit(self, api_client, admin_user, sample_unit):
        """Test retrieving unit details"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_unit', kwargs={'id': sample_unit.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['building'] == sample_unit.building
        assert 'clientDetails' in response.data

    @pytest.mark.django_db
    def test_update_unit_get(self, api_client, admin_user, sample_unit):
        """Test getting unit data for update form"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_unit', kwargs={'id': sample_unit.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['building'] == sample_unit.building

    @pytest.mark.django_db
    def test_update_unit_put(self, api_client, admin_user, sample_unit):
        """Test updating unit information"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_unit', kwargs={'id': sample_unit.id})
        data = {
            'building': 'F',
            'totalPrice': 150000.0,
            'notes': 'Updated notes'
        }
        
        response = api_client.put(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_200_OK
        sample_unit.refresh_from_db()
        assert sample_unit.building == 'F'

    @pytest.mark.django_db
    def test_delete_unit_admin_only(self, api_client, admin_user, sample_unit):
        """Test deleting unit (admin only)"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('delete_unit', kwargs={'id': sample_unit.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Unit.objects.filter(id=sample_unit.id).exists()

    @pytest.mark.django_db
    def test_delete_unit_non_admin_forbidden(self, api_client, sales_user, sample_unit):
        """Test deleting unit as non-admin (should be forbidden)"""
        api_client.force_authenticate(user=sales_user)
        url = reverse('delete_unit', kwargs={'id': sample_unit.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

