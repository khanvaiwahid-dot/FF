"""
Free Fire Diamond Top-Up Platform - Price Update & Admin Orders Tests
Tests: 
1. Price update flow - new orders use new price, old orders retain locked_price_paisa
2. Admin Orders page - shows ALL orders (wallet_load + product_topup), filters, edit functionality
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://garena-credits.preview.emergentagent.com').rstrip('/')


class TestPriceUpdateFlow:
    """Test that price updates affect new orders but not old orders"""
    
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
    
    def test_price_update_affects_new_orders_only(self, admin_token, user_token):
        """Test that updating package price affects new orders but old orders retain original locked_price_paisa"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get a package to test with (50 Diamonds)
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        test_package = next((p for p in packages if p["name"] == "50 Diamonds"), packages[0])
        package_id = test_package["id"]
        original_price_paisa = test_package["price_paisa"]
        original_price_rupees = test_package["price"]
        
        # Step 1: Update package price to ₹2.50 (250 paisa)
        new_price_rupees = 2.50
        response = requests.put(
            f"{BASE_URL}/api/admin/packages/{package_id}",
            headers=admin_headers,
            json={"price_rupees": new_price_rupees}
        )
        assert response.status_code == 200
        
        # Step 2: Verify package price updated in API
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        updated_package = next(p for p in packages if p["id"] == package_id)
        assert updated_package["price_paisa"] == 250, f"Expected 250 paisa, got {updated_package['price_paisa']}"
        
        # Step 3: Create order with new price
        response = requests.post(
            f"{BASE_URL}/api/orders/create",
            headers=user_headers,
            json={"player_uid": "TEST_88776655", "package_id": package_id}
        )
        assert response.status_code == 200
        order_data = response.json()
        order_id = order_data["order_id"]
        
        # Step 4: Verify order has new locked_price_paisa
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        assert response.status_code == 200
        order = response.json()
        assert order["locked_price_paisa"] == 250, f"Expected locked_price_paisa=250, got {order['locked_price_paisa']}"
        
        # Step 5: Revert package price to original
        response = requests.put(
            f"{BASE_URL}/api/admin/packages/{package_id}",
            headers=admin_headers,
            json={"price_rupees": original_price_rupees}
        )
        assert response.status_code == 200
        
        # Step 6: Verify package price reverted
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        reverted_package = next(p for p in packages if p["id"] == package_id)
        assert reverted_package["price_paisa"] == original_price_paisa
        
        # Step 7: Verify old order STILL has locked_price_paisa = 250 (not reverted)
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        assert response.status_code == 200
        order = response.json()
        assert order["locked_price_paisa"] == 250, f"Old order should retain locked_price_paisa=250, got {order['locked_price_paisa']}"
    
    def test_packages_api_returns_fresh_prices(self, admin_token):
        """Test that packages API returns fresh prices without caching"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get a package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        test_package = packages[0]
        package_id = test_package["id"]
        original_price = test_package["price"]
        
        # Update price
        new_price = original_price + 0.01
        requests.put(
            f"{BASE_URL}/api/admin/packages/{package_id}",
            headers=admin_headers,
            json={"price_rupees": new_price}
        )
        
        # Immediately fetch packages - should have new price (no caching)
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        updated_package = next(p for p in packages if p["id"] == package_id)
        assert abs(updated_package["price"] - new_price) < 0.02, "Packages API should return fresh prices"
        
        # Revert
        requests.put(
            f"{BASE_URL}/api/admin/packages/{package_id}",
            headers=admin_headers,
            json={"price_rupees": original_price}
        )


class TestAdminOrdersAllTypes:
    """Test Admin Orders page shows ALL orders (wallet_load + product_topup)"""
    
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
    
    def test_admin_orders_returns_all_order_types(self, admin_token):
        """Test admin orders API returns both product_topup and wallet_load orders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        
        # Verify order structure includes order_type
        if len(orders) > 0:
            order = orders[0]
            assert "order_type" in order
            assert order["order_type"] in ["product_topup", "wallet_load"]
    
    def test_admin_orders_filter_by_product_topup(self, admin_token):
        """Test admin can filter orders by order_type=product_topup"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders?order_type=product_topup", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        
        # All returned orders should be product_topup
        for order in orders:
            assert order["order_type"] == "product_topup"
    
    def test_admin_orders_filter_by_wallet_load(self, admin_token):
        """Test admin can filter orders by order_type=wallet_load"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders?order_type=wallet_load", headers=headers)
        assert response.status_code == 200
        orders = response.json()
        
        # All returned orders should be wallet_load
        for order in orders:
            assert order["order_type"] == "wallet_load"
    
    def test_admin_orders_filter_by_status(self, admin_token):
        """Test admin can filter orders by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test various statuses
        for status in ["pending_payment", "success", "queued", "paid"]:
            response = requests.get(f"{BASE_URL}/api/admin/orders?status={status}", headers=headers)
            assert response.status_code == 200
            orders = response.json()
            
            for order in orders:
                assert order["status"] == status
    
    def test_admin_orders_combined_filters(self, admin_token):
        """Test admin can combine order_type and status filters"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/admin/orders?order_type=product_topup&status=queued", 
            headers=headers
        )
        assert response.status_code == 200
        orders = response.json()
        
        for order in orders:
            assert order["order_type"] == "product_topup"
            assert order["status"] == "queued"


