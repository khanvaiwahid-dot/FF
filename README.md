# Free Fire Diamonds Top-Up Platform

A fully automated platform for Free Fire diamonds top-up with SMS-based payment verification, wallet system, and comprehensive admin panel.

## 🚀 Features

### User Features
- **User Authentication**: Unique username-based signup (permanent username)
- **Diamond Packages**: 6 fixed packages (100, 310, 520, 1060, 2180, 5600 diamonds)
- **Wallet System**: 
  - Add funds via payment verification
  - Use wallet balance for full or partial payments
  - Transaction history tracking
- **Order Management**: 
  - Real-time order status tracking
  - 11 order states (pending_payment, paid, queued, processing, etc.)
  - Auto-updating order status page
- **Payment Verification**: Submit payment details for automatic matching

### Admin Features
- **Separate Admin Authentication**: Secure admin login system
- **Dashboard**: 
  - Real-time statistics (sales, orders, failed/suspicious counts)
  - Visual charts for order status breakdown
  - Wallet balance monitoring
- **Order Management**: 
  - View all orders with filtering and search
  - Retry failed orders
  - Manually complete orders
- **Manual Review Queue**: Orders requiring admin attention
- **Payment Inbox**: Unmatched SMS payments
- **Action Logs**: Complete audit trail

### Technical Features
- **SMS Payment Detection**: Parse payment messages from phone/emulator
- **Browser Automation**: Playwright-based Garena top-up automation
- **Queue System**: Automated order processing with retry logic
- **Duplicate Prevention**: RRN-based duplicate payment detection
- **11 Order States**: Comprehensive order lifecycle management

## 📋 Order States

1. `pending_payment` - Waiting for payment
2. `paid` - Payment confirmed
3. `queued` - In processing queue
4. `processing` - Being processed by automation
5. `wallet_partial_paid` - Partially paid via wallet
6. `wallet_fully_paid` - Fully paid via wallet
7. `success` - Successfully completed
8. `failed` - Processing failed
9. `manual_review` - Requires admin review
10. `suspicious` - Flagged as suspicious
11. `duplicate_payment` - Duplicate payment detected
12. `expired` - Order expired

## 🛠 Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React 19
- **Database**: MongoDB
- **UI Library**: Shadcn/UI with Tailwind CSS
- **Automation**: Playwright (Chromium)
- **Authentication**: JWT tokens

## 🎨 Design System

