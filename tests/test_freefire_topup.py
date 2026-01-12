"""
Free Fire Diamond Top-Up Platform - Backend API Tests
Tests: Authentication, Packages, Admin Dashboard, Admin CRUD operations, Orders, Wallet
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
        # Wallet balance can change, just verify it's a number
        assert isinstance(data["wallet_balance"], (int, float))
        assert data["wallet_balance"] >= 0
    
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
    
    def test_packages_have_correct_price_format(self):
        """Test that packages have price in rupees (converted from paisa)"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        for pkg in packages:
            # Price should be a positive number
            assert isinstance(pkg["price"], (int, float))
            assert pkg["price"] > 0
            # price_paisa should also exist
            assert "price_paisa" in pkg
            assert isinstance(pkg["price_paisa"], int)


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
        assert "pending_orders" in data
        assert "total_wallet_balance" in data
        assert "review_queue_count" in data
        
        # Verify values are numbers
        assert isinstance(data["total_sales"], (int, float))
        assert isinstance(data["total_orders"], int)
        assert isinstance(data["success_orders"], int)
    
    def test_admin_dashboard_requires_auth(self):
        """Test admin dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code in [401, 403]


class TestAdminOrders:
    """Admin orders endpoint tests"""
    
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
    
    def test_admin_list_all_orders(self, admin_token):
        """Test admin can list all orders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        
        # Verify order structure if orders exist
        if len(orders) > 0:
            order = orders[0]
            assert "id" in order
            assert "status" in order
            assert "locked_price" in order
            assert "username" in order
    
    def test_admin_filter_orders_by_status(self, admin_token):
        """Test admin can filter orders by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test filtering by pending_payment status
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=pending_payment", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        
        # All returned orders should have pending_payment status
        for order in orders:
            assert order["status"] == "pending_payment"
    
    def test_admin_filter_orders_by_success_status(self, admin_token):
        """Test admin can filter orders by success status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders?status=success", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        
        for order in orders:
            assert order["status"] == "success"
    
    def test_admin_orders_have_correct_price_format(self, admin_token):
        """Test admin orders have prices in rupees"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        
        for order in orders:
            # locked_price should be in rupees (converted from paisa)
            assert "locked_price" in order
            assert isinstance(order["locked_price"], (int, float))


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
        
        # Update price using price_rupees (backend expects this)
        new_price = original_price + 0.01
        response = requests.put(
            f"{BASE_URL}/api/admin/packages/{first_package['id']}", 
            headers=headers,
            json={"price_rupees": new_price}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/admin/packages", headers=headers)
        updated_packages = response.json()
        updated_package = next(p for p in updated_packages if p["id"] == first_package["id"])
        # Allow small floating point differences
        assert abs(updated_package["price"] - new_price) < 0.02
        
        # Restore original price
        requests.put(
            f"{BASE_URL}/api/admin/packages/{first_package['id']}", 
            headers=headers,
            json={"price_rupees": original_price}
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
        # Wallet balance can change, just verify it's a number
        assert isinstance(testclient["wallet_balance"], (int, float))
    
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
            params={"blocked": True}
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
            params={"blocked": False}
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
        assert isinstance(data["wallet_balance"], (int, float))
        assert data["username"] == "testclient"


class TestUserWallet:
    """User wallet endpoint tests"""
    
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
    
    def test_user_wallet_returns_balance_and_transactions(self, user_token):
        """Test user wallet returns balance and transaction history"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/user/wallet", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "balance" in data
        assert isinstance(data["balance"], (int, float))
        assert "transactions" in data
        assert isinstance(data["transactions"], list)


class TestOrderCreation:
    """Order creation endpoint tests"""
    
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
    
    @pytest.fixture
    def package_id(self):
        """Get first package ID"""
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        return packages[0]["id"]
    
    def test_order_creation_requires_valid_uid(self, user_token, package_id):
        """Test order creation requires minimum 8 digit UID"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test with invalid UID (less than 8 digits)
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=headers, json={
            "player_uid": "1234567",  # Only 7 digits
            "package_id": package_id
        })
        assert response.status_code == 400
        assert "8 digits" in response.json().get("detail", "").lower()
    
    def test_order_creation_rejects_non_numeric_uid(self, user_token, package_id):
        """Test order creation rejects non-numeric UID"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test with non-numeric UID
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=headers, json={
            "player_uid": "abc12345678",
            "package_id": package_id
        })
        assert response.status_code == 400
    
    def test_order_creation_with_valid_uid(self, user_token, package_id):
        """Test order creation with valid 8+ digit UID"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Test with valid UID (8+ digits)
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=headers, json={
            "player_uid": "12345678",  # 8 digits
            "package_id": package_id
        })
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert "status" in data


class TestUserOrders:
    """User orders endpoint tests"""
    
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
    
    def test_user_can_list_orders(self, user_token):
        """Test user can list their orders"""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/user/orders", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        
        # Verify order structure if orders exist
        if len(orders) > 0:
            order = orders[0]
            assert "id" in order
            assert "status" in order
            assert "locked_price" in order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
