import pytest
from django.urls import reverse
from rest_framework import status
from datetime import date, timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Client, Unit, Installment


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


class TestClientAPIs:
    """Test cases for Client APIs"""

    @pytest.mark.django_db
    def test_list_clients_authenticated(self, api_client, admin_user, sample_client):
        """Test listing clients with authentication"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_clients')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['name'] == sample_client.name

    @pytest.mark.django_db
    def test_list_clients_unauthenticated(self, api_client):
        """Test listing clients without authentication"""
        url = reverse('list_clients')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_list_clients_search(self, api_client, admin_user, sample_client):
        """Test searching clients by name"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_clients')
        
        response = api_client.get(url, {'search': 'John'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert 'John' in response.data['results'][0]['name']

    @pytest.mark.django_db
    def test_create_client_valid_data(self, api_client, admin_user):
        """Test creating client with valid data"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_client')
        data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'phone': '+1987654321'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == data['name']
        assert Client.objects.filter(name='Jane Smith').exists()

    @pytest.mark.django_db
    def test_create_client_invalid_data(self, api_client, admin_user):
        """Test creating client with invalid email"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_client')
        data = {
            'name': 'Invalid User',
            'email': 'invalid-email',
            'phone': '+1987654321'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_retrieve_client(self, api_client, admin_user, sample_client):
        """Test retrieving specific client"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_client', kwargs={'id': sample_client.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == sample_client.name
        assert 'clientUnits' in response.data
        assert 'financialSummary' in response.data  # Admin sees financial data

    @pytest.mark.django_db
    def test_retrieve_client_non_admin(self, api_client, sales_user, sample_client):
        """Test retrieving client as non-admin (no financial summary)"""
        api_client.force_authenticate(user=sales_user)
        url = reverse('view_client', kwargs={'id': sample_client.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == sample_client.name
        assert 'clientUnits' in response.data
        assert 'financialSummary' not in response.data  # Non-admin doesn't see financial data

    @pytest.mark.django_db
    def test_update_client(self, api_client, admin_user, sample_client):
        """Test updating client information"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('update_client', kwargs={'id': sample_client.id})
        data = {
            'name': 'John Updated',
            'email': 'john.updated@example.com',
            'phone': '+1111111111'
        }
        
        response = api_client.put(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        sample_client.refresh_from_db()
        assert sample_client.name == 'John Updated'

    @pytest.mark.django_db
    def test_delete_client(self, api_client, admin_user, sample_client):
        """Test deleting client"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('delete_client', kwargs={'id': sample_client.id})
        
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Client.objects.filter(id=sample_client.id).exists()

    @pytest.mark.django_db
    def test_client_payment_status(self, api_client, admin_user, sample_client, sample_unit, sample_installment):
        """Test client payment status calculation"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_clients')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        client_data = next(c for c in response.data['results'] if c['id'] == str(sample_client.id))
        assert client_data['paymentStatus'] in ['PAID', 'PENDING', 'OVERDUE']
