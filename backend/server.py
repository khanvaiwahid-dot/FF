"""
Nex-Store Backend Server
Free Fire Diamond Top-Up Platform with Wallet + SMS Payment Verification
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
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

def get_real_ip(request: Request) -> str:
    """Get real IP address, considering X-Forwarded-For for proxy setups"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, the first one is the client
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)

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

# Rate limiter setup with proxy support
limiter = Limiter(key_func=get_real_ip)

# Background scheduler for periodic tasks
scheduler = AsyncIOScheduler()

# ===== SYSTEM SETTINGS (GLOBAL CACHE) =====
# Loaded on startup and cached, updated when admin changes settings

DEFAULT_SYSTEM_SETTINGS = {
    "id": "system_settings",
    "auto_payment_check": True,  # Auto-match payments to orders
    "auto_topup": False,  # Auto-run automation (disabled due to bot detection)
    "max_overpayment_ratio": 3,  # Max overpayment multiplier before suspicious
    "max_wallet_credit": 1000000,  # Max wallet credit in paisa (₹10,000)
    "automation_fail_threshold": 5,  # Circuit breaker threshold
    "automation_fail_window_minutes": 10,  # Circuit breaker window
    "order_expiry_minutes": 1440,  # 24 hours
    "payment_match_window_minutes": 60,  # Payment age limit for auto-match
    "created_at": None,
    "updated_at": None
}

# Global cache for system settings
_system_settings_cache = None
_automation_failures = []  # Track recent automation failures for circuit breaker

