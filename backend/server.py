"""
Nex-Store Backend Server
Free Fire Diamond Top-Up Platform with Wallet + SMS Payment Verification
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import math
import hashlib
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncio
from contextlib import asynccontextmanager

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Background scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Background scheduler for periodic tasks
scheduler = AsyncIOScheduler()

# ===== SCHEDULED JOBS =====

async def expire_old_orders():
    """
    Expire orders that have been pending_payment for more than 24 hours
    Runs every hour
    """
    try:
        expiry_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        expiry_threshold_iso = expiry_threshold.isoformat()
        
        # Find pending orders older than 24 hours
        result = await db.orders.update_many(
            {
                "status": "pending_payment",
                "created_at": {"$lt": expiry_threshold_iso}
            },
            {
                "$set": {
                    "status": "expired",
                    "expired_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Expired {result.modified_count} orders older than 24 hours")
            
            # Refund wallet amounts for expired orders
            expired_orders = await db.orders.find(
                {
                    "status": "expired",
                    "expired_at": {"$gt": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()},
                    "wallet_used_paisa": {"$gt": 0}
                },
                {"_id": 0}
            ).to_list(100)
            
            for order in expired_orders:
                wallet_used = order.get("wallet_used_paisa", 0)
                if wallet_used > 0:
                    # Refund wallet
                    await db.users.update_one(
                        {"id": order["user_id"]},
                        {"$inc": {"wallet_balance_paisa": wallet_used}}
                    )
                    
                    # Log wallet transaction
                    await db.wallet_transactions.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": order["user_id"],
                        "type": "refund",
                        "amount_paisa": wallet_used,
                        "reference_id": order["id"],
                        "description": f"Refund for expired order #{order['id'][:8].upper()}",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
                    
                    logger.info(f"Refunded {wallet_used} paisa for expired order {order['id'][:8]}")
                    
    except Exception as e:
        logger.error(f"Error in expire_old_orders job: {str(e)}")

async def flag_suspicious_sms():
    """
    Flag SMS messages that remain unmatched for more than 1 hour as suspicious
    Runs every 15 minutes
    """
    try:
        suspicious_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        suspicious_threshold_iso = suspicious_threshold.isoformat()
        
        result = await db.sms_messages.update_many(
            {
                "used": False,
                "suspicious": False,
                "parsed_at": {"$lt": suspicious_threshold_iso}
            },
            {
                "$set": {
                    "suspicious": True,
                    "suspicious_at": datetime.now(timezone.utc).isoformat(),
                    "suspicious_reason": "Unmatched for over 1 hour"
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Flagged {result.modified_count} SMS messages as suspicious (unmatched >1 hour)")
            
    except Exception as e:
        logger.error(f"Error in flag_suspicious_sms job: {str(e)}")

async def cleanup_processing_orders():
    """
    Reset orders stuck in 'processing' status for more than 10 minutes back to 'queued'
    Runs every 5 minutes
    """
    try:
        stuck_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        stuck_threshold_iso = stuck_threshold.isoformat()
        
        result = await db.orders.update_many(
            {
                "status": "processing",
                "processing_started_at": {"$lt": stuck_threshold_iso}
            },
            {
                "$set": {
                    "status": "queued",
                    "automation_state": "reset_from_stuck",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                "$inc": {"retry_count": 1}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Reset {result.modified_count} stuck orders from processing to queued")
            
    except Exception as e:
        logger.error(f"Error in cleanup_processing_orders job: {str(e)}")

# ===== APP LIFECYCLE =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - start/stop scheduler"""
    # Startup
    scheduler.add_job(expire_old_orders, 'interval', hours=1, id='expire_orders')
    scheduler.add_job(flag_suspicious_sms, 'interval', minutes=15, id='flag_suspicious_sms')
    scheduler.add_job(cleanup_processing_orders, 'interval', minutes=5, id='cleanup_processing')
    scheduler.start()
    logger.info("Background scheduler started with 3 jobs")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Background scheduler stopped")

app = FastAPI(title="Nex-Store API", version="2.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")

# Encryption
from cryptography.fernet import Fernet
import base64

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET", "nex-store-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# ===== CONFIGURATION =====
# All amounts stored in PAISA (1/100 of rupee) to avoid float issues
# Display: paisa / 100 = rupees

# Overpayment safety limits
MAX_OVERPAYMENT_RATIO = 3.0  # If payment > required * 3, mark suspicious
MAX_AUTO_CREDIT_AMOUNT_PAISA = 100000  # Max ₹1000 auto credit, else suspicious

# Order expiry time
ORDER_EXPIRY_HOURS = 24

# SMS suspicious threshold (unmatched for X hours)
SMS_SUSPICIOUS_HOURS = 1

# ===== ORDER TYPES & STATUSES =====
ORDER_TYPES = ["product_topup", "wallet_load"]

ORDER_STATUSES = [
    "pending_payment",    # Waiting for payment
    "paid",               # Payment received, queued for processing
    "queued",             # In automation queue
    "processing",         # Automation in progress
    "success",            # Completed successfully
    "failed",             # Automation failed
    "manual_review",      # Needs admin review
    "suspicious",         # Suspicious payment/activity
    "duplicate_payment",  # Duplicate RRN detected
    "expired",            # Not paid within time limit
    "invalid_uid",        # Invalid player UID
    "refunded"            # Refunded to wallet
]

AUTOMATION_STATES = [
    "INIT", "OPEN_SITE", "LOGOUT_PREVIOUS", "INPUT_UID", "SELECT_SERVER",
    "SELECT_PACKAGE", "CONFIRM_PURCHASE", "VERIFY_SUCCESS", "DONE", "FAILED"
]

# ===== UTILITY FUNCTIONS =====

def paisa_to_rupees(paisa: int) -> float:
    """Convert paisa to rupees for display"""
    return paisa / 100.0

def rupees_to_paisa(rupees: float) -> int:
    """Convert rupees to paisa for storage"""
    return int(round(rupees * 100))

def round_up_payment_paisa(amount_paisa: int) -> int:
    """Round up payment to clean number (in paisa).
    Rules:
    - < ₹100 (10000 paisa): round to nearest ₹1 (100 paisa)
    - ₹100-500: round to nearest ₹5 (500 paisa)
    - > ₹500: round to nearest ₹10 (1000 paisa)
    """
    if amount_paisa <= 0:
        return 0
    
    rupees = amount_paisa / 100.0
    
    if rupees < 100:
        # Round to nearest 1
        rounded = math.ceil(rupees)
    elif rupees <= 500:
        # Round to nearest 5
        rounded = math.ceil(rupees / 5) * 5
    else:
        # Round to nearest 10
        rounded = math.ceil(rupees / 10) * 10
    
    return int(rounded * 100)

