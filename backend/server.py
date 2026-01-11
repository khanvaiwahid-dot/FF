from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# Order states
ORDER_STATES = [
    "pending_payment", "paid", "queued", "processing", 
    "wallet_partial_paid", "wallet_fully_paid", "success", 
    "failed", "manual_review", "suspicious", "duplicate_payment", "expired"
]

AUTOMATION_STATES = [
    "INIT", "OPEN_SITE", "INPUT_UID", "SELECT_SERVER", 
    "SELECT_PACKAGE", "CONFIRM_PURCHASE", "VERIFY_SUCCESS", "DONE", "FAILED"
]

# ===== Models =====
class SignupRequest(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    identifier: str  # username, email or phone
    password: str

class ResetPasswordRequest(BaseModel):
    identifier: str
    new_password: str

class TokenResponse(BaseModel):
    token: str
    user_type: str
    username: str
    wallet_balance: Optional[float] = None

class UserProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    wallet_balance: float
    created_at: str

class Package(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    diamonds: int
    price: float
    active: bool

class CreateOrderRequest(BaseModel):
    player_uid: str
    package_id: str

class PaymentVerificationRequest(BaseModel):
    order_id: str
    sent_amount: float
    last_3_digits: str
    payment_method: str
    payment_screenshot: Optional[str] = None
    remark: Optional[str] = None

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    username: str
    player_uid: str
    server: Optional[str] = None
    package_name: str
    diamonds: int
    amount: float
    wallet_used: float
    payment_amount: float
    payment_last3digits: Optional[str] = None
    payment_method: Optional[str] = None
    payment_remark: Optional[str] = None
    payment_screenshot: Optional[str] = None
    payment_rrn: Optional[str] = None
    raw_message: Optional[str] = None
    status: str
    automation_state: Optional[str] = None
    retry_count: int
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

class SMSMessage(BaseModel):
    raw_message: str
    amount: Optional[float] = None
    last3digits: Optional[str] = None
    rrn: Optional[str] = None
    method: Optional[str] = None
    remark: Optional[str] = None

class WalletTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    type: str
    amount: float
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    balance_before: float
    balance_after: float
    created_at: str

class DashboardStats(BaseModel):
    total_sales: float
    total_orders: int
    success_orders: int
    failed_orders: int
    suspicious_orders: int
    duplicate_orders: int
    pending_orders: int
    total_wallet_balance: float

# ===== Utility Functions =====
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("type")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "type": user_type}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_data = await get_current_user(credentials)
    if user_data["type"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_data

def parse_sms_message(raw_message: str) -> dict:
    """Parse SMS payment message to extract details"""
    import re
    result = {
        "amount": None,
        "last3digits": None,
        "rrn": None,
        "method": None,
        "remark": None
    }
    
    # Extract amount (Rs 125.00 or Rs 125)
    amount_match = re.search(r'Rs\.?\s*([0-9,]+\.?[0-9]*)', raw_message, re.IGNORECASE)
    if amount_match:
        result["amount"] = float(amount_match.group(1).replace(',', ''))
    
    # Extract last 3 digits (900****910)
    phone_match = re.search(r'\d+\*+([0-9]{3})', raw_message)
    if phone_match:
        result["last3digits"] = phone_match.group(1)
    
    # Extract RRN
    rrn_match = re.search(r'RRN\s*[:\-]?\s*([A-Za-z0-9]+)', raw_message, re.IGNORECASE)
    if rrn_match:
        result["rrn"] = rrn_match.group(1)
    
    # Extract method (after last comma)
    parts = raw_message.split(',')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        if last_part and '/' in last_part:
            method_parts = last_part.split('/')
            if len(method_parts) >= 2:
                result["method"] = method_parts[-1].strip()
                result["remark"] = method_parts[0].strip()
    
    return result

# ===== Authentication Endpoints =====
@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    # Check if username exists
    existing = await db.users.find_one({"username": request.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if request.email:
        existing_email = await db.users.find_one({"email": request.email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if request.phone:
        existing_phone = await db.users.find_one({"phone": request.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "phone": request.phone,
        "password_hash": hash_password(request.password),
        "wallet_balance": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id, "type": "user", "username": request.username})
    
    return TokenResponse(
        token=token,
        user_type="user",
        username=request.username,
        wallet_balance=0.0
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = await db.users.find_one({
        "$or": [
            {"username": request.identifier},
            {"email": request.identifier},
            {"phone": request.identifier}
        ]
    }, {"_id": 0})
    
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["id"], "type": "user", "username": user["username"]})
    
    return TokenResponse(
        token=token,
        user_type="user",
        username=user["username"],
        wallet_balance=user["wallet_balance"]
    )

@api_router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = await db.users.find_one({
        "$or": [
            {"username": request.identifier},
            {"email": request.identifier},
            {"phone": request.identifier}
        ]
    })
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(request.new_password)}}
    )
    
    return {"message": "Password reset successful"}

# ===== Admin Auth Endpoints =====
@api_router.post("/admin/login", response_model=TokenResponse)
async def admin_login(request: LoginRequest):
    admin = await db.admins.find_one({"username": request.identifier}, {"_id": 0})
    
    if not admin or not verify_password(request.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    token = create_access_token({"sub": admin["id"], "type": "admin", "username": admin["username"]})
    
    return TokenResponse(
        token=token,
        user_type="admin",
        username=admin["username"]
    )

@api_router.post("/admin/reset-password")
async def admin_reset_password(request: ResetPasswordRequest, user_data: dict = Depends(get_current_admin)):
    admin = await db.admins.find_one({"id": user_data["user_id"]})
    
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    await db.admins.update_one(
        {"id": admin["id"]},
        {"$set": {"password_hash": hash_password(request.new_password)}}
    )
    
    return {"message": "Admin password reset successful"}

# ===== User Endpoints =====
@api_router.get("/user/profile", response_model=UserProfile)
async def get_profile(user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfile(**user)

@api_router.get("/user/wallet")
async def get_wallet(user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0, "wallet_balance": 1})
    transactions = await db.wallet_transactions.find(
        {"user_id": user_data["user_id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    return {
        "balance": user["wallet_balance"],
        "transactions": transactions
    }

# ===== Package Endpoints =====
@api_router.get("/packages/list", response_model=List[Package])
async def list_packages():
    packages = await db.packages.find({"active": True}, {"_id": 0}).to_list(100)
    return packages

# ===== Order Endpoints =====
@api_router.post("/orders/create")
async def create_order(request: CreateOrderRequest, user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    package = await db.packages.find_one({"id": request.package_id}, {"_id": 0})
    if not package or not package["active"]:
        raise HTTPException(status_code=404, detail="Package not found")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0})
    
    order_id = str(uuid.uuid4())
    wallet_used = 0.0
    payment_amount = package["price"]
    status = "pending_payment"
    
    # Check if wallet can cover partially or fully
    if user["wallet_balance"] > 0:
        if user["wallet_balance"] >= package["price"]:
            wallet_used = package["price"]
            payment_amount = 0.0
            status = "wallet_fully_paid"
        else:
            wallet_used = user["wallet_balance"]
            payment_amount = package["price"] - wallet_used
            status = "wallet_partial_paid"
    
    order_doc = {
        "id": order_id,
        "user_id": user_data["user_id"],
        "username": user["username"],
        "player_uid": request.player_uid,
        "server": "Bangladesh",
        "package_name": package["name"],
        "diamonds": package["diamonds"],
        "amount": package["price"],
        "wallet_used": wallet_used,
        "payment_amount": payment_amount,
        "payment_last3digits": None,
        "payment_method": None,
        "payment_remark": None,
        "payment_screenshot": None,
        "payment_rrn": None,
        "raw_message": None,
        "status": status,
        "automation_state": None,
        "retry_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
    
    await db.orders.insert_one(order_doc)
    
    # Deduct wallet if used
    if wallet_used > 0:
        new_balance = user["wallet_balance"] - wallet_used
        await db.users.update_one(
            {"id": user_data["user_id"]},
            {"$set": {"wallet_balance": new_balance}}
        )
        
        # Create wallet transaction
        transaction_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_data["user_id"],
            "type": "order_payment",
            "amount": -wallet_used,
            "order_id": order_id,
            "payment_id": None,
            "balance_before": user["wallet_balance"],
            "balance_after": new_balance,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.wallet_transactions.insert_one(transaction_doc)
    
    return {"order_id": order_id, "status": status, "payment_amount": payment_amount}

@api_router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user_data: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Users can only see their own orders
    if user_data["type"] == "user" and order["user_id"] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return Order(**order)

@api_router.get("/orders/list/user")
async def list_user_orders(user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    orders = await db.orders.find(
        {"user_id": user_data["user_id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return orders

@api_router.post("/orders/verify-payment")
async def verify_payment(request: PaymentVerificationRequest, user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    order = await db.orders.find_one({"id": request.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["user_id"] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update order with payment details
    await db.orders.update_one(
        {"id": request.order_id},
        {"$set": {
            "payment_last3digits": request.last_3_digits,
            "payment_method": request.payment_method,
            "payment_remark": request.remark,
            "payment_screenshot": request.payment_screenshot,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Try to match with SMS messages
    matching_sms = await db.sms_messages.find_one({
        "amount": request.sent_amount,
        "last3digits": request.last_3_digits,
        "used": False
    }, {"_id": 0})
    
    if matching_sms:
        # Check if RRN is already used
        existing_order = await db.orders.find_one({"payment_rrn": matching_sms["rrn"]})
        if existing_order and existing_order["id"] != request.order_id:
            await db.orders.update_one(
                {"id": request.order_id},
                {"$set": {"status": "duplicate_payment", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"message": "This payment has already been used for another order", "status": "duplicate_payment"}
        
        # Mark SMS as used and update order
        await db.sms_messages.update_one(
            {"id": matching_sms["id"]},
            {"$set": {"used": True, "matched_order_id": request.order_id}}
        )
        
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {
                "payment_rrn": matching_sms["rrn"],
                "raw_message": matching_sms["raw_message"],
                "status": "paid",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Add to automation queue
        await add_to_queue(request.order_id)
        
        return {"message": "Payment verified successfully! Your order is being processed.", "status": "paid"}
    else:
        # Payment not found - mark as pending manual review
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {"status": "manual_review", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "We're verifying your payment. This usually takes a few minutes.", "status": "manual_review"}

# ===== SMS Webhook Endpoint =====
@api_router.post("/sms/receive")
async def receive_sms(message: SMSMessage):
    """Receive SMS messages from phone/emulator app"""
    parsed = parse_sms_message(message.raw_message)
    
    sms_doc = {
        "id": str(uuid.uuid4()),
        "raw_message": message.raw_message,
        "amount": parsed["amount"],
        "last3digits": parsed["last3digits"],
        "rrn": parsed["rrn"],
        "method": parsed["method"],
        "remark": parsed["remark"],
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "used": False,
        "matched_order_id": None
    }
    
    await db.sms_messages.insert_one(sms_doc)
    
    # Try to match with pending orders
    if parsed["amount"] and parsed["last3digits"]:
        pending_orders = await db.orders.find({
            "status": {"$in": ["pending_payment", "wallet_partial_paid", "manual_review"]},
            "payment_amount": parsed["amount"],
            "payment_last3digits": parsed["last3digits"]
        }, {"_id": 0}).to_list(10)
        
        for order in pending_orders:
            # Check if RRN already used
            if parsed["rrn"]:
                existing = await db.orders.find_one({"payment_rrn": parsed["rrn"]})
                if existing:
                    await db.orders.update_one(
                        {"id": order["id"]},
                        {"$set": {"status": "duplicate_payment", "updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    continue
            
            # Update order
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {
                    "payment_rrn": parsed["rrn"],
                    "raw_message": message.raw_message,
                    "status": "paid",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            await db.sms_messages.update_one(
                {"id": sms_doc["id"]},
                {"$set": {"used": True, "matched_order_id": order["id"]}}
            )
            
            await add_to_queue(order["id"])
            break
    
    return {"message": "SMS received and processed"}

# ===== Queue & Automation =====
queue_lock = asyncio.Lock()
processing_orders = set()

async def add_to_queue(order_id: str):
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": "queued", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    # In production, use a proper queue like Redis/RabbitMQ
    asyncio.create_task(process_order(order_id))

async def process_order(order_id: str):
    async with queue_lock:
        if order_id in processing_orders:
            return
        processing_orders.add(order_id)
    
    try:
        order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        if not order:
            return
        
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {"status": "processing", "automation_state": "INIT", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Run automation
        success = await run_automation(order)
        
        if success:
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {
                    "status": "success",
                    "automation_state": "DONE",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            retry_count = order.get("retry_count", 0) + 1
            if retry_count >= 3:
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "status": "manual_review",
                        "automation_state": "FAILED",
                        "retry_count": retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            else:
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "status": "queued",
                        "retry_count": retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                await asyncio.sleep(30)  # Wait before retry
                await process_order(order_id)
    finally:
        processing_orders.discard(order_id)

async def run_automation(order: dict) -> bool:
    """Run Playwright automation for Garena top-up with stealth mode"""
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
    import random
    
    GARENA_EMAIL = "thenexkshetriempire01@gmail.com"
    GARENA_PASSWORD = "Theone164@"
    SECURITY_PIN = "164164"
    
    async def human_delay(min_ms=500, max_ms=2000):
        """Add random human-like delay"""
        await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))
    
    async def human_type(element, text):
        """Type text with human-like delays"""
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
    
    try:
        async with async_playwright() as p:
            # Launch with stealth settings
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Create context with realistic settings
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Asia/Kuala_Lumpur'
            )
            
            page = await context.new_page()
            
            # Apply stealth mode
            await stealth_async(page)
            
            logging.info(f"Starting stealth automation for order {order['id']}")
            
            # STEP 1: Open Garena Shop
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "OPEN_SITE"}}
            )
            logging.info("Step 1: Opening Garena shop")
            await page.goto("https://shop.garena.my/", wait_until="domcontentloaded", timeout=30000)
            await human_delay(2000, 4000)
            
            # STEP 2: Select Free Fire
            logging.info("Step 2: Selecting Free Fire")
            try:
                freefire_selector = await page.wait_for_selector('text="Free Fire"', timeout=15000)
                await human_delay(500, 1500)
                await freefire_selector.click()
                await human_delay(2000, 4000)
            except Exception as e:
                logging.error(f"Could not find Free Fire: {e}")
                await browser.close()
                return False
            
            # STEP 3: Insert Player UID
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "INPUT_UID"}}
            )
            logging.info(f"Step 3: Inserting Player UID: {order['player_uid']}")
            try:
                uid_input = await page.wait_for_selector('input[placeholder*="player ID"]', timeout=15000)
                await human_delay(500, 1000)
                await human_type(uid_input, order["player_uid"])
                await human_delay(1000, 2000)
            except Exception as e:
                logging.error(f"Could not find UID input: {e}")
                await browser.close()
                return False
            
            # STEP 4: Click Redeem Tab
            logging.info("Step 4: Clicking Redeem tab")
            try:
                redeem_btn = await page.wait_for_selector('button:has-text("Redeem")', timeout=15000)
                await human_delay(500, 1500)
                await redeem_btn.click()
                await human_delay(2000, 3000)
            except Exception as e:
                logging.error(f"Could not click Redeem: {e}")
                await browser.close()
                return False
            
            # STEP 5: Click Login Button
            logging.info("Step 5: Clicking Login button")
            try:
                login_btn = await page.wait_for_selector('button:has-text("Login")', timeout=15000)
                await human_delay(500, 1500)
                await login_btn.click()
                await human_delay(3000, 5000)
                
                # Check if email/password login modal appears
                email_input = await page.query_selector('input[type="email"], input[placeholder*="email" i]')
                if email_input:
                    logging.info("Login modal appeared - entering credentials")
                    await human_type(email_input, GARENA_EMAIL)
                    await human_delay(500, 1000)
                    
                    password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
                    await human_type(password_input, GARENA_PASSWORD)
                    await human_delay(500, 1000)
                    
                    login_submit = await page.wait_for_selector('button[type="submit"], button:has-text("Login")', timeout=10000)
                    await login_submit.click()
                    await human_delay(4000, 6000)
                    logging.info("Login completed")
                else:
                    logging.info("Already logged in")
            except Exception as e:
                logging.warning(f"Login step issue: {e}")
            
            # STEP 6: Select Diamond Amount
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "SELECT_PACKAGE"}}
            )
            logging.info(f"Step 6: Selecting {order['diamonds']} diamonds")
            try:
                # Scroll to see options
                await page.evaluate('window.scrollTo(0, 600)')
                await human_delay(1000, 2000)
                
                # Map our packages to Garena's available options
                garena_amounts = {
                    100: "115",  # Closest to 100
                    310: "240",  # Closest to 310
                    520: "610",  # Closest to 520
                    1060: "1,240",  # Closest to 1060
                    2180: "2,530",  # Closest to 2180
                    5600: "2,530"   # Use highest available
                }
                
                target_amount = garena_amounts.get(order["diamonds"], str(order["diamonds"]))
                
                diamond_selector = await page.wait_for_selector(
                    f'text="{target_amount} Diamond"',
                    timeout=15000
                )
                await human_delay(500, 1500)
                await diamond_selector.click()
                await human_delay(2000, 3000)
                logging.info(f"Selected {target_amount} Diamond package")
            except Exception as e:
                logging.error(f"Could not select diamond package: {e}")
                await browser.close()
                return False
            
            # STEP 7: Click Proceed to Payment
            logging.info("Step 7: Clicking Proceed to Payment")
            try:
                proceed_btn = await page.wait_for_selector('button:has-text("Proceed to Payment")', timeout=15000)
                await human_delay(1000, 2000)
                await proceed_btn.click()
                await human_delay(3000, 5000)
            except Exception as e:
                logging.error(f"Could not click Proceed to Payment: {e}")
                await browser.close()
                return False
            
            # STEP 8: Select Wallet Payment Method
            logging.info("Step 8: Looking for Wallet payment option")
            try:
                await page.evaluate('window.scrollTo(0, 400)')
                await human_delay(1000, 2000)
                
                # Try multiple selectors for Wallet
                wallet_found = False
                wallet_selectors = [
                    'text="Wallet"',
                    'text="wallet"',
                    'text="Shell"',
                    'button:has-text("Wallet")',
                    'div:has-text("Wallet")'
                ]
                
                for selector in wallet_selectors:
                    wallet_elem = await page.query_selector(selector)
                    if wallet_elem:
                        logging.info(f"Found Wallet with selector: {selector}")
                        await human_delay(500, 1500)
                        await wallet_elem.click()
                        await human_delay(2000, 3000)
                        wallet_found = True
                        break
                
                if not wallet_found:
                    logging.error("Wallet option not found")
                    await browser.close()
                    return False
                    
            except Exception as e:
                logging.error(f"Could not select Wallet: {e}")
                await browser.close()
                return False
            
            # STEP 9: Select UP Points
            logging.info("Step 9: Looking for UP Points")
            try:
                await human_delay(1000, 2000)
                
                up_points_selectors = [
                    'text="UP Points"',
                    'text="UP"',
                    'button:has-text("UP Points")',
                    'div:has-text("UP Points")'
                ]
                
                up_found = False
                for selector in up_points_selectors:
                    up_elem = await page.query_selector(selector)
                    if up_elem:
                        logging.info(f"Found UP Points with selector: {selector}")
                        await human_delay(500, 1500)
                        await up_elem.click()
                        await human_delay(2000, 3000)
                        up_found = True
                        break
                
                if not up_found:
                    logging.warning("UP Points not found, continuing...")
                    
            except Exception as e:
                logging.warning(f"UP Points selection issue: {e}")
            
            # STEP 10: Enter Security PIN
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "CONFIRM_PURCHASE"}}
            )
            logging.info("Step 10: Looking for Security PIN input")
            try:
                pin_input = await page.wait_for_selector(
                    'input[type="password"], input[placeholder*="PIN" i], input[name*="pin" i]',
                    timeout=15000
                )
                await human_delay(500, 1000)
                await human_type(pin_input, SECURITY_PIN)
                await human_delay(1000, 2000)
                logging.info("Security PIN entered")
            except Exception as e:
                logging.warning(f"PIN input not found or not required: {e}")
            
            # STEP 11: Click Confirm/Purchase Button
            logging.info("Step 11: Confirming purchase")
            try:
                confirm_selectors = [
                    'button:has-text("Confirm")',
                    'button:has-text("Purchase")',
                    'button:has-text("Pay Now")',
                    'button:has-text("Buy Now")',
                    'button[type="submit"]'
                ]
                
                confirm_btn = None
                for selector in confirm_selectors:
                    confirm_btn = await page.query_selector(selector)
                    if confirm_btn:
                        logging.info(f"Found confirm button: {selector}")
                        break
                
                if confirm_btn:
                    await human_delay(1000, 2000)
                    await confirm_btn.click()
                    await human_delay(5000, 8000)
                else:
                    logging.error("Confirm button not found")
                    await browser.close()
                    return False
            except Exception as e:
                logging.error(f"Could not confirm purchase: {e}")
                await browser.close()
                return False
            
            # STEP 12: Verify Success
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "VERIFY_SUCCESS"}}
            )
            logging.info("Step 12: Verifying transaction success")
            try:
                success_indicators = [
                    'text=/success/i',
                    'text=/complete/i',
                    'text=/successful/i',
                    '[class*="success"]',
                    'text=/transaction.*complete/i'
                ]
                
                success_found = False
                for selector in success_indicators:
                    success_elem = await page.query_selector(selector)
                    if success_elem:
                        logging.info(f"Success indicator found: {selector}")
                        success_found = True
                        break
                
                if success_found:
                    logging.info(f"Transaction successful for order {order['id']}")
                    await browser.close()
                    return True
                else:
                    # Wait a bit more and check again
                    await asyncio.sleep(5)
                    page_text = await page.inner_text('body')
                    if any(word in page_text.lower() for word in ['success', 'complete', 'successful']):
                        logging.info(f"Transaction successful for order {order['id']}")
                        await browser.close()
                        return True
                    else:
                        logging.error("Success indicator not found")
                        await browser.close()
                        return False
                        
            except Exception as e:
                logging.error(f"Could not verify success: {e}")
                await browser.close()
                return False
                
    except Exception as e:
        logging.error(f"Automation error for order {order['id']}: {str(e)}")
        return False
            
            # STEP 1: Open Garena Shop
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "OPEN_SITE"}}
            )
            logging.info("Step 1: Opening Garena shop")
            await page.goto("https://shop.garena.my/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # STEP 2: Select FreeFire
            logging.info("Step 2: Selecting FreeFire")
            try:
                # Look for FreeFire game option
                freefire_selector = await page.wait_for_selector('text=/free.*fire/i', timeout=10000)
                await freefire_selector.click()
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Could not find FreeFire option: {e}")
                await browser.close()
                return False
            
            # STEP 3: Insert Player ID (UID)
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "INPUT_UID"}}
            )
            logging.info(f"Step 3: Inserting Player UID: {order['player_uid']}")
            try:
                # Find UID input field
                uid_input = await page.wait_for_selector('input[placeholder*="ID" i], input[placeholder*="UID" i], input[name*="playerId" i]', timeout=10000)
                await uid_input.fill(order["player_uid"])
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Could not find UID input: {e}")
                await browser.close()
                return False
            
            # STEP 4: Select Redeem
            logging.info("Step 4: Selecting Redeem option")
            try:
                redeem_option = await page.wait_for_selector('text=/redeem/i, button:has-text("Redeem"), [data-testid*="redeem"]', timeout=10000)
                await redeem_option.click()
                await asyncio.sleep(2)
            except Exception as e:
                logging.warning(f"Redeem option not found or not needed: {e}")
            
            # STEP 5: Login (if not already logged in)
            logging.info("Step 5: Checking login status")
            try:
                # Check if login button exists
                login_button = await page.query_selector('button:has-text("Login"), button:has-text("Log In"), a:has-text("Login")')
                if login_button:
                    logging.info("Not logged in, proceeding to login")
                    await login_button.click()
                    await asyncio.sleep(2)
                    
                    # Enter email
                    email_input = await page.wait_for_selector('input[type="email"], input[name*="email" i], input[placeholder*="email" i]', timeout=10000)
                    await email_input.fill(GARENA_EMAIL)
                    await asyncio.sleep(1)
                    
                    # Enter password
                    password_input = await page.wait_for_selector('input[type="password"], input[name*="password" i]', timeout=10000)
                    await password_input.fill(GARENA_PASSWORD)
                    await asyncio.sleep(1)
                    
                    # Click login submit
                    login_submit = await page.wait_for_selector('button[type="submit"], button:has-text("Login"), button:has-text("Sign In")', timeout=10000)
                    await login_submit.click()
                    await asyncio.sleep(3)
                else:
                    logging.info("Already logged in")
            except Exception as e:
                logging.warning(f"Login step issue: {e}")
            
            # STEP 6: Proceed to Payment
            logging.info("Step 6: Proceeding to payment")
            try:
                proceed_button = await page.wait_for_selector('button:has-text("Proceed"), button:has-text("Continue"), button:has-text("Next")', timeout=10000)
                await proceed_button.click()
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Could not proceed to payment: {e}")
                await browser.close()
                return False
            
            # STEP 7: Select Amount (Diamond Package)
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "SELECT_PACKAGE"}}
            )
            logging.info(f"Step 7: Selecting diamond amount: {order['diamonds']}")
            try:
                # Try to find package by diamonds count
                package_selector = await page.wait_for_selector(
                    f'text="{order["diamonds"]}", button:has-text("{order["diamonds"]}"), div:has-text("{order["diamonds"]}")',
                    timeout=10000
                )
                await package_selector.click()
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Could not select diamond package: {e}")
                await browser.close()
                return False
            
            # STEP 8: Select Wallet
            logging.info("Step 8: Selecting Wallet payment method")
            try:
                wallet_option = await page.wait_for_selector('text=/wallet/i, button:has-text("Wallet"), [data-payment="wallet"]', timeout=10000)
                await wallet_option.click()
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Could not select Wallet: {e}")
                await browser.close()
                return False
            
            # STEP 9: Select UP Points
            logging.info("Step 9: Selecting UP Points")
            try:
                up_points_option = await page.wait_for_selector('text=/UP Points/i, button:has-text("UP Points"), [data-payment*="up" i]', timeout=10000)
                await up_points_option.click()
                await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Could not select UP Points: {e}")
                await browser.close()
                return False
            
            # STEP 10: Login with credentials if prompted
            logging.info("Step 10: Checking if login required for payment")
            try:
                # Check if login prompt appears
                login_id_input = await page.query_selector('input[placeholder*="ID" i], input[placeholder*="username" i], input[name*="username" i]')
                if login_id_input:
                    logging.info("Login required, entering credentials")
                    await login_id_input.fill(GARENA_EMAIL)
                    await asyncio.sleep(1)
                    
                    password_input = await page.wait_for_selector('input[type="password"], input[name*="password" i]', timeout=5000)
                    await password_input.fill(GARENA_PASSWORD)
                    await asyncio.sleep(1)
                    
                    login_btn = await page.wait_for_selector('button[type="submit"], button:has-text("Login")', timeout=5000)
                    await login_btn.click()
                    await asyncio.sleep(2)
            except Exception as e:
                logging.info(f"No additional login required: {e}")
            
            # STEP 11: Insert Security PIN
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "CONFIRM_PURCHASE"}}
            )
            logging.info("Step 11: Entering security PIN")
            try:
                # Look for PIN input
                pin_input = await page.wait_for_selector('input[type="password"], input[placeholder*="PIN" i], input[name*="pin" i]', timeout=10000)
                await pin_input.fill(SECURITY_PIN)
                await asyncio.sleep(1)
            except Exception as e:
                logging.warning(f"PIN input not found or not required: {e}")
            
            # STEP 12: Confirm Purchase
            logging.info("Step 12: Confirming purchase")
            try:
                confirm_button = await page.wait_for_selector(
                    'button:has-text("Confirm"), button:has-text("Purchase"), button:has-text("Pay Now"), button[type="submit"]',
                    timeout=10000
                )
                await confirm_button.click()
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Could not confirm purchase: {e}")
                await browser.close()
                return False
            
            # STEP 13: Verify Success
            await db.orders.update_one(
                {"id": order["id"]},
                {"$set": {"automation_state": "VERIFY_SUCCESS"}}
            )
            logging.info("Step 13: Verifying transaction success")
            try:
                # Look for success indicators
                success_indicator = await page.wait_for_selector(
                    'text=/success/i, text=/complete/i, text=/successful/i, [class*="success"], .success-message',
                    timeout=15000
                )
                
                if success_indicator:
                    logging.info(f"Transaction successful for order {order['id']}")
                    await browser.close()
                    return True
                else:
                    logging.error("Success indicator not found")
                    await browser.close()
                    return False
            except Exception as e:
                logging.error(f"Could not verify success: {e}")
                await browser.close()
                return False
                
    except Exception as e:
        logging.error(f"Automation error for order {order['id']}: {str(e)}")
        return False

