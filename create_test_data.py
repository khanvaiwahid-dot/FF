#!/usr/bin/env python3
"""Create test data: client with funds and Garena account"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid
from cryptography.fernet import Fernet

# Load environment
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    return cipher_suite.encrypt(data.encode()).decode()

async def create_test_data():
    """Create test client and Garena account"""
    
    print("=== Creating Test Data ===\n")
    
    # 1. Create test client with funds
    print("1. Creating test client...")
    test_user = await db.users.find_one({"username": "testclient"})
    
    if not test_user:
        user_id = str(uuid.uuid4())
        user_doc = {
            "id": user_id,
            "username": "testclient",
            "email": "testclient@example.com",
            "phone": "+1234567890",
            "password_hash": pwd_context.hash("test123"),
            "wallet_balance": 50.00,  # $50 balance
            "blocked": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
        print(f"✓ Created test client: testclient")
        print(f"  Username: testclient")
        print(f"  Password: test123")
        print(f"  Wallet Balance: $50.00")
    else:
        print(f"✓ Test client already exists: testclient")
        print(f"  Wallet Balance: ${test_user['wallet_balance']}")
    
    # 2. Create Garena account
    print("\n2. Creating Garena account...")
    garena_account = await db.garena_accounts.find_one({"email": "thenexkshetriempire01@gmail.com"})
    
    if not garena_account:
        account_id = str(uuid.uuid4())
        account_doc = {
            "id": account_id,
            "name": "Primary Garena Account",
            "email": "thenexkshetriempire01@gmail.com",
            "password": encrypt_data("Theone164@"),
            "pin": encrypt_data("164164"),
            "active": True,
            "last_used": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.garena_accounts.insert_one(account_doc)
        print(f"✓ Created Garena account")
        print(f"  Name: Primary Garena Account")
        print(f"  Email: thenexkshetriempire01@gmail.com")
        print(f"  Password: ***encrypted***")
        print(f"  PIN: ***encrypted***")
    else:
        print(f"✓ Garena account already exists")
    
    # 3. Print admin credentials
    print("\n3. Admin Credentials:")
    admin = await db.admins.find_one({"username": "admin"})
    if admin:
        print(f"  Username: admin")
        print(f"  Password: admin123")
    else:
        print(f"  ⚠ Admin not found - run init endpoint")
    
    print("\n=== Test Data Created Successfully ===")
    print("\nYou can now:")
    print("1. Login as testclient (testclient / test123) with $50 wallet")
    print("2. Login as admin (admin / admin123)")
    print("3. Admin can manage Garena accounts, products, and users")
    print("4. Automation will use the Garena account from database")

if __name__ == "__main__":
    asyncio.run(create_test_data())
