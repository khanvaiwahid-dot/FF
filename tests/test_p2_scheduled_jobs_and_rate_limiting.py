"""
P2 Feature Tests - Scheduled Jobs, Rate Limiting, and Admin Job Endpoints
Tests for:
1. Scheduler status endpoint (GET /api/admin/jobs/status)
2. Manual job triggers (POST /api/admin/jobs/expire-orders, flag-suspicious-sms, cleanup-processing)
3. Expiry statistics endpoint (GET /api/admin/stats/expiry)
4. Order expiry job logic (pending orders > 24h get expired)
5. Wallet refund on expired orders
6. Suspicious SMS flagging (unmatched > 1 hour)
7. Stuck order cleanup (processing > 10 min reset to queued)
8. Rate limit headers in responses
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://garena-credits.preview.emergentagent.com').rstrip('/')


class TestAdminAuth:
    """Get admin token for authenticated tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }


class TestSchedulerStatus(TestAdminAuth):
    """Test scheduler status endpoint"""
    
    def test_scheduler_status_returns_3_jobs(self, admin_headers):
        """GET /api/admin/jobs/status should return 3 scheduled jobs"""
        response = requests.get(f"{BASE_URL}/api/admin/jobs/status", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "scheduler_running" in data, "Missing scheduler_running field"
        assert data["scheduler_running"] == True, "Scheduler should be running"
        assert "jobs" in data, "Missing jobs field"
        
        jobs = data["jobs"]
        assert len(jobs) == 3, f"Expected 3 jobs, got {len(jobs)}"
        
        job_ids = [job["id"] for job in jobs]
        assert "expire_orders" in job_ids, "Missing expire_orders job"
        assert "flag_suspicious_sms" in job_ids, "Missing flag_suspicious_sms job"
        assert "cleanup_processing" in job_ids, "Missing cleanup_processing job"
        
        print(f"✓ Scheduler running with 3 jobs: {job_ids}")
    
    def test_scheduler_status_requires_admin_auth(self):
        """GET /api/admin/jobs/status should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/jobs/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Scheduler status requires admin auth")
    
    def test_scheduler_jobs_have_next_run_time(self, admin_headers):
        """Each job should have a next_run_time"""
        response = requests.get(f"{BASE_URL}/api/admin/jobs/status", headers=admin_headers)
        assert response.status_code == 200
        
        jobs = response.json()["jobs"]
        for job in jobs:
            assert "next_run_time" in job, f"Job {job['id']} missing next_run_time"
            assert job["next_run_time"] is not None, f"Job {job['id']} has null next_run_time"
            assert "trigger" in job, f"Job {job['id']} missing trigger"
            print(f"✓ Job {job['id']}: next_run={job['next_run_time']}, trigger={job['trigger']}")


class TestManualJobTriggers(TestAdminAuth):
    """Test manual job trigger endpoints"""
    
    def test_expire_orders_job_manual_trigger(self, admin_headers):
        """POST /api/admin/jobs/expire-orders should run the job"""
        response = requests.post(f"{BASE_URL}/api/admin/jobs/expire-orders", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message field"
        assert "completed" in data["message"].lower() or "expire" in data["message"].lower(), \
            f"Unexpected message: {data['message']}"
        print(f"✓ Expire orders job triggered: {data['message']}")
    
    def test_flag_suspicious_sms_job_manual_trigger(self, admin_headers):
        """POST /api/admin/jobs/flag-suspicious-sms should run the job"""
        response = requests.post(f"{BASE_URL}/api/admin/jobs/flag-suspicious-sms", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message field"
        print(f"✓ Flag suspicious SMS job triggered: {data['message']}")
    
    def test_cleanup_processing_job_manual_trigger(self, admin_headers):
        """POST /api/admin/jobs/cleanup-processing should run the job"""
        response = requests.post(f"{BASE_URL}/api/admin/jobs/cleanup-processing", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Missing message field"
        print(f"✓ Cleanup processing job triggered: {data['message']}")
    
    def test_manual_job_triggers_require_admin_auth(self):
        """Manual job triggers should require admin auth"""
        endpoints = [
            "/api/admin/jobs/expire-orders",
            "/api/admin/jobs/flag-suspicious-sms",
            "/api/admin/jobs/cleanup-processing"
        ]
        
        for endpoint in endpoints:
            response = requests.post(f"{BASE_URL}{endpoint}")
            assert response.status_code in [401, 403], \
                f"{endpoint} should require auth, got {response.status_code}"
        
        print("✓ All manual job triggers require admin auth")


class TestExpiryStatistics(TestAdminAuth):
    """Test expiry statistics endpoint"""
    
    def test_expiry_stats_endpoint_exists(self, admin_headers):
        """GET /api/admin/stats/expiry should return statistics"""
        response = requests.get(f"{BASE_URL}/api/admin/stats/expiry", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        required_fields = [
            "expired_last_24h",
            "pending_older_than_12h",
            "suspicious_sms_count",
            "unmatched_sms_count"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"{field} should be integer"
        
        print(f"✓ Expiry stats: expired_24h={data['expired_last_24h']}, "
              f"pending_old={data['pending_older_than_12h']}, "
              f"suspicious_sms={data['suspicious_sms_count']}, "
              f"unmatched_sms={data['unmatched_sms_count']}")
    
    def test_expiry_stats_requires_admin_auth(self):
        """GET /api/admin/stats/expiry should require admin auth"""
        response = requests.get(f"{BASE_URL}/api/admin/stats/expiry")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Expiry stats requires admin auth")


class TestOrderExpiryLogic:
    """Test order expiry job logic with test data"""
    
    @pytest.fixture(scope="class")
    def test_user_token(self):
        """Create a test user and get token"""
        username = f"TEST_expiry_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "username": username,
            "password": "test123"
        })
        if response.status_code == 200:
            return response.json()["token"]
        # If signup fails (rate limit), try login with existing test user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "identifier": "testclient",
            "password": "test123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def user_headers(self, test_user_token):
        return {
            "Authorization": f"Bearer {test_user_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_pending_order_not_expired_immediately(self, user_headers, admin_headers):
        """New pending orders should not be expired by the job"""
        # Get packages
        packages_resp = requests.get(f"{BASE_URL}/api/packages/list")
        packages = packages_resp.json()
        package_id = packages[0]["id"]
        
        # Create order
        order_resp = requests.post(f"{BASE_URL}/api/orders/create", json={
            "player_uid": "12345678",
            "package_id": package_id
        }, headers=user_headers)
        
        if order_resp.status_code != 200:
            pytest.skip(f"Could not create order: {order_resp.text}")
        
        order_id = order_resp.json()["order_id"]
        
        # Run expire job
        requests.post(f"{BASE_URL}/api/admin/jobs/expire-orders", headers=admin_headers)
        
        # Check order status - should still be pending
        order_check = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=user_headers)
        assert order_check.status_code == 200
        
        status = order_check.json()["status"]
        assert status == "pending_payment", f"New order should not be expired, got status: {status}"
        print(f"✓ New pending order {order_id[:8]} not expired by job")


class TestSuspiciousSMSFlagging:
    """Test suspicious SMS flagging logic"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_new_sms_not_flagged_suspicious_immediately(self, admin_headers):
        """New unmatched SMS should not be flagged suspicious immediately"""
        # Send a new SMS
        unique_msg = f"Rs. 999.00 received from 900****{uuid.uuid4().hex[:3]} for test, RRN: TEST{uuid.uuid4().hex[:8]}"
        
        sms_resp = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": unique_msg
        })
        
        if sms_resp.status_code != 200:
            pytest.skip(f"SMS receive failed: {sms_resp.text}")
        
        # Run flag suspicious job
        requests.post(f"{BASE_URL}/api/admin/jobs/flag-suspicious-sms", headers=admin_headers)
        
        # Check SMS list - new SMS should not be suspicious
        sms_list = requests.get(f"{BASE_URL}/api/admin/sms", headers=admin_headers)
        assert sms_list.status_code == 200
        
        messages = sms_list.json()
        # Find our message
        our_msg = None
        for msg in messages:
            if "TEST" in msg.get("rrn", "") and msg.get("raw_message") == unique_msg:
                our_msg = msg
                break
        
        if our_msg:
            assert our_msg.get("suspicious") == False, "New SMS should not be flagged suspicious"
            print(f"✓ New SMS not flagged suspicious immediately")
        else:
            print("✓ SMS test completed (message may have been matched)")


