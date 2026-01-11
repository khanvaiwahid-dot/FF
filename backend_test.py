#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class FreeFireDiamondAPITester:
    def __init__(self, base_url="https://diamondtop.preview.emergentagent.com"):
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
        """Test order creation flow"""
        print("\n🛒 Testing Order Management...")
        
        if not self.user_token or not self.package_id:
            self.log_test("Order Creation", False, "Missing user token or package ID")
            return
        
        # Create order
        order_data = {
            "player_uid": "123456789",
            "server": "Asia",
            "package_id": self.package_id
        }
        
        success, status, data = self.make_request('POST', 'orders/create', order_data, token=self.user_token)
        
        if success and 'order_id' in data:
            self.test_order_id = data['order_id']
            self.log_test("Create Order", True, f"Order ID: {self.test_order_id}, Status: {data.get('status')}")
        else:
            self.log_test("Create Order", False, f"Status: {status}, Response: {data}")
            return
        
        # Get order details
        success, status, data = self.make_request('GET', f'orders/{self.test_order_id}', token=self.user_token)
        self.log_test("Get Order Details", success, f"Status: {status}")
        
        # List user orders
        success, status, data = self.make_request('GET', 'orders/list/user', token=self.user_token)
        
        if success and isinstance(data, list):
            self.log_test("List User Orders", True, f"Found {len(data)} orders")
        else:
            self.log_test("List User Orders", False, f"Status: {status}")

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
                "sent_amount": 4.50,
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
        
        # Test payments inbox
        success, status, data = self.make_request('GET', 'admin/payments/inbox', token=self.admin_token)
        
        if success and isinstance(data, list):
            self.log_test("Admin Payments Inbox", True, f"Found {len(data)} unmatched payments")
        else:
            self.log_test("Admin Payments Inbox", False, f"Status: {status}")
        
        # Test order retry if we have an order
        if self.test_order_id:
            success, status, data = self.make_request('POST', f'admin/orders/{self.test_order_id}/retry', token=self.admin_token)
            self.log_test("Admin Retry Order", success, f"Status: {status}")
            
            # Test manual completion
            success, status, data = self.make_request('POST', f'admin/orders/{self.test_order_id}/complete-manual', token=self.admin_token)
            self.log_test("Admin Manual Complete", success, f"Status: {status}")

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
        self.test_sms_simulation()
        self.test_admin_endpoints()
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