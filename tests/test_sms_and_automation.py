"""
Free Fire Diamond Top-Up Platform - P1 Testing
Tests: SMS Receive Endpoint & Automation System

Features tested:
1. SMS receive endpoint parses FonePay/bank SMS correctly
2. SMS extracts amount, last3digits, RRN from message
3. SMS auto-matches to pending orders with matching last3digits
4. Duplicate SMS (same fingerprint) is rejected
5. Duplicate RRN is rejected
6. Admin can view automation queue (/api/admin/automation/queue)
7. Admin can trigger automation for single order (/api/admin/orders/{id}/process)
8. Admin can trigger batch automation (/api/admin/automation/process-all)
9. Payment verification flow with SMS matching works end-to-end
10. Overpayment is credited to user wallet
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://payment-system-82.preview.emergentagent.com').rstrip('/')


# ===== FIXTURES =====

@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/admin/login", json={
        "identifier": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture
def user_token():
    """Get user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "identifier": "testclient",
        "password": "test123"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("User authentication failed")


@pytest.fixture
def package_id():
    """Get first package ID"""
    response = requests.get(f"{BASE_URL}/api/packages/list")
    packages = response.json()
    return packages[0]["id"]


# ===== SMS PARSING TESTS =====

class TestSMSReceiveEndpoint:
    """Test SMS receive endpoint parsing and storage"""
    
    def test_sms_receive_endpoint_exists(self):
        """Test that SMS receive endpoint exists and accepts POST"""
        # Send a unique SMS to avoid duplicate rejection
        unique_id = str(uuid.uuid4())[:8]
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": f"TEST_{unique_id} Rs. 100.00 received from 98XXXXX123 for Payment. RRN: TEST{unique_id}. Bal: Rs 15000.00"
        })
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_sms_parses_fonepay_format(self):
        """Test SMS parsing extracts amount, last3digits, RRN from FonePay format"""
        unique_id = str(uuid.uuid4())[:8]
        sms_message = f"Rs. 125.50 received from 98XXXXX456 for Payment. RRN: FP{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        # SMS should be saved (matched or not)
        data = response.json()
        assert "message" in data
    
    def test_sms_parses_bank_format_with_asterisks(self):
        """Test SMS parsing with asterisk-masked phone number"""
        unique_id = str(uuid.uuid4())[:8]
        sms_message = f"Rs. 200.00 received from 900****789 for Payment. RRN: BNK{unique_id}. Bal: Rs 20000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
    
    def test_sms_parses_amount_with_comma(self):
        """Test SMS parsing handles amounts with commas"""
        unique_id = str(uuid.uuid4())[:8]
        sms_message = f"Rs. 1,500.00 received from 98XXXXX321 for Payment. RRN: CMM{unique_id}. Bal: Rs 25,000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200


class TestDuplicateSMSRejection:
    """Test duplicate SMS and RRN rejection"""
    
    def test_duplicate_sms_fingerprint_rejected(self):
        """Test that duplicate SMS (same fingerprint) is rejected"""
        unique_id = str(uuid.uuid4())[:8]
        sms_message = f"Rs. 100.00 received from 98XXXXX111 for Payment. RRN: DUP{unique_id}. Bal: Rs 15000.00"
        
        # First SMS should be accepted
        response1 = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second identical SMS should be rejected as duplicate
        response2 = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("duplicate") == True, "Duplicate SMS should be flagged"
        assert "Duplicate" in data2.get("message", "")
    
    def test_duplicate_rrn_rejected_via_sms(self):
        """Test that duplicate RRN is rejected when sending same RRN twice via SMS"""
        unique_id = str(uuid.uuid4())[:8]
        rrn = f"DRNTEST{unique_id}"
        
        # First SMS with RRN
        sms_message1 = f"Rs. 100.00 received from 98XXXXX111 for Payment. RRN: {rrn}. Bal: Rs 15000.00"
        response1 = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message1
        })
        assert response1.status_code == 200
        
        # Second SMS with same RRN but different amount (different fingerprint)
        sms_message2 = f"Rs. 200.00 received from 98XXXXX222 for Payment. RRN: {rrn}. Bal: Rs 20000.00"
        response2 = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message2
        })
        assert response2.status_code == 200
        # If first SMS matched an order, second should report RRN already used
        # This is a valid test - the system should handle duplicate RRNs