async def get_system_settings() -> dict:
    """Get system settings from cache or database"""
    global _system_settings_cache
    
    if _system_settings_cache is None:
        settings = await db.system_settings.find_one({"id": "system_settings"}, {"_id": 0})
        if settings is None:
            # Initialize with defaults
            settings = DEFAULT_SYSTEM_SETTINGS.copy()
            settings["created_at"] = datetime.now(timezone.utc).isoformat()
            settings["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.system_settings.insert_one(settings)
        _system_settings_cache = settings
    
    return _system_settings_cache

async def update_system_settings(updates: dict) -> dict:
    """Update system settings and refresh cache"""
    global _system_settings_cache
    
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.system_settings.update_one(
        {"id": "system_settings"},
        {"$set": updates},
        upsert=True
    )
    
    # Refresh cache
    _system_settings_cache = await db.system_settings.find_one({"id": "system_settings"}, {"_id": 0})
    return _system_settings_cache

def record_automation_failure():
    """Record an automation failure for circuit breaker"""
    global _automation_failures
    _automation_failures.append(datetime.now(timezone.utc))
    # Keep only recent failures
    _automation_failures = [f for f in _automation_failures if f > datetime.now(timezone.utc) - timedelta(minutes=30)]

async def check_circuit_breaker() -> bool:
    """Check if circuit breaker should trip. Returns True if automation should be disabled."""
    global _automation_failures
    settings = await get_system_settings()
    
    threshold = settings.get("automation_fail_threshold", 5)
    window_minutes = settings.get("automation_fail_window_minutes", 10)
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    
    recent_failures = [f for f in _automation_failures if f > window_start]
    
    if len(recent_failures) >= threshold:
        # Trip the circuit breaker
        if settings.get("auto_topup", False):
            await update_system_settings({"auto_topup": False})
            logger.warning(f"CIRCUIT BREAKER TRIPPED: {len(recent_failures)} automation failures in {window_minutes} minutes. Auto-topup disabled.")
            
            # Create alert
            await db.system_alerts.insert_one({
                "id": str(uuid.uuid4()),
                "type": "circuit_breaker",
                "severity": "critical",
                "message": f"Auto-topup disabled due to {len(recent_failures)} failures in {window_minutes} minutes",
                "acknowledged": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        return True
    
    return False

# ===== USER ROLES =====
ROLES = ["USER", "STAFF", "ADMIN"]

def get_role_level(role: str) -> int:
    """Get numeric level for role comparison"""
    levels = {"USER": 1, "STAFF": 2, "ADMIN": 3}
    return levels.get(role, 0)

# ===== SCHEDULED JOBS =====

async def expire_old_orders():
    """
    Expire orders that have been pending_payment for longer than configured time
    Runs every 10 minutes
    """
    try:
        settings = await get_system_settings()
        expiry_minutes = settings.get("order_expiry_minutes", 1440)  # Default 24 hours
        
        expiry_threshold = datetime.now(timezone.utc) - timedelta(minutes=expiry_minutes)
        expiry_threshold_iso = expiry_threshold.isoformat()
        
        # Find pending orders older than expiry time
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
            logger.info(f"Expired {result.modified_count} orders older than {expiry_minutes} minutes")
            
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

# ===== ENCRYPTION - FAIL FAST IF NOT CONFIGURED =====
from cryptography.fernet import Fernet
import base64

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logger.critical("FATAL: ENCRYPTION_KEY environment variable is not set!")
    logger.critical("Please set ENCRYPTION_KEY in .env file before starting the server.")
    logger.critical("Generate a key with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    raise SystemExit("ENCRYPTION_KEY is required. Server cannot start without it.")

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    logger.info("Encryption key loaded successfully")
except Exception as e:
    logger.critical(f"FATAL: Invalid ENCRYPTION_KEY format: {e}")
    raise SystemExit(f"Invalid ENCRYPTION_KEY: {e}")

def encrypt_data(data: str) -> str:
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed - data may have been encrypted with different key: {e}")
        raise ValueError("Decryption failed - credentials may be corrupted or encrypted with a different key")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET", "nex-store-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# ===== AUDIT LOGGING =====

async def create_audit_log(
    user_id: str,
    username: str,
    role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    details: Optional[str] = None
):
    """Create an audit log entry for any admin/staff action"""
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "username": username,
        "role": role,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before": before,
        "after": after,
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

async def create_system_alert(
    alert_type: str,
    severity: str,  # info, warning, critical
    message: str,
    entity_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """Create a system alert for admin notification"""
    await db.system_alerts.insert_one({
        "id": str(uuid.uuid4()),
        "type": alert_type,
        "severity": severity,
        "message": message,
        "entity_id": entity_id,
        "metadata": metadata,
        "acknowledged": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

# ===== CONFIGURATION =====
# All amounts stored in PAISA (1/100 of rupee) to avoid float issues
# Display: paisa / 100 = rupees

# Overpayment safety limits (loaded from system_settings at runtime)
MAX_OVERPAYMENT_RATIO = 3.0  # Default, overridden by system_settings
MAX_AUTO_CREDIT_AMOUNT_PAISA = 100000  # Default, overridden by system_settings

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
    "manual_pending",     # Paid but auto_topup disabled, needs manual processing
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
        role = payload.get("role", "USER")  # Default to USER role
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "type": user_type, "username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require ADMIN role"""
    user_data = await get_current_user(credentials)
    if user_data["type"] != "admin" or user_data.get("role") not in ["ADMIN"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_data

async def get_current_staff_or_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Require STAFF or ADMIN role"""
    user_data = await get_current_user(credentials)
    if user_data["type"] != "admin" or user_data.get("role") not in ["STAFF", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Staff or Admin access required")
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
    role: Optional[str] = None  # USER, STAFF, ADMIN

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

class AdminWalletRechargeRequest(BaseModel):
    amount_paisa: int = Field(..., gt=0, description="Amount in paisa (must be positive integer)")
    reason: str = Field(..., min_length=5, description="Reason for recharge (min 5 characters)")

class AdminWalletRedeemRequest(BaseModel):
    amount_paisa: int = Field(..., gt=0, description="Amount in paisa (must be positive integer)")
    reason: str = Field(..., min_length=5, description="Reason for redemption (min 5 characters)")

# ===== CONFIGURATION =====
# Admin wallet redeem single-action limit (₹5000 = 500000 paisa)
ADMIN_REDEEM_SINGLE_LIMIT_PAISA = 500000

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
    """
    Add order to automation queue.
    Checks auto_topup setting - if disabled, routes to manual_pending.
    """
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
    
    # Check if auto_topup is enabled
    settings = await get_system_settings()
    if not settings.get("auto_topup", False):
        # Route to manual_pending - requires manual processing
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "status": "manual_pending",
                "manual_pending_reason": "auto_topup_disabled",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        logger.info(f"Order {order_id} routed to manual_pending (auto_topup disabled)")
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
            
            # Record failure for circuit breaker
            record_automation_failure()
            await check_circuit_breaker()
            
            logger.error(f"Order {order_id} automation failed: {status_msg}")
            
    except Exception as e:
        logger.error(f"Automation error for order {order_id}: {str(e)}")
        
        # Record failure for circuit breaker
        record_automation_failure()
        await check_circuit_breaker()
        
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
    """
    Try to match an SMS payment to pending orders.
    Implements production-ready safety checks:
    - Duplicate prevention (RRN + fingerprint)
    - Payment age window check
    - Overpayment ratio check
    - Max wallet credit check
    - Routes to manual queue if auto_payment_check is disabled
    """
    settings = await get_system_settings()
    
    amount_paisa = sms_doc.get("amount_paisa")
    last3digits = sms_doc.get("last3digits")
    rrn = sms_doc.get("rrn")
    fingerprint = sms_doc.get("fingerprint")
    sms_received_at = sms_doc.get("received_at") or sms_doc.get("parsed_at")
    
    if not amount_paisa or not last3digits:
        return None
    
    # Check for duplicate RRN
    if rrn:
        existing = await db.orders.find_one({"payment_rrn": rrn})
        if existing:
            logger.warning(f"Duplicate RRN {rrn} detected - marking SMS as duplicate")
            await db.sms_messages.update_one(
                {"id": sms_doc["id"]},
                {"$set": {"status": "duplicate_payment", "used": True}}
            )
            await create_system_alert("duplicate_payment", "warning", f"Duplicate payment RRN: {rrn}", rrn)
            return None
    
    # Check for duplicate fingerprint
    if fingerprint:
        existing = await db.orders.find_one({"sms_fingerprint": fingerprint})
        if existing:
            logger.warning(f"Duplicate SMS fingerprint detected")
            await db.sms_messages.update_one(
                {"id": sms_doc["id"]},
                {"$set": {"status": "duplicate_payment", "used": True}}
            )
            return None
    
    # Check if auto_payment_check is disabled - route to manual queue
    if not settings.get("auto_payment_check", True):
        logger.info("Auto payment check disabled - routing to manual queue")
        await db.sms_messages.update_one(
            {"id": sms_doc["id"]},
            {"$set": {"status": "manual_review", "manual_review_reason": "auto_payment_check_disabled"}}
        )
        return None
    
    # Check payment age (within payment_match_window_minutes)
    payment_match_window = settings.get("payment_match_window_minutes", 60)
    if sms_received_at:
        try:
            if isinstance(sms_received_at, str):
                sms_time = datetime.fromisoformat(sms_received_at.replace('Z', '+00:00'))
            else:
                sms_time = sms_received_at
            
            age_minutes = (datetime.now(timezone.utc) - sms_time).total_seconds() / 60
            if age_minutes > payment_match_window:
                logger.warning(f"Payment too old ({age_minutes:.0f} min > {payment_match_window} min) - requires manual review")
                await db.sms_messages.update_one(
                    {"id": sms_doc["id"]},
                    {"$set": {"status": "manual_review", "manual_review_reason": "payment_age_exceeded"}}
                )
                return None
        except Exception as e:
            logger.error(f"Error checking payment age: {e}")
    
    # Find best matching order:
    # - Status is pending_payment (NOT expired)
    # - Last 3 digits match
    # - Payment amount >= required
    # - Prefer smallest overpayment
    # - Prefer oldest order
    pending_orders = await db.orders.find({
        "status": "pending_payment",  # Only pending_payment, not expired
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
    
    if not best_order:
        return None
    
    required_amount = best_order.get("payment_required_paisa", 0)
    
    # OVERPAYMENT SAFETY CHECK 1: Ratio check
    max_ratio = settings.get("max_overpayment_ratio", 3)
    if amount_paisa > required_amount * max_ratio:
        logger.warning(f"Suspicious overpayment: {amount_paisa} > {required_amount} * {max_ratio}")
        await db.sms_messages.update_one(
            {"id": sms_doc["id"]},
            {"$set": {"suspicious": True, "status": "suspicious", "suspicious_reason": f"overpayment_ratio_exceeded"}}
        )
        await create_system_alert(
            "suspicious_payment", "critical",
            f"Suspicious overpayment: Rs {paisa_to_rupees(amount_paisa)} for order requiring Rs {paisa_to_rupees(required_amount)}",
            best_order["id"],
            {"amount_paisa": amount_paisa, "required_paisa": required_amount, "ratio": amount_paisa / required_amount}
        )
        return None  # Don't auto-credit
    
    # OVERPAYMENT SAFETY CHECK 2: Max wallet credit check
    leftover = amount_paisa - required_amount
    max_wallet_credit = settings.get("max_wallet_credit", 1000000)
    if leftover > max_wallet_credit:
        logger.warning(f"Leftover {leftover} exceeds max wallet credit {max_wallet_credit}")
        await db.sms_messages.update_one(
            {"id": sms_doc["id"]},
            {"$set": {"suspicious": True, "status": "suspicious", "suspicious_reason": f"leftover_exceeds_max_wallet_credit"}}
        )
        await create_system_alert(
            "suspicious_payment", "critical",
            f"Leftover Rs {paisa_to_rupees(leftover)} exceeds max wallet credit Rs {paisa_to_rupees(max_wallet_credit)}",
            best_order["id"],
            {"leftover_paisa": leftover, "max_wallet_credit_paisa": max_wallet_credit}
        )
        return None  # Don't auto-credit
    
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
            {"username": login_data.identifier},
            {"email": login_data.identifier},
            {"phone": login_data.identifier}
        ]
    }, {"_id": 0})
    
    if not user or not verify_password(login_data.password, user["password_hash"]):
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
@limiter.limit("3/minute")  # Rate limit: 3 password resets per minute per IP
async def reset_password(request: Request, reset_data: ResetPasswordRequest):
    user = await db.users.find_one({
        "$or": [
            {"username": reset_data.identifier},
            {"email": reset_data.identifier},
            {"phone": reset_data.identifier}
        ]
    })
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(reset_data.new_password)}}
    )
    
    return {"message": "Password reset successful"}

@api_router.post("/admin/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Rate limit: 5 admin login attempts per minute per IP
async def admin_login(request: Request, login_data: LoginRequest):
    admin = await db.admins.find_one({"username": login_data.identifier}, {"_id": 0})
    
    if not admin or not verify_password(login_data.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    
    # Get role (default to ADMIN for existing admins)
    role = admin.get("role", "ADMIN")
    
    token = create_access_token({
        "sub": admin["id"], 
        "type": "admin", 
        "username": admin["username"],
        "role": role
    })
    
    return TokenResponse(token=token, user_type="admin", username=admin["username"], role=role)

@api_router.post("/admin/reset-password")
async def admin_reset_password(reset_data: ResetPasswordRequest, user_data: dict = Depends(get_current_admin)):
    await db.admins.update_one(
        {"id": user_data["user_id"]},
        {"$set": {"password_hash": hash_password(reset_data.new_password)}}
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
@limiter.limit("10/minute")  # Rate limit: 10 orders per minute per IP
async def create_product_order(request: Request, order_data: CreateOrderRequest, user_data: dict = Depends(get_current_user)):
    """Create a product top-up order"""
    if user_data["type"] != "user":
        raise HTTPException(status_code=403, detail="User access required")
    
    # Validate UID (min 8 digits)
    if not order_data.player_uid.isdigit() or len(order_data.player_uid) < 8:
        raise HTTPException(status_code=400, detail="Player UID must be at least 8 digits")
    
    user = await db.users.find_one({"id": user_data["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")
    
    package = await db.packages.find_one({"id": order_data.package_id, "active": True}, {"_id": 0})
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
    
    # Build order document - only include payment_rrn and sms_fingerprint if they have values
    # MongoDB sparse unique indexes only skip documents where the field is MISSING
    order_doc = {
        "id": order_id,
        "order_type": "product_topup",
        "user_id": user_data["user_id"],
        "username": user["username"],
        "player_uid": order_data.player_uid,
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
        # payment_rrn and sms_fingerprint NOT included - allows sparse unique index to work
        "payment_received_paisa": 0,
        "raw_message": None,
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
    
    # Build order document - omit payment_rrn and sms_fingerprint for sparse unique index
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
        # payment_rrn and sms_fingerprint NOT included - allows sparse unique index to work
        "payment_received_paisa": 0,
        "raw_message": None,
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
@limiter.limit("60/minute")  # Rate limit: 60 SMS per minute per IP (for Android app)
async def receive_sms(request: Request, message: SMSMessage):
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

# ===== SYSTEM SETTINGS ENDPOINTS =====

class SystemSettingsUpdate(BaseModel):
    auto_payment_check: Optional[bool] = None
    auto_topup: Optional[bool] = None
    max_overpayment_ratio: Optional[int] = None
    max_wallet_credit: Optional[int] = None
    automation_fail_threshold: Optional[int] = None
    automation_fail_window_minutes: Optional[int] = None
    order_expiry_minutes: Optional[int] = None
    payment_match_window_minutes: Optional[int] = None

@api_router.get("/admin/system-settings")
async def get_settings(user_data: dict = Depends(get_current_admin)):
    """Get current system settings (ADMIN only)"""
    settings = await get_system_settings()
    return settings

@api_router.put("/admin/system-settings")
async def update_settings(request: SystemSettingsUpdate, user_data: dict = Depends(get_current_admin)):
    """Update system settings (ADMIN only)"""
    updates = {}
    old_settings = await get_system_settings()
    
    if request.auto_payment_check is not None:
        updates["auto_payment_check"] = request.auto_payment_check
    if request.auto_topup is not None:
        updates["auto_topup"] = request.auto_topup
    if request.max_overpayment_ratio is not None:
        if request.max_overpayment_ratio < 1:
            raise HTTPException(status_code=400, detail="max_overpayment_ratio must be >= 1")
        updates["max_overpayment_ratio"] = request.max_overpayment_ratio
    if request.max_wallet_credit is not None:
        if request.max_wallet_credit < 0:
            raise HTTPException(status_code=400, detail="max_wallet_credit must be >= 0")
        updates["max_wallet_credit"] = request.max_wallet_credit
    if request.automation_fail_threshold is not None:
        if request.automation_fail_threshold < 1:
            raise HTTPException(status_code=400, detail="automation_fail_threshold must be >= 1")
        updates["automation_fail_threshold"] = request.automation_fail_threshold
    if request.automation_fail_window_minutes is not None:
        if request.automation_fail_window_minutes < 1:
            raise HTTPException(status_code=400, detail="automation_fail_window_minutes must be >= 1")
        updates["automation_fail_window_minutes"] = request.automation_fail_window_minutes
    if request.order_expiry_minutes is not None:
        if request.order_expiry_minutes < 1:
            raise HTTPException(status_code=400, detail="order_expiry_minutes must be >= 1")
        updates["order_expiry_minutes"] = request.order_expiry_minutes
    if request.payment_match_window_minutes is not None:
        if request.payment_match_window_minutes < 1:
            raise HTTPException(status_code=400, detail="payment_match_window_minutes must be >= 1")
        updates["payment_match_window_minutes"] = request.payment_match_window_minutes
    
    if not updates:
        raise HTTPException(status_code=400, detail="No valid updates provided")
    
    new_settings = await update_system_settings(updates)
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "ADMIN"),
        action="update_system_settings",
        entity_type="system_settings",
        entity_id="system_settings",
        before={k: old_settings.get(k) for k in updates.keys()},
        after={k: new_settings.get(k) for k in updates.keys()}
    )
    
    return {"message": "Settings updated", "settings": new_settings}

@api_router.get("/admin/system-alerts")
async def get_alerts(
    acknowledged: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    user_data: dict = Depends(get_current_staff_or_admin)
):
    """Get system alerts (STAFF or ADMIN)"""
    query = {}
    if acknowledged is not None:
        query["acknowledged"] = acknowledged
    if severity:
        query["severity"] = severity
    
    alerts = await db.system_alerts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return alerts

@api_router.put("/admin/system-alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user_data: dict = Depends(get_current_staff_or_admin)):
    """Acknowledge a system alert"""
    result = await db.system_alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "acknowledged": True,
            "acknowledged_by": user_data["username"],
            "acknowledged_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert acknowledged"}

# ===== MANUAL OPERATIONS ENDPOINTS (STAFF + ADMIN) =====

@api_router.get("/staff/manual-orders")
async def get_manual_orders(user_data: dict = Depends(get_current_staff_or_admin)):
    """Get orders needing manual action (STAFF or ADMIN)"""
    orders = await db.orders.find({
        "status": {"$in": ["paid", "failed", "invalid_uid", "suspicious", "manual_pending", "manual_review"]}
    }, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["payment_received"] = paisa_to_rupees(order.get("payment_received_paisa", 0))
        order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
    
    return orders

@api_router.post("/staff/orders/{order_id}/mark-success")
async def staff_mark_success(order_id: str, user_data: dict = Depends(get_current_staff_or_admin)):
    """Mark order as successfully completed (STAFF or ADMIN)"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.get("status")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "success",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "manual_completed_by": user_data["username"]
        }}
    )
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "STAFF"),
        action="mark_success",
        entity_type="order",
        entity_id=order_id,
        before={"status": old_status},
        after={"status": "success"},
        details=f"Manually marked order as successful"
    )
    
    return {"message": "Order marked as success"}

@api_router.post("/staff/orders/{order_id}/mark-failed")
async def staff_mark_failed(order_id: str, reason: Optional[str] = None, user_data: dict = Depends(get_current_staff_or_admin)):
    """Mark order as failed (STAFF or ADMIN)"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.get("status")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "failed",
            "failed_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "manual_failed_by": user_data["username"]
        }}
    )
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "STAFF"),
        action="mark_failed",
        entity_type="order",
        entity_id=order_id,
        before={"status": old_status},
        after={"status": "failed"},
        details=f"Manually marked order as failed. Reason: {reason}"
    )
    
    return {"message": "Order marked as failed"}

class EditUIDRequest(BaseModel):
    player_uid: str = Field(..., min_length=1)

@api_router.put("/staff/orders/{order_id}/edit-uid")
async def staff_edit_uid(order_id: str, request: EditUIDRequest, user_data: dict = Depends(get_current_staff_or_admin)):
    """Edit player UID (STAFF or ADMIN)"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_uid = order.get("player_uid")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "player_uid": request.player_uid,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "STAFF"),
        action="edit_uid",
        entity_type="order",
        entity_id=order_id,
        before={"player_uid": old_uid},
        after={"player_uid": request.player_uid}
    )
    
    return {"message": "UID updated"}

class AddNoteRequest(BaseModel):
    note: str = Field(..., min_length=1)

@api_router.post("/staff/orders/{order_id}/add-note")
async def staff_add_note(order_id: str, request: AddNoteRequest, user_data: dict = Depends(get_current_staff_or_admin)):
    """Add manual note to order (STAFF or ADMIN)"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    existing_notes = order.get("manual_notes", [])
    new_note = {
        "id": str(uuid.uuid4()),
        "note": request.note,
        "by": user_data["username"],
        "at": datetime.now(timezone.utc).isoformat()
    }
    existing_notes.append(new_note)
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"manual_notes": existing_notes, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Note added", "note": new_note}

# ===== MANUAL PAYMENT CHECK (STAFF + ADMIN) =====

@api_router.get("/staff/unmatched-payments")
async def get_unmatched_payments(user_data: dict = Depends(get_current_staff_or_admin)):
    """Get unmatched/suspicious payments needing review"""
    payments = await db.sms_messages.find({
        "$or": [
            {"used": False},
            {"status": {"$in": ["suspicious", "duplicate_payment", "manual_review"]}}
        ]
    }, {"_id": 0}).sort("parsed_at", -1).limit(200).to_list(200)
    
    for p in payments:
        if p.get("amount_paisa"):
            p["amount"] = paisa_to_rupees(p["amount_paisa"])
    
    return payments

class LinkPaymentRequest(BaseModel):
    order_id: str

@api_router.post("/staff/payments/{payment_id}/link")
async def link_payment_to_order(payment_id: str, request: LinkPaymentRequest, user_data: dict = Depends(get_current_staff_or_admin)):
    """Manually link payment to order (STAFF or ADMIN)"""
    payment = await db.sms_messages.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.get("used"):
        raise HTTPException(status_code=400, detail="Payment already used")
    
    order = await db.orders.find_one({"id": request.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Process the payment for this order
    status, overpayment, msg = await process_payment(
        order=order,
        payment_amount_paisa=payment.get("amount_paisa", 0),
        rrn=payment.get("rrn"),
        raw_message=payment.get("raw_message"),
        sms_fingerprint=payment.get("fingerprint")
    )
    
    # Mark SMS as used
    await db.sms_messages.update_one(
        {"id": payment_id},
        {"$set": {
            "used": True,
            "matched_order_id": request.order_id,
            "matched_by": user_data["username"],
            "matched_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Add to queue if paid successfully
    if status == "paid":
        await add_to_queue(request.order_id)
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "STAFF"),
        action="link_payment",
        entity_type="payment",
        entity_id=payment_id,
        details=f"Linked payment to order {request.order_id}. Result: {status}"
    )
    
    return {"message": msg, "status": status, "overpayment_credited": paisa_to_rupees(overpayment)}

@api_router.post("/staff/payments/{payment_id}/mark-invalid")
async def mark_payment_invalid(payment_id: str, reason: Optional[str] = None, user_data: dict = Depends(get_current_staff_or_admin)):
    """Mark payment as invalid (STAFF or ADMIN)"""
    payment = await db.sms_messages.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    await db.sms_messages.update_one(
        {"id": payment_id},
        {"$set": {
            "status": "invalid",
            "used": True,
            "invalid_reason": reason,
            "invalid_by": user_data["username"],
            "invalid_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Audit log
    await create_audit_log(
        user_id=user_data["user_id"],
        username=user_data["username"],
        role=user_data.get("role", "STAFF"),
        action="mark_payment_invalid",
        entity_type="payment",
        entity_id=payment_id,
        details=f"Marked payment as invalid. Reason: {reason}"
    )
    
    return {"message": "Payment marked as invalid"}

# ===== AUDIT LOGS (ADMIN ONLY) =====

@api_router.get("/admin/audit-logs")
async def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 200,
    user_data: dict = Depends(get_current_admin)
):
    """Get audit logs (ADMIN only)"""
    query = {}
    if action:
        query["action"] = action
    if entity_type:
        query["entity_type"] = entity_type
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs

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

@api_router.get("/admin/automation/issues")
async def admin_automation_issues(user_data: dict = Depends(get_current_admin)):
    """Get orders with automation issues (manual_review, failed, invalid_uid)"""
    orders = await db.orders.find(
        {
            "order_type": "product_topup",
            "status": {"$in": ["manual_review", "failed", "invalid_uid"]}
        },
        {"_id": 0}
    ).sort("updated_at", -1).limit(20).to_list(20)
    
    for order in orders:
        order["locked_price"] = paisa_to_rupees(order.get("locked_price_paisa", 0))
        order["wallet_used"] = paisa_to_rupees(order.get("wallet_used_paisa", 0))
    
    return {
        "total": len(orders),
        "orders": orders
    }

# ===== SMS FORWARDER APP API =====

# Token for SMS forwarder app authentication
SMS_FORWARDER_TOKEN = os.environ.get("SMS_FORWARDER_TOKEN", "sms-forwarder-secret-token-change-me")

class SMSIngestRequest(BaseModel):
    raw_message: str
    sender: Optional[str] = None
    received_at: str
    amount_paisa: Optional[int] = None
    last3digits: Optional[str] = None
    rrn: Optional[str] = None
    remark: Optional[str] = None
    method: Optional[str] = None
    sms_fingerprint: str
    device_id: Optional[str] = None
    app_version: Optional[str] = None

async def verify_sms_forwarder_token(authorization: str = Header(None)):
    """Verify SMS forwarder app token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    if token != SMS_FORWARDER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token

@api_router.post("/sms/ingest")
async def sms_ingest(request: SMSIngestRequest, token: str = Depends(verify_sms_forwarder_token)):
    """
    Receive SMS from Android forwarder app.
    - Validates token
    - Checks for duplicates by fingerprint or RRN
    - Parses SMS if fields not provided
    - Stores and attempts auto-matching
    """
    # Check duplicate by fingerprint
    existing = await db.sms_messages.find_one({"fingerprint": request.sms_fingerprint})
    if existing:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "status": "duplicate", "reason": "fingerprint_exists"}
        )
    
    # Check duplicate by RRN if provided
    if request.rrn:
        existing_rrn = await db.sms_messages.find_one({"rrn": request.rrn})
        if existing_rrn:
            return JSONResponse(
                status_code=409,
                content={"ok": False, "status": "duplicate", "reason": "rrn_exists"}
            )
    
    # If amount not parsed by app, try server-side parsing
    parsed = {}
    if request.amount_paisa is None or request.last3digits is None:
        parsed = parse_sms_message(request.raw_message)
    
    sms_doc = {
        "id": str(uuid.uuid4()),
        "raw_message": request.raw_message,
        "sender": request.sender,
        "fingerprint": request.sms_fingerprint,
        "amount_paisa": request.amount_paisa or parsed.get("amount_paisa"),
        "last3digits": request.last3digits or parsed.get("last3digits"),
        "rrn": request.rrn or parsed.get("rrn"),
        "method": request.method or parsed.get("method"),
        "remark": request.remark or parsed.get("remark"),
        "received_at": request.received_at,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "device_id": request.device_id,
        "app_version": request.app_version,
        "source": "android_forwarder",
        "used": False,
        "matched_order_id": None,
        "suspicious": False
    }
    
    await db.sms_messages.insert_one(sms_doc)
    logger.info(f"SMS ingested from forwarder: amount={sms_doc['amount_paisa']} paisa, rrn={sms_doc['rrn']}, device={request.device_id}")
    
    # Try to auto-match
    best_order = await try_match_sms_to_orders(sms_doc)
    
    if best_order:
        return {
            "ok": True,
            "status": "accepted",
            "matched": True,
            "matched_order_id": best_order["id"][:8]
        }
    
    return {
        "ok": True,
        "status": "accepted",
        "matched": False
    }