- **Theme**: Cosmic Neon (Dark Mode)
- **Primary Color**: Electric Cyan (#00F0FF)
- **Secondary Color**: Magenta (#B026FF)
- **Accent Color**: Gold (#FFBA00)
- **Fonts**: 
  - Headings: Chivo
  - Body: Manrope
  - Mono: JetBrains Mono

## 🔐 Default Credentials

**Admin Account**:
- Username: `admin`
- Password: `admin123`

⚠️ **Important**: Change admin password immediately after first login!

## 📦 Installation & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Yarn package manager

### Backend Setup
```bash
cd /app/backend

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set environment variables in .env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="free_fire_topup"
JWT_SECRET="your-secure-secret-key"

# Initialize database with default data
curl -X POST http://localhost:8001/api/admin/init
```

### Frontend Setup
```bash
cd /app/frontend

# Install dependencies
yarn install

# Start development server
yarn start
```

## 🔄 SMS Payment Flow

### Message Format
```
You have received Rs 125.00 from 900****910 for RRN 11672918bccl, cake /FonepayQR
```

### Parsed Fields
- **Amount**: Rs 125.00
- **Last 3 Digits**: 910
- **RRN**: 11672918bccl (unique transaction ID)
- **Remark**: cake
- **Payment Method**: FonepayQR

### Integration
Send SMS to webhook endpoint:
```bash
POST /api/sms/receive
{
  "raw_message": "You have received Rs 125.00 from 900****910 for RRN 11672918bccl, cake /FonepayQR"
}
```

## 🤖 Automation System

### Playwright Automation States
1. `INIT` - Initialize browser
2. `OPEN_SITE` - Open Garena shop
3. `INPUT_UID` - Check and input Player UID
4. `SELECT_SERVER` - Select server (if needed)
5. `SELECT_PACKAGE` - Select diamond package
6. `CONFIRM_PURCHASE` - Confirm purchase
7. `VERIFY_SUCCESS` - Verify completion
8. `DONE` / `FAILED` - Final state

### Critical Rule
**Never reuse old UID sessions**:
- After opening site, check if UID input is visible
- If not visible → logout/switch account
- Confirm UID input appears before proceeding
- If logout fails → mark order for manual review

## 📡 API Endpoints

### Authentication
- `POST /api/auth/signup` - User signup
- `POST /api/auth/login` - User login
- `POST /api/auth/reset-password` - Reset password
- `POST /api/admin/login` - Admin login
- `POST /api/admin/reset-password` - Admin password reset

### User Endpoints
- `GET /api/user/profile` - Get user profile
- `GET /api/user/wallet` - Get wallet & transactions

### Orders
- `GET /api/packages/list` - List diamond packages
- `POST /api/orders/create` - Create order
- `GET /api/orders/{order_id}` - Get order details
- `GET /api/orders/list/user` - List user orders
- `POST /api/orders/verify-payment` - Verify payment

### SMS
- `POST /api/sms/receive` - Receive SMS message (webhook)

### Admin
- `GET /api/admin/dashboard` - Dashboard statistics
- `GET /api/admin/orders` - List all orders
- `POST /api/admin/orders/{order_id}/retry` - Retry automation
- `POST /api/admin/orders/{order_id}/complete-manual` - Manual completion
- `GET /api/admin/payments/inbox` - Unmatched payments
- `GET /api/admin/action-logs` - Admin action logs

## 📱 Mobile-First Design

The platform is optimized for mobile devices with:
- Responsive layouts
- Bottom navigation
- Touch-friendly buttons
- Swipeable cards
- Optimized forms

## 🔒 Security Features

- JWT-based authentication
- Separate admin authentication
- Password hashing with bcrypt
- RRN-based duplicate prevention
- Input validation
- Action audit logging

## 🎯 UX Principles

- **Friendly Language**: No technical error codes shown to users
- **Clear Feedback**: Toast notifications for all actions
- **Real-time Updates**: Auto-refreshing order status
- **Progressive Disclosure**: Show only relevant information
- **Mobile-First**: Optimized for mobile gaming audience

## 🧪 Testing

Run comprehensive tests:
```bash
# Backend tests
pytest /app/backend/tests

# Frontend tests
cd /app/frontend
yarn test

# E2E tests
Use testing agent for complete flow testing
```

## 📊 Database Schema

### Users Collection
- id, username, email, phone, password_hash, wallet_balance, created_at

### Orders Collection
- id, user_id, username, player_uid, server, package_name, diamonds, amount
- wallet_used, payment_amount, payment_last3digits, payment_method, payment_remark
- payment_screenshot, payment_rrn, raw_message, status, automation_state
- retry_count, created_at, updated_at, completed_at

### Packages Collection
- id, name, diamonds, price, active

### SMS Messages Collection
- id, raw_message, amount, last3digits, rrn, method, remark
- parsed_at, used, matched_order_id

### Wallet Transactions Collection
- id, user_id, type, amount, order_id, payment_id
- balance_before, balance_after, created_at

### Admin Actions Collection
- id, admin_id, action_type, target_id, details, created_at

## 🚨 Important Notes

1. **Username is Permanent**: Users cannot change their username after signup
2. **Wallet Cannot Withdraw**: Wallet funds can only be used for orders
3. **RRN Uniqueness**: Each payment RRN can only be used once
4. **Automation Requirements**: Playwright automation needs real Garena site integration
5. **Admin Password**: Change default admin password immediately
6. **Environment Variables**: Never commit .env files with real secrets

## 🔮 Future Enhancements

- Email/SMS notifications for order status
- Multi-language support
- Referral system
- Loyalty rewards
- Payment gateway integration (Stripe/Razorpay)
- Mobile app (React Native)
- Customer support chat
- Analytics dashboard

## 📞 Support

For issues or questions:
1. Check order status in admin panel
2. Review payment inbox for unmatched payments
3. Check admin action logs for audit trail
4. Retry failed orders from admin panel
5. Manually complete orders if automation fails

## 📄 License

Proprietary - All rights reserved

---

Built with ❤️ for Free Fire gamers
