import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Client, Unit


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


class TestApprovalAPIs:
    """Test cases for Approval APIs"""

    @pytest.fixture
    def pending_unit(self, sample_client):
        """Fixture for unit pending approval"""
        return Unit.objects.create(
            building='P',
            floor='Floor 1',
            unitCode='101',
            activity='RESIDENTIAL',
            totalPrice=100000.0,
            status='PENDING',
            requestedStatus='SOLD',
            client=sample_client,
            isApproved=False,
            updatedBy='Sales User (SALES)'
        )

    @pytest.mark.django_db
    def test_list_pending_units_admin(self, api_client, admin_user, pending_unit):
        """Test listing units pending approval as admin"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_pending_units')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        
        unit_data = response.data['results'][0]
        assert unit_data['currentStatus'] == 'PENDING'
        assert unit_data['requestedStatus'] == 'SOLD'

    @pytest.mark.django_db
    def test_list_pending_units_non_admin_forbidden(self, api_client, sales_user, pending_unit):
        """Test listing pending units as non-admin (should be forbidden)"""
        api_client.force_authenticate(user=sales_user)
        url = reverse('list_pending_units')
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_approve_unit(self, api_client, admin_user, pending_unit):
        """Test approving unit changes"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('approve_pending_unit', kwargs={'unit_id': pending_unit.id})
        data = {'isApproved': True}
        
        # Store the requested status before approval
        expected_status = pending_unit.requestedStatus
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        pending_unit.refresh_from_db()
        assert pending_unit.isApproved is True
        # After approval, status should match what was requested
        assert pending_unit.status == expected_status


    @pytest.mark.django_db
    def test_reject_unit(self, api_client, admin_user, pending_unit):
        """Test rejecting unit changes"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('approve_pending_unit', kwargs={'unit_id': pending_unit.id})
        data = {'isApproved': False}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        pending_unit.refresh_from_db()
        assert pending_unit.isApproved is False

    @pytest.mark.django_db
    def test_preview_approve_unit_get(self, api_client, admin_user, pending_unit):
        """Test getting unit details for preview/approval"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_or_approve_pending_unit', kwargs={'unit_id': pending_unit.id})
        
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['currentStatus'] == 'PENDING'
        assert response.data['requestedStatus'] == 'SOLD'

    @pytest.mark.django_db
    def test_preview_approve_unit_patch(self, api_client, admin_user, pending_unit):
        """Test approving unit from preview page"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('view_or_approve_pending_unit', kwargs={'unit_id': pending_unit.id})
        data = {'isApproved': True}
        
        response = api_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        pending_unit.refresh_from_db()
        assert pending_unit.isApproved is True

    @pytest.mark.django_db
    def test_approval_search(self, api_client, admin_user, pending_unit):
        """Test searching pending units"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_pending_units')
        
        response = api_client.get(url, {'search': pending_unit.client.name})
        
        assert response.status_code == status.HTTP_200_OK