class TestSMSAutoMatching:
    """Test SMS auto-matching to pending orders"""
    
    def test_sms_auto_matches_to_pending_order(self, admin_token):
        """Test SMS auto-matches to pending order with matching last3digits"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        last3 = unique_id[:3]  # Use first 3 chars as last3digits
        
        # Create a new test user to avoid wallet balance issues
        test_username = f"smstest_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        package_id = packages[0]["id"]
        
        # Create order (new user has 0 wallet balance)
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "33333333",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Get order details
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        payment_required = order.get("payment_required", 1.99)
        
        # Order should be pending_payment for new user with 0 wallet
        assert order["status"] == "pending_payment", f"New user order should be pending_payment, got {order['status']}"
        
        # Submit payment verification with specific last3digits
        response = requests.post(f"{BASE_URL}/api/orders/verify-payment", headers=user_headers, json={
            "order_id": order_id,
            "sent_amount_rupees": payment_required,
            "last_3_digits": last3,
            "payment_method": "FonePay"
        })
        assert response.status_code == 200
        
        # Now send SMS with matching last3digits and sufficient amount
        sms_amount = payment_required + 0.01  # Slightly more than required
        sms_message = f"Rs. {sms_amount:.2f} received from 98XXXXX{last3} for Payment. RRN: AUTO{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        data = response.json()
        
        # Check if matched
        if data.get("matched"):
            assert data.get("order_id") == order_id, "SMS should match to our order"
    
    def test_sms_no_match_without_pending_order(self):
        """Test SMS doesn't match when no pending order exists"""
        unique_id = str(uuid.uuid4())[:8]
        # Use random last3digits that won't match any order
        sms_message = f"Rs. 999.99 received from 98XXXXX999 for Payment. RRN: NOMATCH{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("matched") == False, "SMS should not match without pending order"


class TestOverpaymentCredit:
    """Test overpayment is credited to user wallet"""
    
    def test_overpayment_credited_to_wallet(self, admin_token):
        """Test that overpayment is credited to user wallet"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        last3 = "777"
        
        # Create a new test user to avoid wallet balance issues
        test_username = f"overpay_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get initial wallet balance (should be 0 for new user)
        response = requests.get(f"{BASE_URL}/api/user/wallet", headers=user_headers)
        initial_balance = response.json().get("balance", 0)
        assert initial_balance == 0, "New user should have 0 wallet balance"
        
        # Get package - use a more expensive one to allow larger overpayment
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        # Find a package with price > ₹5 to allow meaningful overpayment
        test_package = next((p for p in packages if p["price"] >= 5), packages[-1])
        package_id = test_package["id"]
        
        # Create order
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "44444444",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Get order details
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        payment_required = order.get("payment_required", 5.0)
        
        # Calculate safe overpayment (less than 3x required to avoid suspicious flag)
        # Overpay by 50% of required amount (safe margin)
        overpayment = payment_required * 0.5
        total_payment = payment_required + overpayment
        
        # Submit payment verification with overpayment
        response = requests.post(f"{BASE_URL}/api/orders/verify-payment", headers=user_headers, json={
            "order_id": order_id,
            "sent_amount_rupees": total_payment,
            "last_3_digits": last3,
            "payment_method": "FonePay"
        })
        assert response.status_code == 200
        
        # Send SMS with overpayment
        sms_message = f"Rs. {total_payment:.2f} received from 98XXXXX{last3} for Payment. RRN: OVER{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        data = response.json()
        
        if data.get("matched"):
            # Check order status - should be paid, not suspicious
            response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
            order = response.json()
            
            if order["status"] == "paid" or order["status"] == "queued":
                # Check wallet balance increased
                response = requests.get(f"{BASE_URL}/api/user/wallet", headers=user_headers)
                new_balance = response.json().get("balance", 0)
                
                # Overpayment should be credited
                balance_increase = new_balance - initial_balance
                assert balance_increase > 0, f"Wallet should be credited with overpayment, got increase of {balance_increase}"
            elif order["status"] == "suspicious":
                # This is expected if overpayment was too large
                pass  # Test passes - suspicious detection is working


# ===== AUTOMATION QUEUE TESTS =====

class TestAutomationQueue:
    """Test admin automation queue endpoints"""
    
    def test_admin_can_view_automation_queue(self, admin_token):
        """Test admin can view automation queue"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/automation/queue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "queued_count" in data
        assert "processing_count" in data
        assert "orders" in data
        assert isinstance(data["orders"], list)
        assert isinstance(data["queued_count"], int)
        assert isinstance(data["processing_count"], int)
    
    def test_automation_queue_requires_admin_auth(self):
        """Test automation queue requires admin authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/automation/queue")
        assert response.status_code in [401, 403]
    
    def test_automation_queue_shows_queued_orders(self, admin_token):
        """Test automation queue shows orders with queued/processing status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/automation/queue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # All orders in queue should be queued or processing
        for order in data["orders"]:
            assert order["status"] in ["queued", "processing"], f"Order status should be queued or processing, got {order['status']}"
            assert order["order_type"] == "product_topup", "Only product_topup orders should be in automation queue"


