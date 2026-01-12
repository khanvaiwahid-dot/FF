# Free Fire Diamond Top-Up Platform - PRD

## Original Problem Statement
Build a fully automated Free Fire diamonds top-up platform with wallet + SMS payment verification.

---

## What's Been Implemented (as of Jan 12, 2026)

### ✅ Backend - Complete
- FastAPI server with all CRUD endpoints
- User/Admin authentication with JWT
- Products API with full CRUD operations
- **Integer-based currency system (paisa/cents)**
- **Unified Orders System** - Both product_topup and wallet_load orders
- **Payment Rounding Policy** - Round up to nearest 1/5/10 based on amount
- **Overpayment Handling** - Auto-credit to wallet
- **SMS Payment Verification** - SHA256 fingerprint, RRN tracking

### ✅ P1: Automation System - Complete
- Garena Automation Module (`/app/backend/garena_automation.py`)
- Admin Automation Endpoints for queue management and triggering

### ✅ P1: SMS Forwarder Integration - Complete
- Android SMS Forwarder App (`/app/android-sms-forwarder/`)
- SMS receive, parsing, matching endpoints

### ✅ P2: Order Expiry Job - Complete (Jan 12, 2026)
- **APScheduler** for background jobs
- `expire_old_orders` job runs hourly:
  - Expires `pending_payment` orders older than 24 hours
  - Automatically refunds `wallet_used_paisa` to user wallet
  - Creates refund wallet transaction record
- Admin endpoints:
  - `GET /api/admin/jobs/status` - View scheduler status and jobs
  - `POST /api/admin/jobs/expire-orders` - Manually trigger job
  - `GET /api/admin/stats/expiry` - View expiry statistics

### ✅ P2: Suspicious SMS Detection - Complete (Jan 12, 2026)
- `flag_suspicious_sms` job runs every 15 minutes:
  - Flags unmatched SMS messages older than 1 hour as suspicious
  - Sets `suspicious=True` and `suspicious_reason`
- Admin endpoint:
  - `POST /api/admin/jobs/flag-suspicious-sms` - Manually trigger job

### ✅ P2: Stuck Order Cleanup - Complete (Jan 12, 2026)
- `cleanup_processing_orders` job runs every 5 minutes:
  - Resets orders stuck in `processing` status for >10 minutes back to `queued`
  - Increments `retry_count` for tracking
- Admin endpoint:
  - `POST /api/admin/jobs/cleanup-processing` - Manually trigger job

### ✅ P2: Rate Limiting - Complete (Jan 12, 2026)
- **SlowAPI** for API rate limiting with proxy support (X-Forwarded-For)
- Rate limits configured:
  - Signup: 5/minute
  - Login: 10/minute
  - Admin Login: 5/minute
  - Password Reset: 3/minute
  - Order Create: 10/minute
  - SMS Receive: 60/minute

### ✅ Frontend - Complete
- Garena-style theme (white/orange/red)
- User pages: TopUp, Orders, Wallet, Payment flow
- Admin pages: Dashboard, Orders, Review, Payments, Products, Users, Garena Accounts

---

## Test Results Summary
| Iteration | Tests | Status |
|-----------|-------|--------|
| 2 | 26/26 | ✅ PASS - Basic functionality |
| 3 | 16/16 | ✅ PASS - Price update, admin orders |
| 4 | 25/25 | ✅ PASS - SMS & automation |
| 5 | 19/19 | ✅ PASS - Scheduled jobs, rate limiting |
| **Total** | **86/86** | **100% PASS** |

---

## Test Credentials
- **User:** `testclient` / `test123`
- **Admin:** `admin` / `admin123`

---

## Technical Architecture
```
/app/
├── backend/
│   ├── server.py              # Main FastAPI server with scheduler
│   ├── garena_automation.py   # Playwright automation module
│   └── .env
├── frontend/
│   └── src/pages/             # React pages
├── android-sms-forwarder/     # Android SMS app (Kotlin)
└── tests/
    ├── test_freefire_topup.py
    ├── test_price_update_and_admin_orders.py
    ├── test_sms_and_automation.py
    └── test_p2_scheduled_jobs_and_rate_limiting.py
```

---

## Scheduled Jobs Configuration
| Job | Interval | Description |
|-----|----------|-------------|
| `expire_orders` | 1 hour | Expires pending orders >24h, refunds wallet |
| `flag_suspicious_sms` | 15 min | Flags unmatched SMS >1h as suspicious |
| `cleanup_processing` | 5 min | Resets stuck processing orders to queued |

---

## Rate Limits
| Endpoint | Limit |
|----------|-------|
| `/api/auth/signup` | 5/minute |
| `/api/auth/login` | 10/minute |
| `/api/admin/login` | 5/minute |
| `/api/auth/reset-password` | 3/minute |
| `/api/orders/create` | 10/minute |
| `/api/sms/receive` | 60/minute |

---

## Pending Tasks

### P3 - Future/Backlog
- [ ] Build and distribute Android SMS Forwarder APK
- [ ] Admin action audit logging UI
- [ ] Code refactoring (split server.py into routers)
- [ ] Production deployment with real Garena credentials

---

## MOCKED Features
⚠️ **Garena Automation** - Requires real Garena credentials for production
