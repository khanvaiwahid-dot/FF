# Free Fire Diamond Top-Up Platform - PRD

## Original Problem Statement
Build a fully automated Free Fire diamonds top-up platform with the following requirements:

### Core Features
1. **Users & Auth:** User signup with unique permanent username, email/phone, password. Password reset for users and admins.
2. **Website & UI:** Mobile-first, minimal UI with strict White/Orange/Red Garena-style theme.
3. **Top-Up & Payment Flow:** Fixed Bangladesh server, two-step payment (FonePay/Wallet), partial wallet payment support.
4. **Products & Pricing:** Garena-matching products (Diamonds, Memberships, Evo Access), admin-editable pricing.
5. **Garena Automation:** Playwright with stealth for automation, admin-managed Garena accounts stored encrypted.
6. **Admin Panel:** Dashboard, Products CRUD, Garena Accounts Manager, User Management.

---

## What's Been Implemented (as of Jan 12, 2026)

### ✅ Backend - Complete
- FastAPI server with all CRUD endpoints
- User authentication (signup, login, password reset)
- Admin authentication with JWT
- Products API with full CRUD operations
- **Integer-based currency system (paisa/cents)** - All monetary values stored as integers
- **Unified Orders System** - Both product_topup and wallet_load orders in single collection with `order_type` field
- **Payment Rounding Policy** - Round up to nearest 1 (<₹100), nearest 5 (₹100-500), nearest 10 (>₹500)
- **Overpayment Handling** - Auto-credit to wallet with safety checks for suspicious amounts
- **SMS Payment Verification** - SHA256 fingerprint for uniqueness, RRN tracking
- Garena Accounts API with encrypted credentials
- User Management API (create, block/unblock, password reset, soft delete)
- Dashboard stats endpoint with analytics
- **Order Status System**: pending_payment, paid, queued, processing, success, failed, manual_review, suspicious, duplicate_payment, expired, invalid_uid, refunded
- **Admin Order Edit API** - PUT /api/admin/orders/{order_id} for updating player_uid, status, notes

### ✅ Frontend - Complete
- **Garena-style theme** (white/orange/red) applied consistently across all pages
- **Text readability fixed** - All text uses dark gray/black on light backgrounds
- Login & Signup pages with proper styling
- Admin Login page
- Admin Dashboard with stats cards, charts, and management links
- Admin Products Management (view, edit, delete)
- Admin Garena Accounts Management (CRUD with PIN field)
- Admin Users Management (view, block/unblock, password reset)
- **Admin All Orders page** - Shows ALL orders (wallet_load + product_topup) with:
  - Filter by order_type (All Types, Product Top-up, Wallet Load)
  - Filter by status (All Status, success, pending_payment, paid, queued, processing, failed, manual_review)
  - Search by order ID, username, or UID
  - View modal with full order details
  - Edit modal for updating player_uid, status, and notes
  - Retry/Mark Success actions for failed orders
- **Admin Review page** - Queue for suspicious/failed orders needing attention
- **Admin Payments page** - Unmatched SMS payments inbox
- Admin SMS Inbox - Input payment SMS, view parsed data, manual matching
- User TopUp page with wallet balance and package selection
- **UID validation** - minimum 8 digits, numbers only
- **User Orders page** with order list and detail view
- Wallet page with transaction history
- Fixed Bangladesh server display
- Bottom navigation with 3 tabs (Top Up, Orders, Wallet)

### ✅ Price Update System - Verified Working
- Admin can update package prices via PUT /api/admin/packages/{id}
- New orders immediately use the new `price_paisa` value
- Old orders retain their original `locked_price_paisa` value (immutable)
- Packages API returns fresh prices without caching

---

## Test Results (Jan 12, 2026)
- **Iteration 2:** 26/26 tests PASSED - Basic functionality
- **Iteration 3:** 16/16 tests PASSED - Price update flow + Admin orders
- **Total:** 42 tests passing

### Verified Features (Iteration 3):
| Feature | Status |
|---------|--------|
| Price update affects new orders | ✅ PASS |
| Old orders retain locked_price | ✅ PASS |
| Packages API no caching | ✅ PASS |
| Admin orders shows all types | ✅ PASS |
| Filter by order_type | ✅ PASS |
| Filter by status | ✅ PASS |
| Combined filters | ✅ PASS |
| Admin view order modal | ✅ PASS |
| Admin edit player_uid | ✅ PASS |
| Admin edit status | ✅ PASS |
| Admin edit notes | ✅ PASS |
| Wallet load order creation | ✅ PASS |
| Wallet load visible in admin | ✅ PASS |
| Wallet load filterable | ✅ PASS |

---

## Test Credentials
- **User Login:** `testclient` / `test123` (₹999.01 wallet)
- **Admin Login:** `admin` / `admin123`

---

## Technical Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI app with all endpoints (integer currency)
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main router with auth context
│   │   ├── index.css     # Global styles with Garena theme
│   │   ├── pages/        # All page components (light theme)
│   │   │   ├── AdminOrders.js  # All orders with filters, view/edit modal
│   │   │   ├── AdminReview.js  # Manual review queue
│   │   │   └── ...
│   │   └── components/   # Shadcn UI components
│   ├── tailwind.config.js # Tailwind with Garena colors
│   └── package.json
├── tests/
│   ├── test_freefire_topup.py              # Basic API tests (26)
│   └── test_price_update_and_admin_orders.py # Price & admin tests (16)
├── test_reports/
│   ├── iteration_2.json
│   └── iteration_3.json
└── memory/
    └── PRD.md            # This file
```

### Key API Endpoints
- `/api/auth/signup`, `/api/auth/login` - User auth
- `/api/admin/login` - Admin auth
- `/api/packages/list` - Public packages list (fresh, no cache)
- `/api/admin/packages/{id}` - Admin package CRUD (price_rupees -> price_paisa)
- `/api/admin/orders` - Admin orders list (supports order_type, status filters)
- `/api/admin/orders/{id}` - GET order details, PUT update order
- `/api/admin/orders/{id}/retry` - Retry failed order
- `/api/admin/orders/{id}/mark-success` - Manual completion
- `/api/orders/create` - Create product_topup order (uses current package price_paisa)
- `/api/orders/wallet-load` - Create wallet_load order
- `/api/user/orders` - User order list
- `/api/user/wallet` - User wallet with transactions

---

## Pending/Future Tasks

### P1 - High Priority
- [ ] End-to-end automation testing with real Garena site
- [ ] SMS auto-forwarding from Android app integration

### P2 - Medium Priority
- [ ] Order expiry job (mark orders as expired after 24h)
- [ ] Suspicious SMS detection (unmatched for >1 hour)
- [ ] Rate limiting on API endpoints

### P3 - Future/Backlog
- [ ] Admin action audit logging UI
- [ ] Automation queue with retry logic and failover
- [ ] Build and distribute Android SMS Forwarder APK
- [ ] Code refactoring: split server.py into multiple routers

---

## Android SMS Forwarder App

Located at `/app/android-sms-forwarder/`

### Features
- Auto-detects payment SMS (FonePay, eSewa, Khalti, bank transfers)
- Instant forwarding to DiamondStore server
- Background service with foreground notification
- Auto-start on device boot
- Connection testing
- Retry mechanism for failed forwards

### Setup
1. Open in Android Studio
2. Sync Gradle
3. Build → Generate Signed APK (or Run for debug)
4. Install APK on Android device
5. Grant SMS & notification permissions
6. Enter server URL: `https://garena-credits.preview.emergentagent.com`
7. Tap "Test Connection"
8. Enable SMS Forwarding switch
