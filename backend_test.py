#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class FreeFireDiamondAPITester:
    def __init__(self, base_url="https://airflow-tracker-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.user_token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_user_id = None
        self.test_order_id = None
        self.package_id = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method, endpoint, data=None, token=None, expected_status=200):
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            
            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return success, response.status_code, response_data
            
        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_initialization(self):
        """Test system initialization"""
        print("\n🔧 Testing System Initialization...")
        
        success, status, data = self.make_request('POST', 'admin/init', expected_status=200)
        return self.log_test("Initialize System", success, f"Status: {status}")

    def test_admin_authentication(self):
        """Test admin login"""
        print("\n🔐 Testing Admin Authentication...")
        
        # Test admin login
        login_data = {
            "identifier": "admin",
            "password": "admin123"
        }
        
        success, status, data = self.make_request('POST', 'admin/login', login_data)
        
        if success and 'token' in data:
            self.admin_token = data['token']
            self.log_test("Admin Login", True, f"Token received, user_type: {data.get('user_type')}")
        else:
            self.log_test("Admin Login", False, f"Status: {status}, Response: {data}")
        
        # Test invalid admin credentials
        invalid_data = {
            "identifier": "admin",
            "password": "wrongpassword"
        }
        
        success, status, data = self.make_request('POST', 'admin/login', invalid_data, expected_status=401)
        self.log_test("Admin Login - Invalid Credentials", success, f"Status: {status}")

    def test_user_authentication(self):
        """Test user signup and login"""
        print("\n👤 Testing User Authentication...")
        
        # Generate unique username
        timestamp = int(time.time())
        test_username = f"testuser_{timestamp}"
        test_email = f"test_{timestamp}@example.com"
        test_password = "TestPass123!"
        
        # Test user signup
        signup_data = {
            "username": test_username,
            "email": test_email,
            "password": test_password
        }
        
        success, status, data = self.make_request('POST', 'auth/signup', signup_data)
        
        if success and 'token' in data:
            self.user_token = data['token']
            self.log_test("User Signup", True, f"Username: {test_username}")
        else:
            self.log_test("User Signup", False, f"Status: {status}, Response: {data}")
            return False
        
        # Test user login
        login_data = {
            "identifier": test_username,
            "password": test_password
        }
        
        success, status, data = self.make_request('POST', 'auth/login', login_data)
        
        if success and 'token' in data:
            self.user_token = data['token']  # Update token
            self.log_test("User Login", True, f"Wallet balance: {data.get('wallet_balance', 0)}")
        else:
            self.log_test("User Login", False, f"Status: {status}, Response: {data}")
        
        # Test invalid user credentials
        invalid_data = {
            "identifier": test_username,
            "password": "wrongpassword"
        }
        
        success, status, data = self.make_request('POST', 'auth/login', invalid_data, expected_status=401)
        self.log_test("User Login - Invalid Credentials", success, f"Status: {status}")
        
        return True

    def test_packages(self):
        """Test package listing"""
        print("\n📦 Testing Package Management...")
        
        success, status, data = self.make_request('GET', 'packages/list')
        
        if success and isinstance(data, list) and len(data) > 0:
            self.package_id = data[0]['id']  # Store first package ID for order testing
            self.log_test("List Packages", True, f"Found {len(data)} packages")
            
            # Verify package structure
            package = data[0]
            required_fields = ['id', 'name', 'diamonds', 'price', 'active']
            has_all_fields = all(field in package for field in required_fields)
            self.log_test("Package Structure", has_all_fields, f"First package: {package.get('name', 'Unknown')}")
        else:
            self.log_test("List Packages", False, f"Status: {status}, Response: {data}")

    def test_user_profile_and_wallet(self):
        """Test user profile and wallet endpoints"""
        print("\n💰 Testing User Profile & Wallet...")
        
        if not self.user_token:
            self.log_test("User Profile & Wallet", False, "No user token available")
            return
        
        # Test user profile
        success, status, data = self.make_request('GET', 'user/profile', token=self.user_token)
        self.log_test("Get User Profile", success, f"Status: {status}")
        
        # Test wallet
        success, status, data = self.make_request('GET', 'user/wallet', token=self.user_token)
        
        if success and 'balance' in data and 'transactions' in data:
            self.log_test("Get Wallet", True, f"Balance: {data['balance']}, Transactions: {len(data['transactions'])}")
        else:
            self.log_test("Get Wallet", False, f"Status: {status}, Response: {data}")

    def test_order_creation(self):
        """Test order creation flow with Bangladesh server requirement"""
        print("\n🛒 Testing Order Management...")
        
        if not self.user_token or not self.package_id:
            self.log_test("Order Creation", False, "Missing user token or package ID")
            return
        
        # Test 1: Create order WITHOUT server field (should default to Bangladesh)
        order_data = {
            "player_uid": "123456789",
            "package_id": self.package_id
        }
        
        success, status, data = self.make_request('POST', 'orders/create', order_data, token=self.user_token)
        
        if success and 'order_id' in data:
            self.test_order_id = data['order_id']
            self.log_test("Create Order (No Server Field)", True, f"Order ID: {self.test_order_id}, Status: {data.get('status')}")
        else:
            self.log_test("Create Order (No Server Field)", False, f"Status: {status}, Response: {data}")
            return
        
        # Test 2: Get order details and verify server is "Bangladesh"
        success, status, order_details = self.make_request('GET', f'orders/{self.test_order_id}', token=self.user_token)
        
        if success:
            server_value = order_details.get('server')
            if server_value == "Bangladesh":
                self.log_test("Server Field Verification", True, f"Server correctly set to: {server_value}")
            else:
                self.log_test("Server Field Verification", False, f"Expected 'Bangladesh', got: {server_value}")
        else:
            self.log_test("Get Order Details", False, f"Status: {status}")
        
        # Test 3: Try creating order WITH server field (should still be Bangladesh)
        order_data_with_server = {
            "player_uid": "987654321",
            "package_id": self.package_id,
            "server": "Asia"  # This should be ignored
        }
        
        success, status, data = self.make_request('POST', 'orders/create', order_data_with_server, token=self.user_token)
        
        if success and 'order_id' in data:
            # Check if server is still Bangladesh
            success2, status2, order_details2 = self.make_request('GET', f'orders/{data["order_id"]}', token=self.user_token)
            if success2:
                server_value2 = order_details2.get('server')
                if server_value2 == "Bangladesh":
                    self.log_test("Server Override Test", True, f"Server forced to Bangladesh despite input: {server_value2}")
                else:
                    self.log_test("Server Override Test", False, f"Server not forced to Bangladesh: {server_value2}")
        
        # Test 4: List user orders
        success, status, data = self.make_request('GET', 'user/orders', token=self.user_token)
        
        if success and isinstance(data, list):
            self.log_test("List User Orders", True, f"Found {len(data)} orders")
        else:
            self.log_test("List User Orders", False, f"Status: {status}")

    def test_wallet_topup_flow(self):
        """Test wallet top-up payment verification flow"""
        print("\n💳 Testing Wallet Top-Up Flow...")
        
        if not self.user_token:
            self.log_test("Wallet Top-Up Flow", False, "No user token available")
            return
        
        # Simulate wallet top-up SMS message
        wallet_sms_data = {
            "raw_message": "Payment of Rs 100.00 received from 900****555. RRN: WALLET123456789. UPI/FONEPAY"
        }
        
        success, status, data = self.make_request('POST', 'sms/receive', wallet_sms_data)
        self.log_test("Wallet Top-Up SMS Simulation", success, f"Status: {status}")
        
        # Test wallet payment verification (this would be called from wallet payment details page)
        if self.test_order_id:  # Using existing order for testing payment verification
            wallet_payment_data = {
                "order_id": self.test_order_id,
                "sent_amount_rupees": 100.00,
                "last_3_digits": "555",
                "payment_method": "FonePay",
                "remark": "Wallet Top-up"
            }
            
            success, status, data = self.make_request('POST', 'orders/verify-payment', wallet_payment_data, token=self.user_token)
            
            if success:
                self.log_test("Wallet Payment Verification", True, f"Message: {data.get('message', '')}")
            else:
                self.log_test("Wallet Payment Verification", False, f"Status: {status}, Response: {data}")

    def test_sms_simulation(self):
        """Test SMS message simulation"""
        print("\n📱 Testing SMS Message Simulation...")
        
        # Simulate SMS message
        sms_data = {
            "raw_message": "Payment of Rs 4.50 received from 900****910. RRN: ABC123456789. UPI/PAYTM"
        }
        
        success, status, data = self.make_request('POST', 'sms/receive', sms_data)
        self.log_test("Receive SMS Message", success, f"Status: {status}")
        
        # Test payment verification if we have an order
        if self.test_order_id:
            payment_data = {
                "order_id": self.test_order_id,
                "sent_amount_rupees": 4.50,
                "last_3_digits": "910",
                "payment_method": "UPI",
                "remark": "PAYTM"
            }
            
            success, status, data = self.make_request('POST', 'orders/verify-payment', payment_data, token=self.user_token)
            
            if success:
                self.log_test("Verify Payment", True, f"Message: {data.get('message', '')}")
            else:
                self.log_test("Verify Payment", False, f"Status: {status}, Response: {data}")

    def test_admin_endpoints(self):
        """Test admin-specific endpoints"""
        print("\n👑 Testing Admin Endpoints...")
        
        if not self.admin_token:
            self.log_test("Admin Endpoints", False, "No admin token available")
            return
        
        # Test dashboard stats
        success, status, data = self.make_request('GET', 'admin/dashboard', token=self.admin_token)
        
        if success and 'total_orders' in data:
            self.log_test("Admin Dashboard", True, f"Total orders: {data['total_orders']}, Total sales: {data.get('total_sales', 0)}")
        else:
            self.log_test("Admin Dashboard", False, f"Status: {status}")
        
        # Test list all orders
        success, status, data = self.make_request('GET', 'admin/orders', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Admin List Orders", True, f"Found {len(data)} orders")
        else:
            self.log_test("Admin List Orders", False, f"Status: {status}")
        
        # Test order retry if we have an order
        if self.test_order_id:
            success, status, data = self.make_request('POST', f'admin/orders/{self.test_order_id}/retry', token=self.admin_token)
            self.log_test("Admin Retry Order", success, f"Status: {status}")

    def test_admin_wallet_management(self):
        """Test Admin Wallet Recharge and Redeem APIs"""
        print("\n💰 Testing Admin Wallet Management...")
        
        if not self.admin_token:
            self.log_test("Admin Wallet Management", False, "No admin token available")
            return
        
        # First, get users list to find testclient
        success, status, users_data = self.make_request('GET', 'admin/users', token=self.admin_token)
        
        if not success or not isinstance(users_data, list):
            self.log_test("Get Users List", False, f"Status: {status}")
            return
        
        # Find testclient user
        testclient_user = None
        for user in users_data:
            if user.get('username') == 'testclient':
                testclient_user = user
                break
        
        if not testclient_user:
            self.log_test("Find testclient User", False, "testclient user not found")
            return
        
        user_id = testclient_user['id']
        initial_balance = testclient_user.get('wallet_balance', 0)
        self.log_test("Find testclient User", True, f"User ID: {user_id}, Initial balance: ₹{initial_balance}")
        
        # Test 1: Valid Admin Wallet Recharge
        recharge_data = {
            "amount_paisa": 10000,  # ₹100
            "reason": "Test recharge for QA testing purposes"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/recharge', recharge_data, token=self.admin_token)
        
        if success and 'order_id' in data:
            self.log_test("Admin Wallet Recharge - Valid", True, f"Recharged ₹{data.get('amount_recharged', 0)}, New balance: ₹{data.get('new_balance', 0)}")
            recharge_order_id = data['order_id']
        else:
            self.log_test("Admin Wallet Recharge - Valid", False, f"Status: {status}, Response: {data}")
            return
        
        # Test 2: Invalid Recharge - Zero Amount
        invalid_recharge_data = {
            "amount_paisa": 0,
            "reason": "Test invalid amount"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/recharge', invalid_recharge_data, token=self.admin_token, expected_status=422)
        self.log_test("Admin Wallet Recharge - Zero Amount", success, f"Status: {status}")
        
        # Test 3: Invalid Recharge - Short Reason
        invalid_reason_data = {
            "amount_paisa": 5000,
            "reason": "Bad"  # Less than 5 characters
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/recharge', invalid_reason_data, token=self.admin_token, expected_status=400)
        self.log_test("Admin Wallet Recharge - Short Reason", success, f"Status: {status}")
        
        # Test 4: Valid Admin Wallet Redeem
        redeem_data = {
            "amount_paisa": 5000,  # ₹50
            "reason": "Test redemption for QA testing purposes"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/redeem', redeem_data, token=self.admin_token)
        
        if success and 'order_id' in data:
            self.log_test("Admin Wallet Redeem - Valid", True, f"Redeemed ₹{data.get('amount_redeemed', 0)}, New balance: ₹{data.get('new_balance', 0)}")
            redeem_order_id = data['order_id']
        else:
            self.log_test("Admin Wallet Redeem - Valid", False, f"Status: {status}, Response: {data}")
        
        # Test 5: Invalid Redeem - Insufficient Balance
        # First get current balance
        success, status, users_data = self.make_request('GET', 'admin/users', token=self.admin_token)
        current_user = next((u for u in users_data if u['id'] == user_id), None)
        current_balance_paisa = int(current_user['wallet_balance'] * 100) if current_user else 0
        
        excessive_redeem_data = {
            "amount_paisa": current_balance_paisa + 10000,  # More than current balance
            "reason": "Test insufficient balance"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/redeem', excessive_redeem_data, token=self.admin_token, expected_status=400)
        self.log_test("Admin Wallet Redeem - Insufficient Balance", success, f"Status: {status}")
        
        # Test 6: Invalid Redeem - Exceeds Single Action Limit (₹5000)
        limit_exceed_data = {
            "amount_paisa": 600000,  # ₹6000 > ₹5000 limit
            "reason": "Test single action limit"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/redeem', limit_exceed_data, token=self.admin_token, expected_status=400)
        self.log_test("Admin Wallet Redeem - Exceeds Limit", success, f"Status: {status}")
        
        # Test 7: Invalid Redeem - Short Reason
        invalid_redeem_reason = {
            "amount_paisa": 1000,
            "reason": "Bad"  # Less than 5 characters
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/redeem', invalid_redeem_reason, token=self.admin_token, expected_status=400)
        self.log_test("Admin Wallet Redeem - Short Reason", success, f"Status: {status}")

    def test_admin_action_logs(self):
        """Test Admin Action Logs API"""
        print("\n📋 Testing Admin Action Logs...")
        
        if not self.admin_token:
            self.log_test("Admin Action Logs", False, "No admin token available")
            return
        
        # Test 1: Get all action logs
        success, status, data = self.make_request('GET', 'admin/action-logs', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Get All Action Logs", True, f"Found {len(data)} action logs")
            
            # Check if we have wallet actions from previous tests
            wallet_actions = [log for log in data if log.get('action_type') in ['wallet_recharge', 'wallet_redeem']]
            if wallet_actions:
                self.log_test("Wallet Actions in Logs", True, f"Found {len(wallet_actions)} wallet actions")
            else:
                self.log_test("Wallet Actions in Logs", False, "No wallet actions found in logs")
        else:
            self.log_test("Get All Action Logs", False, f"Status: {status}")
            return
        
        # Test 2: Filter by action_type=wallet_recharge
        success, status, data = self.make_request('GET', 'admin/action-logs?action_type=wallet_recharge', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Filter by wallet_recharge", True, f"Found {len(data)} recharge logs")
        else:
            self.log_test("Filter by wallet_recharge", False, f"Status: {status}")
        
        # Test 3: Filter by action_type=wallet_redeem
        success, status, data = self.make_request('GET', 'admin/action-logs?action_type=wallet_redeem', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Filter by wallet_redeem", True, f"Found {len(data)} redeem logs")
        else:
            self.log_test("Filter by wallet_redeem", False, f"Status: {status}")
        
        # Test 4: Filter by admin_username
        success, status, data = self.make_request('GET', 'admin/action-logs?admin_username=admin', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Filter by admin username", True, f"Found {len(data)} logs for admin")
        else:
            self.log_test("Filter by admin username", False, f"Status: {status}")
        
        # Test 5: Get action types helper endpoint
        success, status, data = self.make_request('GET', 'admin/action-logs/action-types', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Get Action Types", True, f"Found {len(data)} action types: {data}")
        else:
            self.log_test("Get Action Types", False, f"Status: {status}")
        
        # Test 6: Get admin usernames helper endpoint
        success, status, data = self.make_request('GET', 'admin/action-logs/admins', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Get Admin Usernames", True, f"Found {len(data)} admin usernames: {data}")
        else:
            self.log_test("Get Admin Usernames", False, f"Status: {status}")

    def test_user_wallet_verification(self):
        """Test User Wallet Verification after admin actions"""
        print("\n🔍 Testing User Wallet Verification...")
        
        # Login as testclient to verify wallet changes
        login_data = {
            "identifier": "testclient",
            "password": "test123"
        }
        
        success, status, data = self.make_request('POST', 'auth/login', login_data)
        
        if success and 'token' in data:
            testclient_token = data['token']
            self.log_test("testclient Login", True, f"Wallet balance: {data.get('wallet_balance', 0)}")
        else:
            self.log_test("testclient Login", False, f"Status: {status}")
            return
        
        # Test user wallet endpoint
        success, status, data = self.make_request('GET', 'user/wallet', token=testclient_token)
        
        if success and 'balance' in data and 'transactions' in data:
            balance = data['balance']
            transactions = data['transactions']
            
            # Check for admin_recharge and admin_redeem transactions
            admin_recharge_txs = [tx for tx in transactions if tx.get('type') == 'admin_recharge']
            admin_redeem_txs = [tx for tx in transactions if tx.get('type') == 'admin_redeem']
            
            self.log_test("User Wallet Balance", True, f"Current balance: ₹{balance}")
            self.log_test("Admin Recharge Transactions", len(admin_recharge_txs) > 0, f"Found {len(admin_recharge_txs)} recharge transactions")
            self.log_test("Admin Redeem Transactions", len(admin_redeem_txs) > 0, f"Found {len(admin_redeem_txs)} redeem transactions")
        else:
            self.log_test("User Wallet Verification", False, f"Status: {status}")
        
        # Test user orders endpoint
        success, status, data = self.make_request('GET', 'user/orders', token=testclient_token)
        
        if success and isinstance(data, list):
            # Check for admin wallet orders
            admin_recharge_orders = [order for order in data if order.get('package_name') == 'Admin Wallet Recharge']
            admin_redeem_orders = [order for order in data if order.get('package_name') == 'Admin Wallet Redemption']
            
            self.log_test("User Orders - Admin Recharge", len(admin_recharge_orders) > 0, f"Found {len(admin_recharge_orders)} recharge orders")
            self.log_test("User Orders - Admin Redeem", len(admin_redeem_orders) > 0, f"Found {len(admin_redeem_orders)} redeem orders")
        else:
            self.log_test("User Orders Verification", False, f"Status: {status}")

    def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n⚠️  Testing Error Handling...")
        
        # Test accessing protected endpoint without token
        success, status, data = self.make_request('GET', 'user/profile', expected_status=401)
        self.log_test("No Token Access", success, f"Status: {status}")
        
        # Test accessing admin endpoint with user token
        if self.user_token:
            success, status, data = self.make_request('GET', 'admin/dashboard', token=self.user_token, expected_status=403)
            self.log_test("User Access Admin Endpoint", success, f"Status: {status}")
        
        # Test invalid order ID
        success, status, data = self.make_request('GET', 'orders/invalid-order-id', token=self.user_token, expected_status=404)
        self.log_test("Invalid Order ID", success, f"Status: {status}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Free Fire Diamond Top-Up Platform API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run test suites in order
        self.test_initialization()
        self.test_admin_authentication()
        self.test_user_authentication()
        self.test_packages()
        self.test_user_profile_and_wallet()
        self.test_order_creation()
        self.test_wallet_topup_flow()
        self.test_sms_simulation()
        self.test_admin_endpoints()
        
        # NEW: Test Admin Wallet Management Features
        self.test_admin_wallet_management()
        self.test_admin_action_logs()
        self.test_user_wallet_verification()
        
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("💥 SOME TESTS FAILED!")
            return 1

def main():
    tester = FreeFireDiamondAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())