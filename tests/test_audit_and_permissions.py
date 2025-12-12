import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

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


class TestAuditLogAPIs:
    """Test cases for Audit Log API"""
    @pytest.mark.django_db
    def test_list_audit_logs_for_admin(self, api_client, admin_user):
        """Test listing audit logs"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('list_audit_logs')    
        response = api_client.get(url)        
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_list_audit_logs_for_non_admin(self, api_client, accountant_user):
        """Test listing audit logs"""
        api_client.force_authenticate(user=accountant_user)
        url = reverse('list_audit_logs')        
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPermissionEdgeCases:
    """Test permission edge cases and error scenarios"""
    @pytest.mark.django_db
    def test_unauthenticated_access(self, api_client):
        """Test various endpoints without authentication"""
        endpoints = [
            reverse('list_clients'),
            reverse('list_units'),
            reverse('list_payments'),
            reverse('list_pending_units'),
        ]
        
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_invalid_uuid_endpoints(self, api_client, admin_user):
        """Test endpoints with invalid UUID parameters"""
        api_client.force_authenticate(user=admin_user)
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        
        # Test GET endpoints that should return 404
        get_endpoints = [
            reverse('view_client', kwargs={'id': invalid_uuid}),
            reverse('view_unit', kwargs={'id': invalid_uuid}),
        ]
        
        for endpoint in get_endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test PATCH endpoint (payment update) - might return 404 or 405 depending on implementation
        payment_endpoint = reverse('update_payment', kwargs={'payment_id': invalid_uuid})
        response = api_client.patch(payment_endpoint, {'paid': True})
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED]

    @pytest.mark.django_db
    def test_role_based_access_control(self, api_client, sales_user, accountant_user):
        """Test role-based access control"""
        # Sales user trying to access payment plans (should fail)
        api_client.force_authenticate(user=sales_user)
        response = api_client.get(reverse('list_payments'))
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Accountant accessing payment plans (should work)
        api_client.force_authenticate(user=accountant_user)
        response = api_client.get(reverse('list_payments'))
        assert response.status_code == status.HTTP_200_OK