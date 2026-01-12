"""
Free Fire Diamond Top-Up Platform - Backend API Tests
Tests: Authentication, Packages, Admin Dashboard, Admin CRUD operations
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://garena-credits.preview.emergentagent.com').rstrip('/')

class TestUserAuthentication:
    """User authentication endpoint tests"""
    
    def test_user_login_success(self):
        """Test user login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "identifier": "testclient",
            "password": "test123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user_type"] == "user"
        assert data["username"] == "testclient"
        assert data["wallet_balance"] == 50.0
    
    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "identifier": "testclient",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


class TestAdminAuthentication:
    """Admin authentication endpoint tests"""
    
    def test_admin_login_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user_type"] == "admin"
        assert data["username"] == "admin"
    
    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestPackagesAPI:
    """Package listing endpoint tests"""
    
    def test_list_packages_returns_all_products(self):
        """Test that packages list returns all 12 products"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        assert response.status_code == 200
        packages = response.json()
        assert isinstance(packages, list)
        assert len(packages) >= 12  # Should have at least 12 products
        
        # Verify package structure
        for pkg in packages:
            assert "id" in pkg
            assert "name" in pkg
            assert "type" in pkg
            assert "amount" in pkg
            assert "price" in pkg
            assert "active" in pkg
    
    def test_packages_include_diamond_types(self):
        """Test that packages include diamond packages"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        diamond_packages = [p for p in packages if p["type"] == "diamond"]
        assert len(diamond_packages) >= 7  # 25, 50, 115, 240, 610, 1240, 2530
    
    def test_packages_include_membership_types(self):
        """Test that packages include membership packages"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        membership_packages = [p for p in packages if p["type"] == "membership"]
        assert len(membership_packages) >= 2  # Weekly, Monthly
    
    def test_packages_include_evo_access_types(self):
        """Test that packages include evo access packages"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        evo_packages = [p for p in packages if p["type"] == "evo_access"]
        assert len(evo_packages) >= 3  # 3D, 7D, 30D


class TestAdminDashboard:
    """Admin dashboard endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_admin_dashboard_returns_stats(self, admin_token):
        """Test admin dashboard returns correct stats structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify dashboard stats structure
        assert "total_sales" in data
        assert "total_orders" in data
        assert "success_orders" in data
        assert "failed_orders" in data
        assert "suspicious_orders" in data
        assert "duplicate_orders" in data
        assert "pending_orders" in data
        assert "total_wallet_balance" in data
    
    def test_admin_dashboard_requires_auth(self):
        """Test admin dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code in [401, 403]


class TestAdminPackagesManagement:
    """Admin packages CRUD endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_admin_list_packages(self, admin_token):
        """Test admin can list all packages"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/packages", headers=headers)
        assert response.status_code == 200
        packages = response.json()
        assert isinstance(packages, list)
        assert len(packages) >= 12
    
    def test_admin_update_package_price(self, admin_token):
        """Test admin can update package price"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get first package
        response = requests.get(f"{BASE_URL}/api/admin/packages", headers=headers)
        packages = response.json()
        first_package = packages[0]
        original_price = first_package["price"]
        
        # Update price
        new_price = original_price + 0.01
        response = requests.put(
            f"{BASE_URL}/api/admin/packages/{first_package['id']}", 
            headers=headers,
            json={"price": new_price}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/admin/packages", headers=headers)
        updated_packages = response.json()
        updated_package = next(p for p in updated_packages if p["id"] == first_package["id"])
        assert updated_package["price"] == new_price
        
        # Restore original price
        requests.put(
            f"{BASE_URL}/api/admin/packages/{first_package['id']}", 
            headers=headers,
            json={"price": original_price}
        )


class TestAdminGarenaAccounts:
    """Admin Garena accounts management tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_admin_list_garena_accounts(self, admin_token):
        """Test admin can list Garena accounts with hidden credentials"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/garena-accounts", headers=headers)
        assert response.status_code == 200
        accounts = response.json()
        assert isinstance(accounts, list)
        
        # Verify credentials are hidden
        for account in accounts:
            assert account["password"] == "***hidden***"
            assert account["pin"] == "***hidden***"


class TestAdminUsersManagement:
    """Admin users management tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    def test_admin_list_users(self, admin_token):
        """Test admin can list all users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        
        # Verify testclient user exists
        testclient = next((u for u in users if u["username"] == "testclient"), None)
        assert testclient is not None
        assert testclient["wallet_balance"] == 50.0
    
    def test_admin_block_unblock_user(self, admin_token):
        """Test admin can block and unblock a user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get testclient user
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        users = response.json()
        testclient = next((u for u in users if u["username"] == "testclient"), None)
        assert testclient is not None
        
        original_blocked = testclient.get("blocked", False)
        
        # Block user
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{testclient['id']}", 
            headers=headers,
            json={"blocked": True}
        )
        assert response.status_code == 200
        
        # Verify blocked
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        users = response.json()
        testclient = next((u for u in users if u["username"] == "testclient"), None)
        assert testclient["blocked"] == True
        
        # Unblock user
        response = requests.put(
            f"{BASE_URL}/api/admin/users/{testclient['id']}", 
            headers=headers,
            json={"blocked": False}
        )
        assert response.status_code == 200
        
        # Verify unblocked
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        users = response.json()
        testclient = next((u for u in users if u["username"] == "testclient"), None)
        assert testclient["blocked"] == False


class TestUserProfile:
    """User profile endpoint tests"""
    
    @pytest.fixture
    def user_token(self):
        """Get user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "identifier": "testclient",
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("User authentication failed")
    
    def test_user_profile_returns_wallet_balance(self, user_token):
        """Test user profile returns correct wallet balance"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "wallet_balance" in data
        assert data["wallet_balance"] == 50.0
        assert data["username"] == "testclient"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