def generate_sms_fingerprint(raw_message: str) -> str:
    """Generate unique fingerprint for SMS to prevent duplicates"""
    return hashlib.sha256(raw_message.strip().encode()).hexdigest()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user_type = payload.get("type")
        username = payload.get("username")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "type": user_type, "username": username}
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
        "amount_paisa": None,
        "last3digits": None,
        "rrn": None,
        "method": None,
        "remark": None
    }
    
    # Extract amount (Rs 125.00 or Rs 125)
    amount_match = re.search(r'Rs\.?\s*([0-9,]+\.?[0-9]*)', raw_message, re.IGNORECASE)
    if amount_match:
        amount_rupees = float(amount_match.group(1).replace(',', ''))
        result["amount_paisa"] = rupees_to_paisa(amount_rupees)
    
    # Extract last 3 digits - multiple patterns
    phone_patterns = [
        r'\d+[\*X]+(\d{3})\b',      # 900****910 or 98XXXXX910
        r'[X\*]+(\d{3})\b',          # XXX****910
        r'from\s+\S*?(\d{3})\s+for', # from xxx910 for
    ]
    for pattern in phone_patterns:
        phone_match = re.search(pattern, raw_message, re.IGNORECASE)
        if phone_match:
            result["last3digits"] = phone_match.group(1)
            break
    
    # Extract RRN
    rrn_match = re.search(r'RRN\s*[:\-]?\s*([A-Za-z0-9]+)', raw_message, re.IGNORECASE)
    if rrn_match:
        result["rrn"] = rrn_match.group(1)
    
    # Extract method and remark (after last comma: "remark /Method")
    parts = raw_message.split(',')
    if len(parts) >= 2:
        last_part = parts[-1].strip()
        if '/' in last_part:
            method_parts = last_part.split('/')
            if len(method_parts) >= 2:
                result["remark"] = method_parts[0].strip()
                result["method"] = method_parts[-1].strip()
    
    return result

# ===== PYDANTIC MODELS =====

class SignupRequest(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class LoginRequest(BaseModel):
    identifier: str
    password: str

class ResetPasswordRequest(BaseModel):
    identifier: str
    new_password: str

class TokenResponse(BaseModel):
    token: str
    user_type: str
    username: str
    wallet_balance: Optional[float] = None

class CreateOrderRequest(BaseModel):
    player_uid: str
    package_id: str

class CreateWalletLoadRequest(BaseModel):
    amount_rupees: float  # Amount user wants to add

class PaymentVerificationRequest(BaseModel):
    order_id: str
    sent_amount_rupees: float
    last_3_digits: str
    payment_method: str = "FonePay"
    payment_screenshot: Optional[str] = None
    remark: Optional[str] = None

class UpdateOrderUIDRequest(BaseModel):
    player_uid: str

class SMSMessage(BaseModel):
    raw_message: str

class CreatePackageRequest(BaseModel):
    name: str
    type: str
    amount: int
    price_rupees: float
    active: bool = True

class UpdatePackageRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[int] = None
    price_rupees: Optional[float] = None
    active: Optional[bool] = None
    sort_order: Optional[int] = None

class CreateGarenaAccountRequest(BaseModel):
    name: str
    email: str
    password: str
    pin: str

class UpdateGarenaAccountRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None
    active: Optional[bool] = None

class CreateUserRequest(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str

class AdminUpdateOrderRequest(BaseModel):
    player_uid: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

# ===== HELPER FUNCTIONS =====

async def credit_wallet(user_id: str, amount_paisa: int, transaction_type: str, 
                        order_id: str = None, description: str = None):
    """Safely credit wallet with proper transaction logging"""
    if amount_paisa <= 0:
        return 0
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        logger.error(f"User {user_id} not found for wallet credit")
        return 0
    
    old_balance = user.get("wallet_balance_paisa", 0)
    new_balance = old_balance + amount_paisa
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"wallet_balance_paisa": new_balance}}
    )
    
    # Log transaction
    await db.wallet_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": transaction_type,
        "amount_paisa": amount_paisa,
        "order_id": order_id,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "description": description or transaction_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Credited {amount_paisa} paisa to user {user_id}. New balance: {new_balance}")
    return amount_paisa

async def debit_wallet(user_id: str, amount_paisa: int, transaction_type: str,
                       order_id: str = None, description: str = None):
    """Safely debit wallet with proper transaction logging"""
    if amount_paisa <= 0:
        return 0
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return 0
    
    old_balance = user.get("wallet_balance_paisa", 0)
    if old_balance < amount_paisa:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    new_balance = old_balance - amount_paisa
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"wallet_balance_paisa": new_balance}}
    )
    
    # Log transaction
    await db.wallet_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": transaction_type,
        "amount_paisa": -amount_paisa,
        "order_id": order_id,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "description": description or transaction_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return amount_paisa

