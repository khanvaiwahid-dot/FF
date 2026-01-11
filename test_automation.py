#!/usr/bin/env python3
"""
Test script for Garena automation
Creates a test order and triggers the automation
"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def test_automation():
    """Test the Garena automation with a sample order"""
    
    # Find a test order in 'paid' status
    test_order = await db.orders.find_one({"status": "paid"}, {"_id": 0})
    
    if not test_order:
        print("No paid orders found. Creating a test order...")
        
        # Get a package
        package = await db.packages.find_one({"diamonds": 100}, {"_id": 0})
        if not package:
            print("No packages found. Please initialize the database first.")
            return
        
        # Create test order
        from datetime import datetime, timezone
        import uuid
        
        order_id = str(uuid.uuid4())
        test_order = {
            "id": order_id,
            "user_id": "test-user",
            "username": "test_user",
            "player_uid": "1234567890",  # Replace with real UID for testing
            "server": "Bangladesh",
            "package_name": package["name"],
            "diamonds": package["diamonds"],
            "amount": package["price"],
            "wallet_used": 0,
            "payment_amount": package["price"],
            "payment_last3digits": "910",
            "payment_method": "FonePay",
            "payment_remark": "test",
            "payment_screenshot": None,
            "payment_rrn": f"TEST{uuid.uuid4().hex[:8]}",
            "raw_message": "Test order",
            "status": "paid",
            "automation_state": None,
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None
        }
        
        await db.orders.insert_one(test_order)
        print(f"Test order created: {order_id}")
    else:
        print(f"Using existing order: {test_order['id']}")
    
    print("\n=== Starting Garena Automation Test ===")
    print(f"Order ID: {test_order['id']}")
    print(f"Player UID: {test_order['player_uid']}")
    print(f"Diamonds: {test_order['diamonds']}")
    print(f"Package: {test_order['package_name']}")
    print("\nNOTE: Please ensure you have a valid Free Fire Player UID for testing!")
    print("The browser will open in headed mode so you can see the automation.")
    print("\nPress Ctrl+C to cancel, or wait 10 seconds to start...")
    
    try:
        await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        return
    
    # Import and run automation
    from server import run_automation
    
    print("\n=== Running Automation ===")
    success = await run_automation(test_order)
    
    if success:
        print("\n✓ Automation completed successfully!")
        print(f"Order {test_order['id']} should be marked as 'success'")
        
        # Check order status
        updated_order = await db.orders.find_one({"id": test_order["id"]}, {"_id": 0})
        print(f"Final status: {updated_order['status']}")
        print(f"Automation state: {updated_order['automation_state']}")
    else:
        print("\n✗ Automation failed!")
        print("Check the logs for details.")
        
        # Check order status
        updated_order = await db.orders.find_one({"id": test_order["id"]}, {"_id": 0})
        print(f"Final status: {updated_order['status']}")
        print(f"Automation state: {updated_order['automation_state']}")

if __name__ == "__main__":
    asyncio.run(test_automation())