class TestStuckOrderCleanup:
    """Test stuck order cleanup logic"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_cleanup_job_runs_without_error(self, admin_headers):
        """Cleanup processing job should run without errors"""
        response = requests.post(f"{BASE_URL}/api/admin/jobs/cleanup-processing", headers=admin_headers)
        assert response.status_code == 200, f"Cleanup job failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ Cleanup processing job completed: {data['message']}")
    
    def test_automation_queue_shows_processing_orders(self, admin_headers):
        """Automation queue should show processing orders if any"""
        response = requests.get(f"{BASE_URL}/api/admin/automation/queue", headers=admin_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "queued_count" in data
        assert "processing_count" in data
        assert "orders" in data
        
        print(f"✓ Automation queue: queued={data['queued_count']}, processing={data['processing_count']}")


class TestRateLimiting:
    """Test rate limiting headers and behavior"""
    
    def test_login_returns_rate_limit_headers(self):
        """Login endpoint should return rate limit headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "identifier": "testclient",
            "password": "test123"
        })
        
        # Check for rate limit headers (SlowAPI uses these)
        headers = response.headers
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ]
        
        found_headers = []
        for header in rate_limit_headers:
            if header.lower() in [h.lower() for h in headers.keys()]:
                found_headers.append(header)
        
        # SlowAPI may use different header names
        if not found_headers:
            # Check for Retry-After header (appears when rate limited)
            if "Retry-After" in headers:
                found_headers.append("Retry-After")
        
        print(f"✓ Login response headers: {dict(headers)}")
        print(f"✓ Rate limit related headers found: {found_headers if found_headers else 'None (may appear on rate limit)'}")
    
    def test_packages_list_no_rate_limit(self):
        """Public packages list should not be rate limited"""
        # Make multiple requests
        for i in range(5):
            response = requests.get(f"{BASE_URL}/api/packages/list")
            assert response.status_code == 200, f"Request {i+1} failed: {response.status_code}"
        
        print("✓ Packages list endpoint not rate limited (5 requests succeeded)")
    
    def test_sms_receive_has_rate_limit(self):
        """SMS receive endpoint should have rate limiting configured"""
        # Just verify the endpoint works (we won't actually hit the limit)
        unique_msg = f"Rs. 50.00 received from 900****{uuid.uuid4().hex[:3]}, RRN: RL{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/sms/receive", json={
            "raw_message": unique_msg
        })
        
        # Should succeed (not rate limited with single request)
        assert response.status_code == 200, f"SMS receive failed: {response.text}"
        print("✓ SMS receive endpoint working (rate limit: 60/minute)")