@api_router.get("/sms/health")
async def sms_health():
    """Health check endpoint for SMS forwarder app"""
    return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()}

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

# ===== ADMIN WALLET MANAGEMENT =====

@api_router.post("/admin/users/{user_id}/wallet/recharge")
async def admin_wallet_recharge(user_id: str, request: AdminWalletRechargeRequest, user_data: dict = Depends(get_current_admin)):
    """
    Admin manually recharges (credits) user wallet.
    Creates wallet transaction (type=credit, source=admin), order record, and audit log.
    wallet_load orders NEVER trigger automation.
    """
    # Validate user exists
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate reason length
    if len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")
    
    order_id = str(uuid.uuid4())
    old_balance = user.get("wallet_balance_paisa", 0)
    new_balance = old_balance + request.amount_paisa
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. Update user wallet balance IMMEDIATELY
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"wallet_balance_paisa": new_balance}}
    )
    
    # 2. Create wallet transaction (type=credit, source=admin)
    wallet_tx = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "credit",
        "source": "admin",
        "amount_paisa": request.amount_paisa,
        "order_id": order_id,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "description": f"Admin recharge: {request.reason}",
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "created_at": now
    }
    await db.wallet_transactions.insert_one(wallet_tx)
    
    # 3. Create wallet_load order record (NO UID, NO product validation, NO automation)
    order_doc = {
        "id": order_id,
        "order_type": "wallet_load",  # NEVER triggers automation
        "user_id": user_id,
        "username": user["username"],
        "player_uid": None,  # NULL - not required for wallet_load
        "server": None,  # NULL - not required for wallet_load
        "package_id": None,  # NULL - not required for wallet_load
        "package_name": "Admin Wallet Recharge",
        "package_type": "wallet_load",
        "amount": None,
        "load_amount_paisa": request.amount_paisa,
        "locked_price_paisa": request.amount_paisa,
        "wallet_used_paisa": 0,
        "payment_required_paisa": 0,
        "payment_amount_paisa": 0,
        "payment_last3digits": None,
        "payment_method": "admin_manual",
        "payment_remark": request.reason,
        "payment_screenshot": None,
        "payment_rrn": f"ADMIN_RECHARGE_{order_id[:8].upper()}",
        "payment_received_paisa": request.amount_paisa,
        "raw_message": None,
        "sms_fingerprint": f"ADMIN_RECHARGE_{order_id}",
        "overpayment_paisa": 0,
        "status": "success",  # Immediately success - no automation
        "automation_state": None,
        "retry_count": 0,
        "notes": f"Admin recharge by {user_data['username']}: {request.reason}",
        "created_by": "admin",
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "created_at": now,
        "updated_at": now,
        "completed_at": now
    }
    await db.orders.insert_one(order_doc)
    
    # 4. Create admin action audit log (MANDATORY)
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "action_type": "wallet_recharge",
        "target_user_id": user_id,
        "target_username": user["username"],
        "order_id": order_id,
        "amount_paisa": request.amount_paisa,
        "reason": request.reason,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "created_at": now
    })
    
    logger.info(f"Admin {user_data['username']} recharged {request.amount_paisa} paisa to user {user['username']}. New balance: {new_balance}")
    
    return {
        "message": f"Successfully recharged ₹{paisa_to_rupees(request.amount_paisa):.2f} to {user['username']}'s wallet",
        "order_id": order_id,
        "amount_recharged_paisa": request.amount_paisa,
        "old_balance_paisa": old_balance,
        "new_balance_paisa": new_balance
    }

