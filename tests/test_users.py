import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

#Get user model 
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



@pytest.mark.django_db
class TestUpdateUserAPIView:
    def test_admin_can_update_user_with_role_and_permissions(self, api_client, admin_user, sales_user):
        """Admin should be able to update role, permissions, and password of another user."""
        api_client.force_authenticate(user=admin_user)
        
        url = reverse("update_user", kwargs={"id": sales_user.id})
        payload = {
            "name": "Updated Sales",
            "email": "updated_sales@test.com",
            "role": "ACCOUNTANT",  # Admin can change role
            "password": "newpassword123",
            "permissions": [
                {"permission": "View Users Data Table", "enabled": True},
                {"permission": "Update User", "enabled": True},
                {"permission": "Delete User", "enabled": False},
            ]
        }

        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        sales_user.refresh_from_db()
        assert sales_user.name == "Updated Sales"
        assert sales_user.email == "updated_sales@test.com"
        assert sales_user.role == "ACCOUNTANT"
        assert check_password("newpassword123", sales_user.password)
        assert "Update User" in sales_user.userPermissions
        assert "Delete User" not in sales_user.userPermissions


    def test_non_admin_cannot_update_user_details(self, api_client, sales_user, accountant_user):
        """Non-admin should NOT see or be able to update their details."""
        api_client.force_authenticate(user=sales_user)

        url = reverse("update_user", kwargs={"id": accountant_user.id})
        payload = {
            "name": "Updated Accountant",
            "role": "ADMIN",  
            "permissions": [
                {"permission": "Update User", "enabled": False},
                {"permission": "Delete User", "enabled": True},
            ],
        }

        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN



    def test_password_update_hashes_properly(self, api_client, admin_user, sales_user):
        """Ensure password updates are hashed and not stored raw."""
        api_client.force_authenticate(user=admin_user)

        url = reverse("update_user", kwargs={"id": sales_user.id})
        payload = {"password": "strongpass123"}

        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        sales_user.refresh_from_db()
        assert check_password("strongpass123", sales_user.password)


    def test_permission_enforcement_blocks_non_privileged_user(self, api_client, sales_user, accountant_user):
        """Sales should get 403 if they try to delete another user (because they lack 'Delete Unit')."""
        api_client.force_authenticate(user=sales_user)

        url = reverse("delete_user", kwargs={"id": accountant_user.id})

        response = api_client.patch(url, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