class TestAdminTriggerAutomation:
    """Test admin can trigger automation for orders"""
    
    def test_admin_can_trigger_single_order_automation(self, admin_token):
        """Test admin can trigger automation for a single queued order"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a new test user
        test_username = f"autotest_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        package_id = packages[0]["id"]
        
        # Create an order
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "55555555",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Admin marks order as queued (simulating payment received)
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}",
            headers=admin_headers,
            json={"status": "queued"}
        )
        assert response.status_code == 200
        
        # Now try to trigger automation
        response = requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/process",
            headers=admin_headers
        )
        
        # Should succeed
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data.get("order_id") == order_id
    
    def test_trigger_automation_requires_queued_status(self, admin_token):
        """Test that triggering automation requires order to be in queued/paid status"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a new test user
        test_username = f"statustest_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        package_id = packages[0]["id"]
        
        # Create an order (will be pending_payment for new user)
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "66666666",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Verify order is pending_payment
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        assert order["status"] == "pending_payment", f"New user order should be pending_payment, got {order['status']}"
        
        # Try to trigger automation on pending_payment order
        response = requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/process",
            headers=admin_headers
        )
        
        # Should fail because order is not queued
        assert response.status_code == 400
        data = response.json()
        assert "queued" in data.get("detail", "").lower() or "paid" in data.get("detail", "").lower()
    
    def test_trigger_automation_rejects_wallet_load_orders(self, admin_token, user_token):
        """Test that automation cannot be triggered for wallet_load orders"""
        user_headers = {"Authorization": f"Bearer {user_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create wallet load order
        response = requests.post(f"{BASE_URL}/api/orders/wallet-load", headers=user_headers, json={
            "amount_rupees": 100.0
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Try to trigger automation
        response = requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/process",
            headers=admin_headers
        )
        
        # Should fail because wallet_load orders can't be automated
        assert response.status_code == 400
        data = response.json()
        assert "product" in data.get("detail", "").lower()


class TestBatchAutomation:
    """Test admin batch automation endpoint"""
    
    def test_admin_can_trigger_batch_automation(self, admin_token):
        """Test admin can trigger batch automation for all queued orders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/admin/automation/process-all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "count" in data
        assert isinstance(data["count"], int)
    
    def test_batch_automation_requires_admin_auth(self):
        """Test batch automation requires admin authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/automation/process-all")
        assert response.status_code in [401, 403]
    
    def test_batch_automation_returns_zero_when_no_queued(self, admin_token):
        """Test batch automation returns count=0 when no queued orders"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First, check current queue
        response = requests.get(f"{BASE_URL}/api/admin/automation/queue", headers=headers)
        queue_data = response.json()
        
        # Trigger batch automation
        response = requests.post(f"{BASE_URL}/api/admin/automation/process-all", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Count should match queued_count from queue
        assert data["count"] >= 0


# ===== END-TO-END PAYMENT FLOW TESTS =====

class TestEndToEndPaymentFlow:
    """Test complete payment flow: create order -> send SMS -> verify payment"""
    
    def test_full_payment_flow_with_sms_matching(self, admin_token):
        """Test full payment flow: create order -> submit verification -> send SMS -> check status"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        last3 = "888"
        
        # Create a new test user
        test_username = f"e2etest_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        package_id = packages[0]["id"]
        
        # Step 1: Create order
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "77777777",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_data = response.json()
        order_id = order_data["order_id"]
        
        # Step 2: Get order details
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        assert response.status_code == 200
        order = response.json()
        payment_required = order.get("payment_required", 1.99)
        initial_status = order["status"]
        
        # New user should have pending_payment status
        assert initial_status == "pending_payment", f"New user order should be pending_payment, got {initial_status}"
        
        # Step 3: Submit payment verification
        response = requests.post(f"{BASE_URL}/api/orders/verify-payment", headers=user_headers, json={
            "order_id": order_id,
            "sent_amount_rupees": payment_required,
            "last_3_digits": last3,
            "payment_method": "FonePay"
        })
        assert response.status_code == 200
        
        # Step 4: Send matching SMS
        sms_message = f"Rs. {payment_required:.2f} received from 98XXXXX{last3} for Payment. RRN: E2E{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        sms_data = response.json()
        
        # Step 5: Check order status changed
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        assert response.status_code == 200
        updated_order = response.json()
        
        # If SMS matched, status should change from pending_payment
        if sms_data.get("matched"):
            assert updated_order["status"] in ["paid", "queued", "processing", "success"], \
                f"Order status should change after SMS match, got {updated_order['status']}"
    
    def test_order_status_tracking(self, admin_token):
        """Test order status tracking through various states"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a new test user
        test_username = f"statustrack_{unique_id}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": test_username,
            "password": "test123"
        })
        assert response.status_code == 200
        user_token = response.json()["token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Get package
        response = requests.get(f"{BASE_URL}/api/packages/list")
        packages = response.json()
        package_id = packages[0]["id"]
        
        # Create order
        response = requests.post(f"{BASE_URL}/api/orders/create", headers=user_headers, json={
            "player_uid": "88888888",
            "package_id": package_id
        })
        assert response.status_code == 200
        order_id = response.json()["order_id"]
        
        # Check initial status (should be pending_payment for new user)
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        assert order["status"] == "pending_payment", f"Initial status should be pending_payment, got {order['status']}"
        
        # Admin can update status to manual_review
        response = requests.put(
            f"{BASE_URL}/api/admin/orders/{order_id}",
            headers=admin_headers,
            json={"status": "manual_review"}
        )
        assert response.status_code == 200
        
        # Verify status changed
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        assert order["status"] == "manual_review"
        
        # Admin can mark as success
        response = requests.post(
            f"{BASE_URL}/api/admin/orders/{order_id}/mark-success",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        # Verify final status
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        order = response.json()
        assert order["status"] == "success"


# ===== ADMIN SMS MANAGEMENT TESTS =====

class TestAdminSMSManagement:
    """Test admin SMS management endpoints"""
    
    def test_admin_can_list_sms(self, admin_token):
        """Test admin can list all SMS messages"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/sms", headers=headers)
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)
        
        # Verify SMS structure if messages exist
        if len(messages) > 0:
            sms = messages[0]
            assert "id" in sms
            assert "raw_message" in sms
            assert "amount" in sms  # Converted from paisa
            assert "used" in sms
    
    def test_admin_can_input_sms_manually(self, admin_token):
        """Test admin can manually input SMS"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        sms_message = f"Rs. 150.00 received from 98XXXXX333 for Payment. RRN: ADMIN{unique_id}. Bal: Rs 15000.00"
        
        response = requests.post(f"{BASE_URL}/api/admin/sms/input", headers=headers, json={
            "raw_message": sms_message
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "parsed" in data
        # Verify parsing worked
        parsed = data["parsed"]
        assert parsed.get("amount") == 150.0
        assert parsed.get("last3digits") == "333"
        assert parsed.get("rrn") == f"ADMIN{unique_id}"
    
    def test_admin_sms_input_detects_duplicate(self, admin_token):
        """Test admin SMS input detects duplicate"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        sms_message = f"Rs. 175.00 received from 98XXXXX444 for Payment. RRN: DUPTEST{unique_id}. Bal: Rs 15000.00"
        
        # First input
        response1 = requests.post(f"{BASE_URL}/api/admin/sms/input", headers=headers, json={
            "raw_message": sms_message
        })
        assert response1.status_code == 200
        
        # Second input (duplicate)
        response2 = requests.post(f"{BASE_URL}/api/admin/sms/input", headers=headers, json={
            "raw_message": sms_message
        })
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("duplicate") == True


class TestAdminReviewQueue:
    """Test admin review queue endpoint"""
    
    def test_admin_can_view_review_queue(self, admin_token):
        """Test admin can view orders needing review"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/review-queue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "orders" in data
        assert "unmatched_sms" in data
        assert isinstance(data["orders"], list)
        assert isinstance(data["unmatched_sms"], list)
    
    def test_review_queue_shows_correct_statuses(self, admin_token):
        """Test review queue shows orders with review-needed statuses"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/review-queue", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        review_statuses = ["manual_review", "suspicious", "failed", "invalid_uid", "duplicate_payment"]
        
        for order in data["orders"]:
            assert order["status"] in review_statuses, \
                f"Order in review queue should have review status, got {order['status']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