@api_router.post("/admin/users/{user_id}/wallet/redeem")
async def admin_wallet_redeem(user_id: str, request: AdminWalletRedeemRequest, user_data: dict = Depends(get_current_admin)):
    """
    Admin manually redeems (debits) from user wallet.
    Creates wallet transaction (type=debit, source=admin), order record, and audit log.
    wallet_load orders NEVER trigger automation.
    Rules:
    - amount_paisa <= wallet.balance
    - amount_paisa <= REDEEM_LIMIT (default ₹5000)
    """
    # Validate user exists
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate reason length
    if len(request.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Reason must be at least 5 characters")
    
    old_balance = user.get("wallet_balance_paisa", 0)
    
    # Check single-action limit (configurable, default ₹5000 = 500000 paisa)
    if request.amount_paisa > ADMIN_REDEEM_SINGLE_LIMIT_PAISA:
        raise HTTPException(
            status_code=400, 
            detail=f"Single redemption cannot exceed ₹{paisa_to_rupees(ADMIN_REDEEM_SINGLE_LIMIT_PAISA):.2f}"
        )
    
    # Check sufficient balance (amount_paisa <= wallet.balance)
    if request.amount_paisa > old_balance:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient wallet balance. Current balance: ₹{paisa_to_rupees(old_balance):.2f}"
        )
    
    order_id = str(uuid.uuid4())
    new_balance = old_balance - request.amount_paisa
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. Update user wallet balance IMMEDIATELY
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"wallet_balance_paisa": new_balance}}
    )
    
    # 2. Create wallet transaction (type=debit, source=admin)
    wallet_tx = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "debit",
        "source": "admin",
        "amount_paisa": -request.amount_paisa,  # Negative for deduction
        "order_id": order_id,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "description": f"Admin redemption: {request.reason}",
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "created_at": now
    }
    await db.wallet_transactions.insert_one(wallet_tx)
    
    # 3. Create wallet_load order record (NO UID, NO product validation, NO automation)
    order_doc = {
        "id": order_id,
        "order_type": "wallet_load",  # NEVER triggers automation
        "user_id": user_id,
        "username": user["username"],
        "player_uid": None,  # NULL - not required for wallet_load
        "server": None,  # NULL - not required for wallet_load
        "package_id": None,  # NULL - not required for wallet_load
        "package_name": "Admin Wallet Redemption",
        "package_type": "wallet_load",
        "amount": None,
        "load_amount_paisa": -request.amount_paisa,  # Negative for deduction
        "locked_price_paisa": request.amount_paisa,
        "wallet_used_paisa": 0,
        "payment_required_paisa": 0,
        "payment_amount_paisa": 0,
        "payment_last3digits": None,
        "payment_method": "admin_manual",
        "payment_remark": request.reason,
        "payment_screenshot": None,
        "payment_rrn": f"ADMIN_REDEEM_{order_id[:8].upper()}",
        "payment_received_paisa": 0,
        "raw_message": None,
        "sms_fingerprint": f"ADMIN_REDEEM_{order_id}",
        "overpayment_paisa": 0,
        "status": "success",  # Immediately success - no automation
        "automation_state": None,
        "retry_count": 0,
        "notes": f"Admin redemption by {user_data['username']}: {request.reason}",
        "created_by": "admin",
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "created_at": now,
        "updated_at": now,
        "completed_at": now
    }
    await db.orders.insert_one(order_doc)
    
    # 4. Create admin action audit log (MANDATORY)
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "admin_username": user_data["username"],
        "action_type": "wallet_redeem",
        "target_user_id": user_id,
        "target_username": user["username"],
        "order_id": order_id,
        "amount_paisa": request.amount_paisa,
        "reason": request.reason,
        "balance_before_paisa": old_balance,
        "balance_after_paisa": new_balance,
        "created_at": now
    })
    
    logger.info(f"Admin {user_data['username']} redeemed {request.amount_paisa} paisa from user {user['username']}. New balance: {new_balance}")
    
    return {
        "message": f"Successfully redeemed ₹{paisa_to_rupees(request.amount_paisa):.2f} from {user['username']}'s wallet",
        "order_id": order_id,
        "amount_redeemed_paisa": request.amount_paisa,
        "old_balance_paisa": old_balance,
        "new_balance_paisa": new_balance
    }