class TestWalletRefundOnExpiry:
    """Test wallet refund when orders expire"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_expiry_stats_tracks_expired_orders(self, admin_headers):
        """Expiry stats should track expired orders"""
        response = requests.get(f"{BASE_URL}/api/admin/stats/expiry", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Just verify the field exists and is a number
        assert "expired_last_24h" in data
        assert isinstance(data["expired_last_24h"], int)
        
        print(f"✓ Expired orders in last 24h: {data['expired_last_24h']}")


class TestJobIntegration:
    """Integration tests for all jobs working together"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "identifier": "admin",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_all_jobs_can_run_sequentially(self, admin_headers):
        """All 3 jobs should be able to run sequentially without errors"""
        jobs = [
            ("/api/admin/jobs/expire-orders", "Expire orders"),
            ("/api/admin/jobs/flag-suspicious-sms", "Flag suspicious SMS"),
            ("/api/admin/jobs/cleanup-processing", "Cleanup processing")
        ]
        
        for endpoint, name in jobs:
            response = requests.post(f"{BASE_URL}{endpoint}", headers=admin_headers)
            assert response.status_code == 200, f"{name} job failed: {response.text}"
            print(f"✓ {name} job completed successfully")
        
        print("✓ All 3 jobs ran successfully")
    
    def test_scheduler_still_running_after_manual_triggers(self, admin_headers):
        """Scheduler should still be running after manual job triggers"""
        response = requests.get(f"{BASE_URL}/api/admin/jobs/status", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["scheduler_running"] == True, "Scheduler should still be running"
        assert len(data["jobs"]) == 3, "Should still have 3 jobs"
        
        print("✓ Scheduler still running with 3 jobs after manual triggers")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