# ===== Admin Endpoints =====
@api_router.get("/admin/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(user_data: dict = Depends(get_current_admin)):
    total_orders = await db.orders.count_documents({})
    success_orders = await db.orders.count_documents({"status": "success"})
    failed_orders = await db.orders.count_documents({"status": "failed"})
    suspicious_orders = await db.orders.count_documents({"status": "suspicious"})
    duplicate_orders = await db.orders.count_documents({"status": "duplicate_payment"})
    pending_orders = await db.orders.count_documents({"status": {"$in": ["pending_payment", "queued", "processing"]}})
    
    # Calculate total sales
    pipeline = [
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    sales_result = await db.orders.aggregate(pipeline).to_list(1)
    total_sales = sales_result[0]["total"] if sales_result else 0.0
    
    # Calculate total wallet balance
    wallet_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$wallet_balance"}}}
    ]
    wallet_result = await db.users.aggregate(wallet_pipeline).to_list(1)
    total_wallet_balance = wallet_result[0]["total"] if wallet_result else 0.0
    
    return DashboardStats(
        total_sales=total_sales,
        total_orders=total_orders,
        success_orders=success_orders,
        failed_orders=failed_orders,
        suspicious_orders=suspicious_orders,
        duplicate_orders=duplicate_orders,
        pending_orders=pending_orders,
        total_wallet_balance=total_wallet_balance
    )

@api_router.get("/admin/orders")
async def admin_list_orders(status: Optional[str] = None, user_data: dict = Depends(get_current_admin)):
    query = {}
    if status:
        query["status"] = status
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return orders

@api_router.post("/admin/orders/{order_id}/retry")
async def admin_retry_order(order_id: str, user_data: dict = Depends(get_current_admin)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": "queued", "retry_count": 0, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log admin action
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "retry_order",
        "target_id": order_id,
        "details": f"Retried order {order_id}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await add_to_queue(order_id)
    
    return {"message": "Order added to queue for retry"}

@api_router.post("/admin/orders/{order_id}/complete-manual")
async def admin_complete_order(order_id: str, user_data: dict = Depends(get_current_admin)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "success",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log admin action
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "manual_complete",
        "target_id": order_id,
        "details": f"Manually completed order {order_id}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Order marked as success"}

@api_router.get("/admin/payments/inbox")
async def admin_payments_inbox(user_data: dict = Depends(get_current_admin)):
    # Get unmatched SMS messages
    unmatched = await db.sms_messages.find({"used": False}, {"_id": 0}).sort("parsed_at", -1).limit(50).to_list(50)
    return unmatched

@api_router.get("/admin/action-logs")
async def admin_action_logs(user_data: dict = Depends(get_current_admin)):
    logs = await db.admin_actions.find({}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return logs

# ===== Initialize Data =====
@api_router.post("/admin/init")
async def initialize_data():
    """Initialize default packages and admin account"""
    # Check if already initialized
    existing_packages = await db.packages.count_documents({})
    if existing_packages > 0:
        return {"message": "Already initialized"}
    
    # Create default packages
    packages = [
        {"id": str(uuid.uuid4()), "name": "100 Diamonds", "diamonds": 100, "price": 1.5, "active": True},
        {"id": str(uuid.uuid4()), "name": "310 Diamonds", "diamonds": 310, "price": 4.5, "active": True},
        {"id": str(uuid.uuid4()), "name": "520 Diamonds", "diamonds": 520, "price": 7.5, "active": True},
        {"id": str(uuid.uuid4()), "name": "1060 Diamonds", "diamonds": 1060, "price": 15.0, "active": True},
        {"id": str(uuid.uuid4()), "name": "2180 Diamonds", "diamonds": 2180, "price": 30.0, "active": True},
        {"id": str(uuid.uuid4()), "name": "5600 Diamonds", "diamonds": 5600, "price": 75.0, "active": True}
    ]
    await db.packages.insert_many(packages)
    
    # Create default admin
    admin_exists = await db.admins.count_documents({})
    if admin_exists == 0:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "username": "admin",
            "email": "admin@diamondstore.com",
            "password_hash": hash_password("admin123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.admins.insert_one(admin_doc)
    
    return {"message": "Initialization complete. Admin username: admin, password: admin123"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()