@api_router.get("/admin/action-logs")
async def admin_get_action_logs(
    admin_username: Optional[str] = None,
    action_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 200,
    user_data: dict = Depends(get_current_admin)
):
    """
    Get admin action audit logs with filters.
    Filters: admin_username, action_type, date range
    """
    query = {}
    
    if admin_username:
        query["admin_username"] = admin_username
    
    if action_type:
        query["action_type"] = action_type
    
    # Date range filter
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        if date_query:
            query["created_at"] = date_query
    
    logs = await db.admin_actions.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Convert paisa to rupees for display
    for log in logs:
        if log.get("amount_paisa"):
            log["amount"] = paisa_to_rupees(log["amount_paisa"])
        if log.get("balance_before_paisa") is not None:
            log["balance_before"] = paisa_to_rupees(log["balance_before_paisa"])
        if log.get("balance_after_paisa") is not None:
            log["balance_after"] = paisa_to_rupees(log["balance_after_paisa"])
    
    return logs

@api_router.get("/admin/action-logs/action-types")
async def admin_get_action_types(user_data: dict = Depends(get_current_admin)):
    """Get distinct action types for filter dropdown"""
    action_types = await db.admin_actions.distinct("action_type")
    return action_types

@api_router.get("/admin/action-logs/admins")
async def admin_get_admin_usernames(user_data: dict = Depends(get_current_admin)):
    """Get distinct admin usernames for filter dropdown"""
    admin_usernames = await db.admin_actions.distinct("admin_username")
    # Filter out None values
    return [u for u in admin_usernames if u]

