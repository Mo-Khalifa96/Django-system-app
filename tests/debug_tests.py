import pytest
import json
import os
import django
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

# Ensure Django is configured
if not django.conf.settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SystemApp.settings.dev')
    django.setup()

from core.models import Client, Unit, Installment, InstallmentConfiguration

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


class TestDebugUnitCreation:
    """Debug tests to identify unit creation issues"""

    @pytest.mark.django_db
    def test_debug_unit_creation_available(self, api_client, admin_user):
        """Debug unit creation with minimal data"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        
        # First, let's see what the GET endpoint returns (choices/form data)
        get_response = api_client.get(url)
        print(f"\nGET /units/new/ response:")
        print(f"Status: {get_response.status_code}")
        print(f"Data: {get_response.data}")
        
        # Test with minimal required data
        minimal_data = {
            'building': 'TEST',
            'floor': '1',
            'unitCode': '001',
            'activity': 'RESIDENTIAL',
            'status': 'AVAILABLE'
        }
        
        response = api_client.post(url, minimal_data, format='json')
        print(f"\nPOST /units/new/ with minimal data:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.data}")
        
        if response.status_code != 201:
            # Try with more complete data
            complete_data = {
                'building': 'TEST',
                'floor': '1',
                'unitCode': '002',
                'activity': 'RESIDENTIAL',
                'status': 'AVAILABLE',
                'indoorSize': 100.0,
                'outdoorSize': 25.0,
                'areaPrice': 1000.0,
                'totalPrice': 125000.0,
                'enablePaymentPlan': False
            }
            
            response2 = api_client.post(url, complete_data, format='json')
            print(f"\nPOST /units/new/ with complete data:")
            print(f"Status: {response2.status_code}")
            print(f"Response: {response2.data}")
            
    @pytest.mark.django_db
    def test_debug_unit_creation_sold(self, api_client, admin_user):
        """Debug unit creation with sold status"""
        api_client.force_authenticate(user=admin_user)
        url = reverse('create_unit')
        
        # Create a simple contract file
        contract_file = SimpleUploadedFile(
            "test_contract.pdf",
            b"test content",
            content_type="application/pdf"
        )
        
        # Test sold unit with new client
        data = {
            'building': 'SOLD',
            'floor': '1',
            'unitCode': '001',
            'activity': 'RESIDENTIAL', 
            'status': 'SOLD',
            'indoorSize': 100.0,
            'totalPrice': 125000.0,
            'enablePaymentPlan': False,
            'newClient': json.dumps({
                'name': 'Test Client',
                'email': 'test@example.com',
                'phone': '+1234567890'
            }),
            'contract': contract_file
        }
        
        response = api_client.post(url, data, format='multipart')
        print(f"\nPOST sold unit:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.data}")
        
        if response.status_code == 400:
            print("Validation errors detected. Trying without contract...")
            
            # Remove contract and try again
            data_no_contract = data.copy()
            data_no_contract.pop('contract')
            
            response2 = api_client.post(url, data_no_contract, format='json')
            print(f"\nPOST sold unit without contract:")
            print(f"Status: {response2.status_code}")
            print(f"Response: {response2.data}")


# Run this specific test to debug:
# pytest tests/debug_tests.py::TestDebugUnitCreation::test_debug_unit_creation_available -v -s