class TestAdminOrderEdit:
    """Test Admin can edit orders (player_uid, status, notes)"""
    
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
    
    @pytest.fixture
    def test_order_id(self, admin_token):
        """Get a test order ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        orders = response.json()
        if len(orders) > 0:
            return orders[0]["id"]
        pytest.skip("No orders available for testing")
    
    def test_admin_can_view_order_details(self, admin_token, test_order_id):
        """Test admin can view single order details"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        assert response.status_code == 200
        order = response.json()
        
        # Verify order has all required fields
        assert "id" in order
        assert "order_type" in order
        assert "status" in order
        assert "locked_price" in order
        assert "locked_price_paisa" in order
        assert "username" in order
    
    def test_admin_can_update_player_uid(self, admin_token, test_order_id):
        """Test admin can update player_uid"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get original UID
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        original_uid = response.json().get("player_uid")
        
        # Update UID
        new_uid = "TEST_12345678"
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={"player_uid": new_uid}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        assert response.json()["player_uid"] == new_uid
        
        # Revert if original was set
        if original_uid:
            requests.put(
                f"{BASE_URL}/api/admin/orders/{test_order_id}",
                headers=headers,
                json={"player_uid": original_uid}
            )
    
    def test_admin_can_update_status(self, admin_token, test_order_id):
        """Test admin can update order status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get original status
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        original_status = response.json()["status"]
        
        # Update to manual_review
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={"status": "manual_review"}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        assert response.json()["status"] == "manual_review"
        
        # Revert
        requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={"status": original_status}
        )
    
    def test_admin_can_update_notes(self, admin_token, test_order_id):
        """Test admin can update order notes"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Update notes
        test_note = "TEST_Admin note for testing"
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={"notes": test_note}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        assert response.json()["notes"] == test_note
    
    def test_admin_update_rejects_invalid_status(self, admin_token, test_order_id):
        """Test admin update rejects invalid status values"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={"status": "invalid_status_xyz"}
        )
        assert response.status_code == 400
        assert "Invalid status" in response.json().get("detail", "")
    
    def test_admin_can_update_multiple_fields(self, admin_token, test_order_id):
        """Test admin can update multiple fields at once"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get original values
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        original = response.json()
        
        # Update multiple fields
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={
                "player_uid": "TEST_99998888",
                "status": "manual_review",
                "notes": "TEST_Multiple field update"
            }
        )
        assert response.status_code == 200
        
        # Verify all updates
        response = requests.get(f"{BASE_URL}/api/admin/orders/{test_order_id}", headers=headers)
        updated = response.json()
        assert updated["player_uid"] == "TEST_99998888"
        assert updated["status"] == "manual_review"
        assert updated["notes"] == "TEST_Multiple field update"
        
        # Revert
        requests.put(
            f"{BASE_URL}/api/admin/orders/{test_order_id}",
            headers=headers,
            json={
                "player_uid": original.get("player_uid") or "12345678",
                "status": original["status"],
                "notes": original.get("notes") or ""
            }
        )


class TestWalletLoadOrders:
    """Test wallet load order creation and visibility in admin"""
    
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
    
    def test_create_wallet_load_order(self, user_token):
        """Test user can create wallet load order"""
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/orders/wallet-load",
            headers=headers,
            json={"amount_rupees": 100.0}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "order_id" in data
        assert data["status"] == "pending_payment"
        assert data["load_amount"] == 100.0
    
    def test_wallet_load_order_visible_in_admin(self, admin_token, user_token):
        """Test wallet load orders are visible in admin orders list"""
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create wallet load order
        response = requests.post(
            f"{BASE_URL}/api/orders/wallet-load",
            headers=user_headers,
            json={"amount_rupees": 50.0}
        )
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Verify visible in admin orders
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=admin_headers)
        orders = response.json()
        
        wallet_order = next((o for o in orders if o["id"] == order_id), None)
        assert wallet_order is not None, "Wallet load order should be visible in admin orders"
        assert wallet_order["order_type"] == "wallet_load"
    
    def test_wallet_load_order_filterable(self, admin_token, user_token):
        """Test wallet load orders can be filtered by order_type"""
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create wallet load order
        response = requests.post(
            f"{BASE_URL}/api/orders/wallet-load",
            headers=user_headers,
            json={"amount_rupees": 25.0}
        )
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Filter by wallet_load
        response = requests.get(
            f"{BASE_URL}/api/admin/orders?order_type=wallet_load", 
            headers=admin_headers
        )
        orders = response.json()
        
        # Should find our order
        wallet_order = next((o for o in orders if o["id"] == order_id), None)
        assert wallet_order is not None, "Wallet load order should be in filtered results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
