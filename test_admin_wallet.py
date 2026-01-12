#!/usr/bin/env python3

import requests
import json

class AdminWalletTester:
    def __init__(self):
        self.base_url = "https://airflow-tracker-1.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.admin_token = None
        self.testclient_token = None
        
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
            
            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return success, response.status_code, response_data
            
        except Exception as e:
            return False, 0, {"error": str(e)}
    
    def test_admin_wallet_apis(self):
        print("🔐 Testing Admin Login...")
        
        # Admin login
        login_data = {"identifier": "admin", "password": "admin123"}
        success, status, data = self.make_request('POST', 'admin/login', login_data)
        
        if success and 'token' in data:
            self.admin_token = data['token']
            print(f"✅ Admin login successful")
        else:
            print(f"❌ Admin login failed: {status} - {data}")
            return
        
        # Get users list
        success, status, users_data = self.make_request('GET', 'admin/users', token=self.admin_token)
        
        if not success:
            print(f"❌ Failed to get users: {status} - {users_data}")
            return
        
        # Find testclient
        testclient_user = None
        for user in users_data:
            if user.get('username') == 'testclient':
                testclient_user = user
                break
        
        if not testclient_user:
            print("❌ testclient user not found")
            return
        
        user_id = testclient_user['id']
        initial_balance = testclient_user.get('wallet_balance', 0)
        print(f"✅ Found testclient: {user_id}, balance: ₹{initial_balance}")
        
        # Test wallet recharge
        print("\n💰 Testing Wallet Recharge...")
        recharge_data = {
            "amount_paisa": 10000,  # ₹100
            "reason": "Test recharge for QA testing purposes"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/recharge', recharge_data, token=self.admin_token)
        
        if success:
            print(f"✅ Wallet recharge successful: {data}")
        else:
            print(f"❌ Wallet recharge failed: {status} - {data}")
            return
        
        # Test wallet redeem
        print("\n💸 Testing Wallet Redeem...")
        redeem_data = {
            "amount_paisa": 5000,  # ₹50
            "reason": "Test redemption for QA testing purposes"
        }
        
        success, status, data = self.make_request('POST', f'admin/users/{user_id}/wallet/redeem', redeem_data, token=self.admin_token)
        
        if success:
            print(f"✅ Wallet redeem successful: {data}")
        else:
            print(f"❌ Wallet redeem failed: {status} - {data}")
            return
        
        # Test action logs
        print("\n📋 Testing Action Logs...")
        success, status, data = self.make_request('GET', 'admin/action-logs', token=self.admin_token)
        
        if success:
            wallet_actions = [log for log in data if log.get('action_type') in ['wallet_recharge', 'wallet_redeem']]
            print(f"✅ Action logs retrieved: {len(data)} total, {len(wallet_actions)} wallet actions")
        else:
            print(f"❌ Action logs failed: {status} - {data}")
        
        # Test user verification
        print("\n🔍 Testing User Verification...")
        
        # Login as testclient
        login_data = {"identifier": "testclient", "password": "test123"}
        success, status, data = self.make_request('POST', 'auth/login', login_data)
        
        if success and 'token' in data:
            self.testclient_token = data['token']
            print(f"✅ testclient login successful, balance: ₹{data.get('wallet_balance', 0)}")
        else:
            print(f"❌ testclient login failed: {status} - {data}")
            return
        
        # Check wallet transactions
        success, status, data = self.make_request('GET', 'user/wallet', token=self.testclient_token)
        
        if success:
            balance = data['balance']
            transactions = data['transactions']
            admin_recharge_txs = [tx for tx in transactions if tx.get('type') == 'admin_recharge']
            admin_redeem_txs = [tx for tx in transactions if tx.get('type') == 'admin_redeem']
            
            print(f"✅ User wallet: ₹{balance}, {len(admin_recharge_txs)} recharge txs, {len(admin_redeem_txs)} redeem txs")
        else:
            print(f"❌ User wallet check failed: {status} - {data}")
        
        # Check user orders
        success, status, data = self.make_request('GET', 'user/orders', token=self.testclient_token)
        
        if success:
            admin_recharge_orders = [order for order in data if order.get('package_name') == 'Admin Wallet Recharge']
            admin_redeem_orders = [order for order in data if order.get('package_name') == 'Admin Wallet Redemption']
            
            print(f"✅ User orders: {len(admin_recharge_orders)} recharge orders, {len(admin_redeem_orders)} redeem orders")
        else:
            print(f"❌ User orders check failed: {status} - {data}")

if __name__ == "__main__":
    tester = AdminWalletTester()
    tester.test_admin_wallet_apis()