async def process_payment(order: dict, payment_amount_paisa: int, rrn: str = None, 
                          raw_message: str = None, sms_fingerprint: str = None):
    """Process payment with overpayment handling and safety checks.
    Returns: (status, overpayment_paisa, message)
    """
    required_paisa = order.get("payment_required_paisa", 0)
    overpayment_paisa = max(0, payment_amount_paisa - required_paisa)
    
    # Safety check 1: Suspicious if payment > required * MAX_RATIO
    if payment_amount_paisa > required_paisa * MAX_OVERPAYMENT_RATIO:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {
                "status": "suspicious",
                "payment_received_paisa": payment_amount_paisa,
                "payment_rrn": rrn,
                "raw_message": raw_message,
                "sms_fingerprint": sms_fingerprint,
                "suspicious_reason": f"Payment {paisa_to_rupees(payment_amount_paisa)} is more than {MAX_OVERPAYMENT_RATIO}x required {paisa_to_rupees(required_paisa)}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return ("suspicious", 0, "Payment flagged as suspicious due to large overpayment")
    
    # Safety check 2: Don't auto-credit if overpayment exceeds threshold
    credit_to_wallet = overpayment_paisa
    if overpayment_paisa > MAX_AUTO_CREDIT_AMOUNT_PAISA:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {
                "status": "suspicious",
                "payment_received_paisa": payment_amount_paisa,
                "payment_rrn": rrn,
                "raw_message": raw_message,
                "sms_fingerprint": sms_fingerprint,
                "overpayment_paisa": overpayment_paisa,
                "suspicious_reason": f"Overpayment {paisa_to_rupees(overpayment_paisa)} exceeds auto-credit limit",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return ("suspicious", 0, "Overpayment too large for auto-credit, needs manual review")
    
    # Process payment normally
    update_data = {
        "status": "paid",
        "payment_received_paisa": payment_amount_paisa,
        "payment_rrn": rrn,
        "raw_message": raw_message,
        "sms_fingerprint": sms_fingerprint,
        "overpayment_paisa": credit_to_wallet,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.orders.update_one({"id": order["id"]}, {"$set": update_data})
    
    # Credit overpayment to wallet
    if credit_to_wallet > 0:
        await credit_wallet(
            order["user_id"],
            credit_to_wallet,
            "overpayment_credit",
            order["id"],
            f"Overpayment from order #{order['id'][:8].upper()}"
        )
    
    # For wallet_load orders, credit the intended amount to wallet
    if order.get("order_type") == "wallet_load":
        load_amount = order.get("load_amount_paisa", 0)
        if load_amount > 0:
            await credit_wallet(
                order["user_id"],
                load_amount,
                "wallet_load",
                order["id"],
                f"Wallet load from order #{order['id'][:8].upper()}"
            )
    
    return ("paid", credit_to_wallet, "Payment processed successfully")

async def add_to_queue(order_id: str):
    """Add order to automation queue"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        return
    
    # Only queue product_topup orders
    if order.get("order_type") != "product_topup":
        # For wallet_load, mark as success immediately
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "status": "success",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "queued",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

async def process_automation_order(order_id: str):
    """
    Process a queued order through Garena automation
    This runs in a background task
    """
    from garena_automation import run_automation_for_order
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        logger.error(f"Order {order_id} not found for automation")
        return
    
    if order.get("status") != "queued":
        logger.warning(f"Order {order_id} status is {order.get('status')}, skipping automation")
        return
    
    # Update status to processing
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "processing",
            "automation_state": "started",
            "processing_started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Get active Garena account
    garena_acc = await db.garena_accounts.find_one({"active": True}, {"_id": 0})
    if not garena_acc:
        logger.error("No active Garena account found")
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "status": "manual_review",
                "automation_state": "no_garena_account",
                "suspicious_reason": "No active Garena account configured",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return
    
    try:
        # Decrypt credentials
        garena_email = garena_acc.get("email", "")
        garena_password = decrypt_data(garena_acc.get("password", ""))
        garena_pin = decrypt_data(garena_acc.get("pin", ""))
        
        # Run automation
        success, status_msg = await run_automation_for_order(
            order=order,
            garena_email=garena_email,
            garena_password=garena_password,
            garena_pin=garena_pin,
            headless=True
        )
        
        if success:
            # Mark order as success
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {
                    "status": "success",
                    "automation_state": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            logger.info(f"Order {order_id} automation completed successfully")
        else:
            # Determine failure handling
            retry_count = order.get("retry_count", 0) + 1
            
            if status_msg == "invalid_uid":
                # Invalid UID - don't retry
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "status": "invalid_uid",
                        "automation_state": status_msg,
                        "suspicious_reason": "Player UID not found in Free Fire",
                        "retry_count": retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            elif retry_count < 3:
                # Retry later
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "status": "queued",
                        "automation_state": f"retry_{retry_count}",
                        "retry_count": retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            else:
                # Max retries reached - manual review
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {
                        "status": "manual_review",
                        "automation_state": status_msg,
                        "suspicious_reason": f"Automation failed after {retry_count} attempts: {status_msg}",
                        "retry_count": retry_count,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            
            logger.error(f"Order {order_id} automation failed: {status_msg}")
            
    except Exception as e:
        logger.error(f"Automation error for order {order_id}: {str(e)}")
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "status": "manual_review",
                "automation_state": f"error: {str(e)[:100]}",
                "suspicious_reason": f"Automation exception: {str(e)[:200]}",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

async def try_match_sms_to_orders(sms_doc: dict):
    """Try to match an SMS to pending orders"""
    amount_paisa = sms_doc.get("amount_paisa")
    last3digits = sms_doc.get("last3digits")
    rrn = sms_doc.get("rrn")
    fingerprint = sms_doc.get("fingerprint")
    
    if not amount_paisa or not last3digits:
        return None
    
    # Check for duplicate RRN
    if rrn:
        existing = await db.orders.find_one({"payment_rrn": rrn})
        if existing:
            logger.warning(f"Duplicate RRN {rrn} detected")
            return None
    
    # Check for duplicate fingerprint
    if fingerprint:
        existing = await db.orders.find_one({"sms_fingerprint": fingerprint})
        if existing:
            logger.warning(f"Duplicate SMS fingerprint detected")
            return None
    
    # Find best matching order:
    # - Status is pending
    # - Last 3 digits match
    # - Payment amount >= required
    # - Prefer smallest overpayment
    # - Prefer oldest order
    pending_orders = await db.orders.find({
        "status": {"$in": ["pending_payment", "manual_review"]},
        "payment_last3digits": last3digits,
        "payment_required_paisa": {"$lte": amount_paisa}
    }, {"_id": 0}).sort("created_at", 1).to_list(20)
    
    if not pending_orders:
        return None
    
    # Find order with smallest overpayment
    best_order = None
    best_overpayment = float('inf')
    
    for order in pending_orders:
        required = order.get("payment_required_paisa", 0)
        overpayment = amount_paisa - required
        if overpayment < best_overpayment:
            best_overpayment = overpayment
            best_order = order
    
    return best_order

# ===== AUTHENTICATION ENDPOINTS =====

@api_router.post("/auth/signup", response_model=TokenResponse)
@limiter.limit("5/minute")  # Rate limit: 5 signups per minute per IP
async def signup(request: Request, signup_data: SignupRequest):
    # Validate username
    if len(signup_data.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    existing = await db.users.find_one({"username": signup_data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if signup_data.email:
        existing_email = await db.users.find_one({"email": signup_data.email})
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    if signup_data.phone:
        existing_phone = await db.users.find_one({"phone": signup_data.phone})
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "username": signup_data.username,
        "email": signup_data.email,
        "phone": signup_data.phone,
        "password_hash": hash_password(signup_data.password),
        "wallet_balance_paisa": 0,
        "blocked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id, "type": "user", "username": signup_data.username})
    
    return TokenResponse(
        token=token,
        user_type="user",
        username=signup_data.username,
        wallet_balance=0.0
    )

@api_router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 login attempts per minute per IP
async def login(request: Request, login_data: LoginRequest):
    user = await db.users.find_one({
        "$or": [
            {"username": request.identifier},
            {"email": request.identifier},
            {"phone": request.identifier}
        ]
    }, {"_id": 0})
    
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    token = create_access_token({"sub": user["id"], "type": "user", "username": user["username"]})
    balance_paisa = user.get("wallet_balance_paisa", 0)
    
    return TokenResponse(
        token=token,
        user_type="user",
        username=user["username"],
        wallet_balance=paisa_to_rupees(balance_paisa)
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

@api_router.post("/admin/login", response_model=TokenResponse)
async def admin_login(request: LoginRequest):
    admin = await db.admins.find_one({"username": request.identifier}, {"_id": 0})
    
    if not admin or not verify_password(request.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    token = create_access_token({"sub": admin["id"], "type": "admin", "username": admin["username"]})
    
    return TokenResponse(token=token, user_type="admin", username=admin["username"])

@api_router.post("/admin/reset-password")
async def admin_reset_password(request: ResetPasswordRequest, user_data: dict = Depends(get_current_admin)):
    await db.admins.update_one(
        {"id": user_data["user_id"]},
        {"$set": {"password_hash": hash_password(request.new_password)}}
    )
    return {"message": "Admin password reset successful"}

# ===== USER ENDPOINTS =====

@api_router.get("/user/profile")
async def get_profile(user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert paisa to rupees for display
    user["wallet_balance"] = paisa_to_rupees(user.get("wallet_balance_paisa", 0))
    
    return user

@api_router.get("/user/wallet")
async def get_wallet(user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0, "wallet_balance_paisa": 1})
    transactions = await db.wallet_transactions.find(
        {"user_id": user_data["user_id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    # Convert for display
    for t in transactions:
        t["amount"] = paisa_to_rupees(t.get("amount_paisa", 0))
        t["balance_before"] = paisa_to_rupees(t.get("balance_before_paisa", 0))
        t["balance_after"] = paisa_to_rupees(t.get("balance_after_paisa", 0))
    
    return {
        "balance": paisa_to_rupees(user.get("wallet_balance_paisa", 0)),
        "transactions": transactions
    }

@api_router.get("/user/orders")
async def get_user_orders(user_data: dict = Depends(get_current_user)):
    """Get ALL user orders (both wallet_load and product_topup)"""
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    orders = await db.orders.find(
        {"user_id": user_data["user_id"]}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(100).to_list(100)
    
    # Convert paisa to rupees for display
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["payment_amount"] = paisa_to_rupees(order.get("payment_amount_paisa", 0))
        order["payment_required"] = paisa_to_rupees(order.get("payment_required_paisa", 0))
        order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
        order["overpayment_credited"] = paisa_to_rupees(order.get("overpayment_paisa", 0))
        order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
        if order.get("order_type") == "wallet_load":
            order["load_amount"] = paisa_to_rupees(order.get("load_amount_paisa", 0))
    
    return orders

# ===== PACKAGE ENDPOINTS =====

@api_router.get("/packages/list")
async def list_packages():
    packages = await db.packages.find({"active": True}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    for pkg in packages:
        pkg["price"] = paisa_to_rupees(pkg.get("price_paisa", 0))
    return packages

# ===== ORDER ENDPOINTS =====

@api_router.post("/orders/create")
async def create_product_order(request: CreateOrderRequest, user_data: dict = Depends(get_current_user)):
    """Create a product top-up order"""
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    # Validate UID (min 8 digits)
    if not request.player_uid.isdigit() or len(request.player_uid) < 8:
        raise HTTPException(status_code=400, detail="Player UID must be at least 8 digits")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    package = await db.packages.find_one({"id": request.package_id, "active": True}, {"_id": 0})
    if not package:
        raise HTTPException(status_code=404, detail="Package not found or inactive")
    
    order_id = str(uuid.uuid4())
    locked_price_paisa = package.get("price_paisa", 0)
    wallet_balance_paisa = user.get("wallet_balance_paisa", 0)
    
    # Calculate wallet usage and payment required
    wallet_used_paisa = 0
    payment_required_paisa = locked_price_paisa
    status = "pending_payment"
    
    if wallet_balance_paisa > 0:
        if wallet_balance_paisa >= locked_price_paisa:
            wallet_used_paisa = locked_price_paisa
            payment_required_paisa = 0
            status = "paid"  # Fully paid by wallet
        else:
            wallet_used_paisa = wallet_balance_paisa
            payment_required_paisa = locked_price_paisa - wallet_balance_paisa
    
    # Round up payment amount
    payment_amount_paisa = round_up_payment_paisa(payment_required_paisa) if payment_required_paisa > 0 else 0
    
    order_doc = {
        "id": order_id,
        "order_type": "product_topup",
        "user_id": user_data["user_id"],
        "username": user["username"],
        "player_uid": request.player_uid,
        "server": "Bangladesh",
        "package_id": package["id"],
        "package_name": package["name"],
        "package_type": package["type"],
        "amount": package["amount"],
        "locked_price_paisa": locked_price_paisa,
        "wallet_used_paisa": wallet_used_paisa,
        "payment_required_paisa": payment_required_paisa,
        "payment_amount_paisa": payment_amount_paisa,
        "payment_last3digits": None,
        "payment_method": None,
        "payment_remark": None,
        "payment_screenshot": None,
        "payment_rrn": None,
        "payment_received_paisa": 0,
        "raw_message": None,
        "sms_fingerprint": None,
        "overpayment_paisa": 0,
        "status": status,
        "automation_state": None,
        "retry_count": 0,
        "notes": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
    
    await db.orders.insert_one(order_doc)
    
    # Debit wallet if used
    if wallet_used_paisa > 0:
        await debit_wallet(
            user_data["user_id"],
            wallet_used_paisa,
            "order_payment",
            order_id,
            f"Payment for order #{order_id[:8].upper()}"
        )
    
    # If fully paid by wallet, add to queue
    if status == "paid":
        await add_to_queue(order_id)
    
    return {
        "order_id": order_id,
        "status": status,
        "payment_amount": paisa_to_rupees(payment_amount_paisa),
        "payment_required": paisa_to_rupees(payment_required_paisa),
        "wallet_used": paisa_to_rupees(wallet_used_paisa)
    }

@api_router.post("/orders/wallet-load")
async def create_wallet_load_order(request: CreateWalletLoadRequest, user_data: dict = Depends(get_current_user)):
    """Create a wallet load order"""
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    if request.amount_rupees < 10:
        raise HTTPException(status_code=400, detail="Minimum wallet load is ₹10")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    order_id = str(uuid.uuid4())
    load_amount_paisa = rupees_to_paisa(request.amount_rupees)
    payment_amount_paisa = round_up_payment_paisa(load_amount_paisa)
    
    order_doc = {
        "id": order_id,
        "order_type": "wallet_load",
        "user_id": user_data["user_id"],
        "username": user["username"],
        "player_uid": None,
        "server": None,
        "package_id": None,
        "package_name": "Wallet Load",
        "package_type": "wallet_load",
        "amount": None,
        "load_amount_paisa": load_amount_paisa,
        "locked_price_paisa": load_amount_paisa,
        "wallet_used_paisa": 0,
        "payment_required_paisa": load_amount_paisa,
        "payment_amount_paisa": payment_amount_paisa,
        "payment_last3digits": None,
        "payment_method": None,
        "payment_remark": None,
        "payment_screenshot": None,
        "payment_rrn": None,
        "payment_received_paisa": 0,
        "raw_message": None,
        "sms_fingerprint": None,
        "overpayment_paisa": 0,
        "status": "pending_payment",
        "automation_state": None,
        "retry_count": 0,
        "notes": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
    
    await db.orders.insert_one(order_doc)
    
    return {
        "order_id": order_id,
        "status": "pending_payment",
        "load_amount": request.amount_rupees,
        "payment_amount": paisa_to_rupees(payment_amount_paisa)
    }

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, user_data: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if user_data["type"] == "user" and order["user_id"] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Convert paisa to rupees
    order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
    order["payment_amount"] = paisa_to_rupees(order.get("payment_amount_paisa", 0))
    order["payment_required"] = paisa_to_rupees(order.get("payment_required_paisa", 0))
    order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
    order["overpayment_credited"] = paisa_to_rupees(order.get("overpayment_paisa", 0))
    order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
    if order.get("order_type") == "wallet_load":
        order["load_amount"] = paisa_to_rupees(order.get("load_amount_paisa", 0))
    
    return order

@api_router.put("/orders/{order_id}/uid")
async def update_order_uid(order_id: str, request: UpdateOrderUIDRequest, user_data: dict = Depends(get_current_user)):
    """Allow user to update UID if status is invalid_uid or pending_payment"""
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    if not request.player_uid.isdigit() or len(request.player_uid) < 8:
        raise HTTPException(status_code=400, detail="Player UID must be at least 8 digits")
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["user_id"] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if order["status"] not in ["invalid_uid", "pending_payment"]:
        raise HTTPException(status_code=400, detail="Cannot update UID for this order status")
    
    new_status = "pending_payment" if order["status"] == "invalid_uid" else order["status"]
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "player_uid": request.player_uid,
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "UID updated successfully", "new_status": new_status}

@api_router.post("/orders/verify-payment")
async def verify_payment(request: PaymentVerificationRequest, user_data: dict = Depends(get_current_user)):
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    order = await db.orders.find_one({"id": request.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["user_id"] != user_data["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if order["status"] not in ["pending_payment", "manual_review"]:
        raise HTTPException(status_code=400, detail=f"Cannot verify payment for order with status: {order['status']}")
    
    # Update order with payment details
    sent_amount_paisa = rupees_to_paisa(request.sent_amount_rupees)
    
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
    
    required_paisa = order.get("payment_required_paisa", 0)
    
    # Try to match with SMS messages
    matching_sms = await db.sms_messages.find_one({
        "amount_paisa": {"$gte": required_paisa},
        "last3digits": request.last_3_digits,
        "used": False
    }, {"_id": 0}, sort=[("parsed_at", -1)])
    
    # If no match by required amount, try exact sent amount
    if not matching_sms:
        matching_sms = await db.sms_messages.find_one({
            "amount_paisa": sent_amount_paisa,
            "last3digits": request.last_3_digits,
            "used": False
        }, {"_id": 0})
    
    if matching_sms:
        # Check for duplicate RRN
        if matching_sms.get("rrn"):
            existing = await db.orders.find_one({"payment_rrn": matching_sms["rrn"], "id": {"$ne": request.order_id}})
            if existing:
                await db.orders.update_one(
                    {"id": request.order_id},
                    {"$set": {"status": "duplicate_payment", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                return {"message": "This payment was already used for another order", "status": "duplicate_payment"}
        
        # Check for duplicate fingerprint
        if matching_sms.get("fingerprint"):
            existing = await db.orders.find_one({"sms_fingerprint": matching_sms["fingerprint"], "id": {"$ne": request.order_id}})
            if existing:
                await db.orders.update_one(
                    {"id": request.order_id},
                    {"$set": {"status": "duplicate_payment", "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                return {"message": "This payment was already used for another order", "status": "duplicate_payment"}
        
        # Mark SMS as used
        await db.sms_messages.update_one(
            {"id": matching_sms["id"]},
            {"$set": {"used": True, "matched_order_id": request.order_id, "matched_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Process payment
        status, overpayment, message = await process_payment(
            order,
            matching_sms["amount_paisa"],
            matching_sms.get("rrn"),
            matching_sms.get("raw_message"),
            matching_sms.get("fingerprint")
        )
        
        if status == "paid":
            await add_to_queue(request.order_id)
        
        overpayment_rupees = paisa_to_rupees(overpayment)
        if overpayment > 0:
            return {
                "message": f"Payment verified! ₹{overpayment_rupees:.2f} extra was credited to your wallet.",
                "status": status,
                "overpayment_credited": overpayment_rupees
            }
        return {"message": "Payment verified! Your order is being processed.", "status": status}
    else:
        await db.orders.update_one(
            {"id": request.order_id},
            {"$set": {"status": "manual_review", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "We're verifying your payment. This usually takes a few minutes.", "status": "manual_review"}

# ===== SMS ENDPOINTS =====

@api_router.post("/sms/receive")
async def receive_sms(message: SMSMessage):
    """Receive SMS from phone app"""
    parsed = parse_sms_message(message.raw_message)
    fingerprint = generate_sms_fingerprint(message.raw_message)
    
    # Check for duplicate fingerprint
    existing = await db.sms_messages.find_one({"fingerprint": fingerprint})
    if existing:
        return {"message": "Duplicate SMS ignored", "duplicate": True}
    
    sms_doc = {
        "id": str(uuid.uuid4()),
        "raw_message": message.raw_message,
        "fingerprint": fingerprint,
        "amount_paisa": parsed["amount_paisa"],
        "last3digits": parsed["last3digits"],
        "rrn": parsed["rrn"],
        "method": parsed["method"],
        "remark": parsed["remark"],
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "used": False,
        "matched_order_id": None,
        "suspicious": False,
        "suspicious_at": None
    }
    
    await db.sms_messages.insert_one(sms_doc)
    
    # Try to auto-match
    best_order = await try_match_sms_to_orders(sms_doc)
    
    if best_order:
        # Check for duplicate RRN
        if parsed["rrn"]:
            existing = await db.orders.find_one({"payment_rrn": parsed["rrn"]})
            if existing:
                logger.warning(f"Duplicate RRN {parsed['rrn']}")
                return {"message": "SMS received, RRN already used", "matched": False}
        
        # Process payment
        status, overpayment, msg = await process_payment(
            best_order,
            parsed["amount_paisa"],
            parsed["rrn"],
            message.raw_message,
            fingerprint
        )
        
        await db.sms_messages.update_one(
            {"id": sms_doc["id"]},
            {"$set": {"used": True, "matched_order_id": best_order["id"], "matched_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if status == "paid":
            await add_to_queue(best_order["id"])
        
        logger.info(f"Auto-matched SMS to order {best_order['id']}. Overpayment: {overpayment}")
        return {"message": "SMS matched to order", "matched": True, "order_id": best_order["id"]}
    
    return {"message": "SMS saved, no matching order found", "matched": False}

# ===== ADMIN ENDPOINTS =====

@api_router.get("/admin/dashboard")
async def admin_dashboard(user_data: dict = Depends(get_current_admin)):
    """Admin dashboard with analytics"""
    # Get order stats
    pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_paisa": {"$sum": "$locked_price_paisa"}
        }}
    ]
    status_stats = await db.orders.aggregate(pipeline).to_list(100)
    
    # Get sales by product type
    product_pipeline = [
        {"$match": {"status": "success"}},
        {"$group": {
            "_id": "$package_type",
            "count": {"$sum": 1},
            "total_paisa": {"$sum": "$locked_price_paisa"}
        }}
    ]
    product_stats = await db.orders.aggregate(product_pipeline).to_list(100)
    
    # Get total wallet balance
    wallet_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$wallet_balance_paisa"}}}
    ]
    wallet_result = await db.users.aggregate(wallet_pipeline).to_list(1)
    total_wallet_paisa = wallet_result[0]["total"] if wallet_result else 0
    
    # Get unmatched SMS count
    unmatched_sms = await db.sms_messages.count_documents({"used": False})
    
    # Get orders needing review
    review_count = await db.orders.count_documents({
        "status": {"$in": ["manual_review", "suspicious", "failed", "invalid_uid"]}
    })
    
    # Calculate totals
    total_orders = sum(s["count"] for s in status_stats)
    success_orders = next((s["count"] for s in status_stats if s["_id"] == "success"), 0)
    success_sales_paisa = next((s["total_paisa"] for s in status_stats if s["_id"] == "success"), 0)
    failed_orders = next((s["count"] for s in status_stats if s["_id"] == "failed"), 0)
    suspicious_orders = next((s["count"] for s in status_stats if s["_id"] == "suspicious"), 0)
    pending_orders = next((s["count"] for s in status_stats if s["_id"] == "pending_payment"), 0)
    
    return {
        "total_orders": total_orders,
        "success_orders": success_orders,
        "total_sales": paisa_to_rupees(success_sales_paisa),
        "failed_orders": failed_orders,
        "suspicious_orders": suspicious_orders,
        "pending_orders": pending_orders,
        "total_wallet_balance": paisa_to_rupees(total_wallet_paisa),
        "unmatched_sms": unmatched_sms,
        "review_queue_count": review_count,
        "status_breakdown": {s["_id"]: s["count"] for s in status_stats},
        "product_stats": [{"type": p["_id"], "count": p["count"], "total": paisa_to_rupees(p["total_paisa"])} for p in product_stats]
    }

@api_router.get("/admin/orders")
async def admin_list_orders(
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    user_data: dict = Depends(get_current_admin)
):
    """List all orders with optional filters"""
    query = {}
    if status:
        query["status"] = status
    if order_type:
        query["order_type"] = order_type
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).limit(500).to_list(500)
    
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["payment_amount"] = paisa_to_rupees(order.get("payment_amount_paisa", 0))
        order["payment_required"] = paisa_to_rupees(order.get("payment_required_paisa", 0))
        order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
        order["overpayment_credited"] = paisa_to_rupees(order.get("overpayment_paisa", 0))
        order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
    
    return orders

@api_router.get("/admin/orders/{order_id}")
async def admin_get_order(order_id: str, user_data: dict = Depends(get_current_admin)):
    """Get single order details for admin"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
    order["payment_amount"] = paisa_to_rupees(order.get("payment_amount_paisa", 0))
    order["payment_required"] = paisa_to_rupees(order.get("payment_required_paisa", 0))
    order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
    order["overpayment_credited"] = paisa_to_rupees(order.get("overpayment_paisa", 0))
    order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
    
    return order

@api_router.put("/admin/orders/{order_id}")
async def admin_update_order(order_id: str, request: AdminUpdateOrderRequest, user_data: dict = Depends(get_current_admin)):
    """Admin update order"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if request.player_uid:
        update_data["player_uid"] = request.player_uid
    if request.status:
        if request.status not in ORDER_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {ORDER_STATUSES}")
        update_data["status"] = request.status
        if request.status == "success":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    if request.notes is not None:
        update_data["notes"] = request.notes
    
    await db.orders.update_one({"id": order_id}, {"$set": update_data})
    
    # Log action
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "update_order",
        "target_id": order_id,
        "details": f"Updated order: {update_data}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Order updated"}

@api_router.post("/admin/orders/{order_id}/mark-success")
async def admin_mark_order_success(order_id: str, user_data: dict = Depends(get_current_admin)):
    """Admin manually marks order as successful"""
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
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "mark_success",
        "target_id": order_id,
        "details": "Manually marked order as success",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Order marked as successful"}

@api_router.post("/admin/orders/{order_id}/retry")
async def admin_retry_order(order_id: str, user_data: dict = Depends(get_current_admin)):
    """Admin retries failed order"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("order_type") != "product_topup":
        raise HTTPException(status_code=400, detail="Can only retry product orders")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "queued",
            "automation_state": None,
            "retry_count": order.get("retry_count", 0) + 1,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "retry_order",
        "target_id": order_id,
        "details": f"Retry attempt #{order.get('retry_count', 0) + 1}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Order queued for retry"}

@api_router.post("/admin/orders/{order_id}/process")
async def admin_process_order(order_id: str, background_tasks: BackgroundTasks, user_data: dict = Depends(get_current_admin)):
    """Immediately trigger automation for a queued order"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.get("order_type") != "product_topup":
        raise HTTPException(status_code=400, detail="Can only process product orders")
    
    if order.get("status") not in ["queued", "paid"]:
        raise HTTPException(status_code=400, detail=f"Order must be in 'queued' or 'paid' status (current: {order.get('status')})")
    
    # Queue the automation in background
    background_tasks.add_task(process_automation_order, order_id)
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "trigger_automation",
        "target_id": order_id,
        "details": "Manually triggered automation",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Automation started", "order_id": order_id}

@api_router.get("/admin/automation/queue")
async def admin_automation_queue(user_data: dict = Depends(get_current_admin)):
    """Get orders in automation queue (queued/processing)"""
    orders = await db.orders.find(
        {
            "order_type": "product_topup",
            "status": {"$in": ["queued", "processing"]}
        },
        {"_id": 0}
    ).sort("queued_at", 1).to_list(100)
    
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
    
    return {
        "queued_count": len([o for o in orders if o["status"] == "queued"]),
        "processing_count": len([o for o in orders if o["status"] == "processing"]),
        "orders": orders
    }

@api_router.post("/admin/automation/process-all")
async def admin_process_all_queued(background_tasks: BackgroundTasks, user_data: dict = Depends(get_current_admin)):
    """Process all queued orders through automation"""
    orders = await db.orders.find(
        {"order_type": "product_topup", "status": "queued"},
        {"_id": 0, "id": 1}
    ).to_list(50)
    
    if not orders:
        return {"message": "No queued orders", "count": 0}
    
    # Queue all orders for processing
    for order in orders:
        background_tasks.add_task(process_automation_order, order["id"])
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "batch_automation",
        "target_id": None,
        "details": f"Triggered automation for {len(orders)} orders",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Started automation for {len(orders)} orders", "count": len(orders)}

@api_router.get("/admin/review-queue")
async def admin_review_queue(user_data: dict = Depends(get_current_admin)):
    """Get orders needing review"""
    orders = await db.orders.find(
        {"status": {"$in": ["manual_review", "suspicious", "failed", "invalid_uid", "duplicate_payment"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["payment_amount"] = paisa_to_rupees(order.get("payment_amount_paisa", 0))
        order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
    
    # Get unmatched SMS
    unmatched_sms = await db.sms_messages.find({"used": False}, {"_id": 0}).sort("parsed_at", -1).to_list(50)
    for sms in unmatched_sms:
        sms["amount"] = paisa_to_rupees(sms.get("amount_paisa", 0))
    
    return {
        "orders": orders,
        "unmatched_sms": unmatched_sms
    }

@api_router.get("/admin/sms")
async def admin_list_sms(user_data: dict = Depends(get_current_admin)):
    messages = await db.sms_messages.find({}, {"_id": 0}).sort("parsed_at", -1).limit(100).to_list(100)
    for m in messages:
        m["amount"] = paisa_to_rupees(m.get("amount_paisa", 0))
    return messages

@api_router.post("/admin/sms/input")
async def admin_input_sms(message: SMSMessage, user_data: dict = Depends(get_current_admin)):
    """Admin manually inputs SMS"""
    parsed = parse_sms_message(message.raw_message)
    fingerprint = generate_sms_fingerprint(message.raw_message)
    
    # Check duplicate
    existing = await db.sms_messages.find_one({"fingerprint": fingerprint})
    if existing:
        return {"message": "Duplicate SMS", "duplicate": True, "parsed": parsed}
    
    sms_doc = {
        "id": str(uuid.uuid4()),
        "raw_message": message.raw_message,
        "fingerprint": fingerprint,
        "amount_paisa": parsed["amount_paisa"],
        "last3digits": parsed["last3digits"],
        "rrn": parsed["rrn"],
        "method": parsed["method"],
        "remark": parsed["remark"],
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "used": False,
        "matched_order_id": None,
        "input_by_admin": user_data["user_id"]
    }
    
    await db.sms_messages.insert_one(sms_doc)
    
    # Try to auto-match
    best_order = await try_match_sms_to_orders(sms_doc)
    
    if best_order:
        if parsed["rrn"]:
            existing = await db.orders.find_one({"payment_rrn": parsed["rrn"]})
            if existing:
                return {
                    "message": f"RRN already used for order #{existing['id'][:8].upper()}",
                    "parsed": {"amount": paisa_to_rupees(parsed["amount_paisa"]), **{k:v for k,v in parsed.items() if k != "amount_paisa"}},
                    "matched": False,
                    "duplicate_rrn": True
                }
        
        status, overpayment, msg = await process_payment(
            best_order,
            parsed["amount_paisa"],
            parsed["rrn"],
            message.raw_message,
            fingerprint
        )
        
        await db.sms_messages.update_one(
            {"id": sms_doc["id"]},
            {"$set": {"used": True, "matched_order_id": best_order["id"]}}
        )
        
        if status == "paid":
            await add_to_queue(best_order["id"])
        
        await db.admin_actions.insert_one({
            "id": str(uuid.uuid4()),
            "admin_id": user_data["user_id"],
            "action_type": "input_sms",
            "target_id": best_order["id"],
            "details": f"Matched to order #{best_order['id'][:8].upper()}, Overpayment: {paisa_to_rupees(overpayment)}",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": f"SMS matched to order #{best_order['id'][:8].upper()}!",
            "parsed": {"amount": paisa_to_rupees(parsed["amount_paisa"]), **{k:v for k,v in parsed.items() if k != "amount_paisa"}},
            "matched": True,
            "order_id": best_order["id"],
            "overpayment_credited": paisa_to_rupees(overpayment)
        }
    
    return {
        "message": "SMS saved, no matching order found",
        "parsed": {"amount": paisa_to_rupees(parsed["amount_paisa"]) if parsed["amount_paisa"] else None, **{k:v for k,v in parsed.items() if k != "amount_paisa"}},
        "matched": False,
        "sms_id": sms_doc["id"]
    }

@api_router.post("/admin/sms/match/{sms_id}")
async def admin_manual_match(sms_id: str, order_id: str, user_data: dict = Depends(get_current_admin)):
    """Admin manually matches SMS to order"""
    sms = await db.sms_messages.find_one({"id": sms_id}, {"_id": 0})
    if not sms:
        raise HTTPException(status_code=404, detail="SMS not found")
    if sms.get("used"):
        raise HTTPException(status_code=400, detail="SMS already used")
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    status, overpayment, msg = await process_payment(
        order,
        sms["amount_paisa"],
        sms.get("rrn"),
        sms["raw_message"],
        sms.get("fingerprint")
    )
    
    await db.sms_messages.update_one(
        {"id": sms_id},
        {"$set": {"used": True, "matched_order_id": order_id}}
    )
    
    if status == "paid":
        await add_to_queue(order_id)
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "manual_match_sms",
        "target_id": order_id,
        "details": f"Manually matched SMS, Overpayment: {paisa_to_rupees(overpayment)}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"SMS matched to order #{order_id[:8].upper()}!", "overpayment_credited": paisa_to_rupees(overpayment)}

# ===== ADMIN PACKAGE MANAGEMENT =====

@api_router.get("/admin/packages")
async def admin_list_packages(user_data: dict = Depends(get_current_admin)):
    packages = await db.packages.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    for pkg in packages:
        pkg["price"] = paisa_to_rupees(pkg.get("price_paisa", 0))
    return packages

@api_router.post("/admin/packages")
async def admin_create_package(request: CreatePackageRequest, user_data: dict = Depends(get_current_admin)):
    max_pkg = await db.packages.find_one({}, sort=[("sort_order", -1)])
    next_sort = (max_pkg.get("sort_order", 0) + 1) if max_pkg else 1
    
    pkg_doc = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "type": request.type,
        "amount": request.amount,
        "price_paisa": rupees_to_paisa(request.price_rupees),
        "active": request.active,
        "sort_order": next_sort,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.packages.insert_one(pkg_doc)
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "create_package",
        "target_id": pkg_doc["id"],
        "details": f"Created package: {request.name}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    pkg_doc["price"] = request.price_rupees
    return pkg_doc

@api_router.put("/admin/packages/{package_id}")
async def admin_update_package(package_id: str, request: UpdatePackageRequest, user_data: dict = Depends(get_current_admin)):
    pkg = await db.packages.find_one({"id": package_id})
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if request.name:
        update_data["name"] = request.name
    if request.type:
        update_data["type"] = request.type
    if request.amount is not None:
        update_data["amount"] = request.amount
    if request.price_rupees is not None:
        update_data["price_paisa"] = rupees_to_paisa(request.price_rupees)
    if request.active is not None:
        update_data["active"] = request.active
    if request.sort_order is not None:
        update_data["sort_order"] = request.sort_order
    
    await db.packages.update_one({"id": package_id}, {"$set": update_data})
    
    return {"message": "Package updated"}

@api_router.delete("/admin/packages/{package_id}")
async def admin_delete_package(package_id: str, user_data: dict = Depends(get_current_admin)):
    await db.packages.delete_one({"id": package_id})
    return {"message": "Package deleted"}

# ===== ADMIN GARENA ACCOUNTS =====

@api_router.get("/admin/garena-accounts")
async def admin_list_garena_accounts(user_data: dict = Depends(get_current_admin)):
    accounts = await db.garena_accounts.find({}, {"_id": 0}).to_list(100)
    for acc in accounts:
        acc["password"] = "***hidden***"
        acc["pin"] = "***hidden***"
    return accounts

@api_router.post("/admin/garena-accounts")
async def admin_create_garena_account(request: CreateGarenaAccountRequest, user_data: dict = Depends(get_current_admin)):
    acc_doc = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "email": request.email,
        "password": encrypt_data(request.password),
        "pin": encrypt_data(request.pin),
        "active": True,
        "last_used": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.garena_accounts.insert_one(acc_doc)
    return {"message": "Garena account created", "id": acc_doc["id"]}

@api_router.put("/admin/garena-accounts/{account_id}")
async def admin_update_garena_account(account_id: str, request: UpdateGarenaAccountRequest, user_data: dict = Depends(get_current_admin)):
    acc = await db.garena_accounts.find_one({"id": account_id})
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = {}
    if request.name:
        update_data["name"] = request.name
    if request.email:
        update_data["email"] = request.email
    if request.password:
        update_data["password"] = encrypt_data(request.password)
    if request.pin:
        update_data["pin"] = encrypt_data(request.pin)
    if request.active is not None:
        update_data["active"] = request.active
    
    if update_data:
        await db.garena_accounts.update_one({"id": account_id}, {"$set": update_data})
    
    return {"message": "Garena account updated"}

@api_router.delete("/admin/garena-accounts/{account_id}")
async def admin_delete_garena_account(account_id: str, user_data: dict = Depends(get_current_admin)):
    await db.garena_accounts.delete_one({"id": account_id})
    return {"message": "Garena account deleted"}

# ===== ADMIN USER MANAGEMENT =====

@api_router.get("/admin/users")
async def admin_list_users(user_data: dict = Depends(get_current_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    for u in users:
        u["wallet_balance"] = paisa_to_rupees(u.get("wallet_balance_paisa", 0))
    return users

@api_router.post("/admin/users")
async def admin_create_user(request: CreateUserRequest, user_data: dict = Depends(get_current_admin)):
    existing = await db.users.find_one({"username": request.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "phone": request.phone,
        "password_hash": hash_password(request.password),
        "wallet_balance_paisa": 0,
        "blocked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    return {"message": "User created", "user_id": user_id}

@api_router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, blocked: Optional[bool] = None, password: Optional[str] = None, user_data: dict = Depends(get_current_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    if blocked is not None:
        update_data["blocked"] = blocked
    if password:
        update_data["password_hash"] = hash_password(password)
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    return {"message": "User updated"}

@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user_data: dict = Depends(get_current_admin)):
    await db.users.update_one({"id": user_id}, {"$set": {"deleted": True, "blocked": True}})
    return {"message": "User deleted"}

# ===== INIT ENDPOINT =====

@api_router.post("/admin/init")
async def initialize_data():
    """Initialize database with default data"""
    # Check if already initialized
    admin = await db.admins.find_one({"username": "admin"})
    if admin:
        return {"message": "Already initialized"}
    
    # Create admin
    admin_doc = {
        "id": str(uuid.uuid4()),
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.admins.insert_one(admin_doc)
    
    # Create packages (prices in paisa)
    packages = [
        {"name": "25 Diamonds", "type": "diamond", "amount": 25, "price_paisa": 99},
        {"name": "50 Diamonds", "type": "diamond", "amount": 50, "price_paisa": 149},
        {"name": "115 Diamonds", "type": "diamond", "amount": 115, "price_paisa": 299},
        {"name": "240 Diamonds", "type": "diamond", "amount": 240, "price_paisa": 499},
        {"name": "610 Diamonds", "type": "diamond", "amount": 610, "price_paisa": 999},
        {"name": "1,240 Diamonds", "type": "diamond", "amount": 1240, "price_paisa": 1999},
        {"name": "2,530 Diamonds", "type": "diamond", "amount": 2530, "price_paisa": 3999},
        {"name": "Weekly Membership", "type": "membership", "amount": 7, "price_paisa": 19900},
        {"name": "Monthly Membership", "type": "membership", "amount": 30, "price_paisa": 59900},
        {"name": "Evo Access 3D", "type": "evo_access", "amount": 3, "price_paisa": 9900},
        {"name": "Evo Access 7D", "type": "evo_access", "amount": 7, "price_paisa": 19900},
        {"name": "Evo Access 30D", "type": "evo_access", "amount": 30, "price_paisa": 49900},
    ]
    
    for i, pkg in enumerate(packages):
        pkg["id"] = str(uuid.uuid4())
        pkg["active"] = True
        pkg["sort_order"] = i + 1
        pkg["created_at"] = datetime.now(timezone.utc).isoformat()
        pkg["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.packages.insert_one(pkg)
    
    # Create test user
    test_user = {
        "id": str(uuid.uuid4()),
        "username": "testclient",
        "email": "test@example.com",
        "phone": "1234567890",
        "password_hash": hash_password("test123"),
        "wallet_balance_paisa": 5000,  # ₹50
        "blocked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(test_user)
    
    # Create test Garena account
    garena_acc = {
        "id": str(uuid.uuid4()),
        "name": "Primary Account",
        "email": "garena@example.com",
        "password": encrypt_data("garena123"),
        "pin": encrypt_data("1234"),
        "active": True,
        "last_used": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.garena_accounts.insert_one(garena_acc)
    
    # Create indexes
    await db.orders.create_index("payment_rrn", unique=True, sparse=True)
    await db.orders.create_index("sms_fingerprint", unique=True, sparse=True)
    await db.sms_messages.create_index("fingerprint", unique=True)
    await db.sms_messages.create_index("rrn", sparse=True)
    
    return {"message": "Initialization complete. Admin: admin/admin123, Test user: testclient/test123"}

# ===== CORS & APP SETUP =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.on_event("startup")
async def startup_db_client():
    logger.info("Nex-Store API v2.0 started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