# ===== SCHEDULED JOBS ADMIN ENDPOINTS =====

@api_router.get("/admin/jobs/status")
async def admin_jobs_status(user_data: dict = Depends(get_current_admin)):
    """Get status of scheduled background jobs"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs
    }

@api_router.post("/admin/jobs/expire-orders")
async def admin_run_expire_orders(user_data: dict = Depends(get_current_admin)):
    """Manually run the expire orders job"""
    await expire_old_orders()
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "manual_job_run",
        "target_id": None,
        "details": "Manually ran expire_old_orders job",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Expire orders job completed"}

@api_router.post("/admin/jobs/flag-suspicious-sms")
async def admin_run_flag_suspicious(user_data: dict = Depends(get_current_admin)):
    """Manually run the flag suspicious SMS job"""
    await flag_suspicious_sms()
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "manual_job_run",
        "target_id": None,
        "details": "Manually ran flag_suspicious_sms job",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Flag suspicious SMS job completed"}

@api_router.post("/admin/jobs/cleanup-processing")
async def admin_run_cleanup_processing(user_data: dict = Depends(get_current_admin)):
    """Manually run the cleanup processing orders job"""
    await cleanup_processing_orders()
    
    await db.admin_actions.insert_one({
        "id": str(uuid.uuid4()),
        "admin_id": user_data["user_id"],
        "action_type": "manual_job_run",
        "target_id": None,
        "details": "Manually ran cleanup_processing_orders job",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Cleanup processing orders job completed"}

@api_router.get("/admin/stats/expiry")
async def admin_expiry_stats(user_data: dict = Depends(get_current_admin)):
    """Get statistics on order expiry and suspicious SMS"""
    # Get expired orders count (last 24h)
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    expired_count = await db.orders.count_documents({
        "status": "expired",
        "expired_at": {"$gt": yesterday}
    })
    
    # Get pending orders older than 12h (candidates for expiry)
    expiry_warning_threshold = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    pending_old_count = await db.orders.count_documents({
        "status": "pending_payment",
        "created_at": {"$lt": expiry_warning_threshold}
    })
    
    # Get suspicious SMS count
    suspicious_sms_count = await db.sms_messages.count_documents({"suspicious": True})
    
    # Get unmatched SMS count (not yet suspicious)
    unmatched_sms_count = await db.sms_messages.count_documents({
        "used": False,
        "suspicious": False
    })
    
    return {
        "expired_last_24h": expired_count,
        "pending_older_than_12h": pending_old_count,
        "suspicious_sms_count": suspicious_sms_count,
        "unmatched_sms_count": unmatched_sms_count
    }

@api_router.get("/admin/health")
async def admin_health_check(user_data: dict = Depends(get_current_admin)):
    """
    Comprehensive health check for admin - checks encryption, Garena accounts, and system status.
    Returns warnings for any issues that need attention.
    """
    warnings = []
    errors = []
    
    # Check 1: Verify encryption key is set (should always pass since server wouldn't start otherwise)
    if not ENCRYPTION_KEY:
        errors.append("CRITICAL: ENCRYPTION_KEY is not set!")
    
    # Check 2: Verify Garena accounts can be decrypted
    garena_accounts = await db.garena_accounts.find({}, {"_id": 0}).to_list(100)
    corrupted_accounts = []
    valid_accounts = 0
    active_accounts = 0
    
    for acc in garena_accounts:
        try:
            # Try to decrypt password and pin
            if acc.get("password"):
                decrypt_data(acc["password"])
            if acc.get("pin"):
                decrypt_data(acc["pin"])
            valid_accounts += 1
            if acc.get("active"):
                active_accounts += 1
        except Exception as e:
            corrupted_accounts.append({
                "email": acc.get("email"),
                "error": "Cannot decrypt credentials - likely encrypted with different key"
            })
    
    if corrupted_accounts:
        errors.append(f"CRITICAL: {len(corrupted_accounts)} Garena account(s) have corrupted credentials and must be re-added!")
        for acc in corrupted_accounts:
            errors.append(f"  - {acc['email']}: {acc['error']}")
    
    if active_accounts == 0:
        warnings.append("WARNING: No active Garena accounts configured. Automation will not work!")
    
    # Check 3: Check for stuck orders
    stuck_processing = await db.orders.count_documents({
        "status": "processing",
        "processing_started_at": {"$lt": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}
    })
    if stuck_processing > 0:
        warnings.append(f"WARNING: {stuck_processing} order(s) stuck in 'processing' status for >10 minutes")
    
    # Check 4: Check automation queue
    queued_count = await db.orders.count_documents({"status": "queued"})
    if queued_count > 20:
        warnings.append(f"WARNING: {queued_count} orders in automation queue - consider processing")
    
    # Check 5: Check for orders pending payment >12h
    old_pending = await db.orders.count_documents({
        "status": "pending_payment",
        "created_at": {"$lt": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()}
    })
    if old_pending > 0:
        warnings.append(f"INFO: {old_pending} order(s) pending payment for >12 hours (will expire at 24h)")
    
    # Check 6: Check scheduler status
    scheduler_running = scheduler.running
    if not scheduler_running:
        errors.append("CRITICAL: Background scheduler is not running!")
    
    # Determine overall status
    if errors:
        status = "CRITICAL"
    elif warnings:
        status = "WARNING"
    else:
        status = "HEALTHY"
    
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "garena_accounts": {
            "total": len(garena_accounts),
            "valid": valid_accounts,
            "active": active_accounts,
            "corrupted": len(corrupted_accounts)
        },
        "scheduler_running": scheduler_running,
        "queued_orders": queued_count,
        "encryption_key_set": bool(ENCRYPTION_KEY)
    }

# ===== INIT ENDPOINT =====

@api_router.post("/admin/init")
async def initialize_data():
    """Initialize database with default data"""
    # Check if already initialized
    admin = await db.admins.find_one({"username": "admin"})
    if admin:
        return {"message": "Already initialized"}
    
    # Create admin with ADMIN role
    admin_doc = {
        "id": str(uuid.uuid4()),
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "role": "ADMIN",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.admins.insert_one(admin_doc)
    
    # Create staff user
    staff_doc = {
        "id": str(uuid.uuid4()),
        "username": "staff",
        "password_hash": hash_password("staff123"),
        "role": "STAFF",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.admins.insert_one(staff_doc)
    
    # Initialize system settings
    settings = DEFAULT_SYSTEM_SETTINGS.copy()
    settings["created_at"] = datetime.now(timezone.utc).isoformat()
    settings["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.system_settings.update_one(
        {"id": "system_settings"},
        {"$set": settings},
        upsert=True
    )
    
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
    await db.audit_logs.create_index("created_at")
    await db.system_alerts.create_index("created_at")
    
    return {"message": "Initialization complete. Admin: admin/admin123, Staff: staff/staff123, Test user: testclient/test123"}

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
