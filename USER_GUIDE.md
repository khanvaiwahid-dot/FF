# User Guide - Free Fire Diamonds Top-Up Platform

## For Users (Players)

### 1. Getting Started

**Create Your Account:**
1. Visit the platform and click "Sign up"
2. Choose a unique username (⚠️ Cannot be changed later!)
3. Provide either email or phone number
4. Create a strong password
5. Click "Create Account"

**Login:**
1. Enter your username, email, or phone
2. Enter your password
3. Click "Sign In"

### 2. Buying Diamonds

**Step 1: Select Package**
1. On the main page, you'll see your wallet balance
2. Enter your Free Fire Player UID
3. Optionally enter your server (e.g., India, Global)
4. Choose a diamond package:
   - 100 Diamonds - ₹1.50
   - 310 Diamonds - ₹4.50
   - 520 Diamonds - ₹7.50
   - 1060 Diamonds - ₹15.00
   - 2180 Diamonds - ₹30.00
   - 5600 Diamonds - ₹75.00

**Step 2: Review & Order**
1. Check the order summary
2. See how much will be deducted from wallet (if any)
3. See how much payment is required
4. Click "Continue to Payment"

**Step 3: Payment**
1. Send the exact amount to our payment account
2. Fill in the payment verification form:
   - Amount sent
   - Last 3 digits of your phone (linked to payment account)
   - Payment method (PhonePe, GPay, Paytm, etc.)
   - Payment remark (optional)
   - Screenshot URL (optional)
3. Click "Check Payment"

**Step 4: Wait for Processing**
- Your payment will be automatically verified
- Order status will update in real-time
- Diamonds will be added to your account automatically
- Check order status page for updates

### 3. Using Wallet

**View Wallet:**
1. Click on wallet card or wallet icon in navigation
2. See your current balance
3. View transaction history

**Add Funds to Wallet:**
1. Click "Add Funds" button
2. Enter amount to add
3. Complete payment verification (same as order payment)
4. Funds will be added after verification

**Benefits:**
- Faster checkout for future orders
- Pay partially with wallet + payment
- No need to pay full amount each time

### 4. Order Status

Your order can be in these states:
- **Pending Payment** ⏳ - Waiting for you to complete payment
- **Paid** ✓ - Payment received, order in queue
- **Processing** 🔄 - Diamonds being added to your account
- **Success** ✅ - Diamonds delivered!
- **Under Review** 👀 - Manual verification needed (usually resolves in minutes)

### 5. Tips for Smooth Experience

✓ **Always enter correct Player UID** - Double check before creating order
✓ **Send exact amount** - Don't round up or down
✓ **Use correct last 3 digits** - From phone linked to your payment account
✓ **Keep transaction reference** - RRN or transaction ID from payment
✓ **Wait for confirmation** - Don't create multiple orders for same thing
✓ **Check order status** - Real-time updates available

### 6. Common Issues

**Payment not matching:**
- Check if you entered correct last 3 digits
- Verify amount sent matches order amount
- Wait a few minutes for SMS to arrive
- If still not matched, admin will review manually

**Order stuck in processing:**
- Usually resolves automatically
- If stuck more than 10 minutes, contact support
- Admin can manually complete if needed

**Diamonds not received:**
- Check order status is "Success"
- Restart Free Fire game
- Check correct Player UID was used
- Contact support if issue persists

## For Admins

### 1. Admin Login

1. Go to login page and click "Admin Login"
2. Enter admin username: `admin`
3. Enter admin password: `admin123`
4. ⚠️ **Change password immediately after first login!**

### 2. Dashboard

**Overview:**
- Total sales amount
- Total orders count
- Failed/suspicious orders
- Total wallet balance held

**Quick Actions:**
- Manage Orders - View and manage all orders
- Manual Review - Orders needing attention
- Payment Inbox - Unmatched payments

### 3. Order Management

**View All Orders:**
- Search by order ID, username, or UID
- Filter by status (success, pending, failed, etc.)
- View order details

**Retry Failed Orders:**
1. Find failed order
2. Click "Retry" button
3. Order will be added back to queue
4. Automation will attempt again

**Manual Completion:**
1. If automation fails multiple times
2. Verify diamonds were added manually
3. Click "Complete" button
4. Order marked as success

### 4. Manual Review Queue

**What's Here:**
- Failed orders
- Suspicious transactions
- Duplicate payments
- Orders needing manual verification

**Actions:**
1. Review order details
2. Check payment information
3. Verify with user if needed
4. Either retry automation or manually complete

### 5. Payment Inbox

**Unmatched Payments:**
- SMS messages that couldn't auto-match
- Payment details (amount, last3, RRN, method)
- Raw SMS message

**How to Handle:**
1. Review payment details
2. Search for matching pending order
3. Contact user if needed
4. Manually match or mark as resolved

### 6. Best Practices

✓ **Monitor dashboard regularly** - Stay on top of failed orders
✓ **Review inbox daily** - Don't let unmatched payments pile up
✓ **Act on manual review** - Quick resolution improves user trust
✓ **Keep logs** - All actions are logged automatically
✓ **Change default password** - Security first!
✓ **Communicate with users** - If issues arise, let them know

### 7. Admin Responsibilities

**Daily Tasks:**
- Check dashboard for anomalies
- Review failed/suspicious orders
- Clear payment inbox
- Monitor automation success rate

**Weekly Tasks:**
- Review sales trends
- Check wallet balance trends
- Analyze common failure reasons
- Update packages if needed

**Security:**
- Never share admin credentials
- Log out when done
- Monitor for suspicious patterns
- Keep action logs clean

## SMS Integration Setup

### For Developers

**SMS Webhook:**
```
POST /api/sms/receive
Content-Type: application/json

{
  "raw_message": "You have received Rs 125.00 from 900****910 for RRN 11672918bccl, cake /FonepayQR"
}
```

**SMS Message Format:**
The system parses messages in this format:
```
You have received Rs {amount} from {masked_phone} for RRN {transaction_id}, {remark} /{payment_method}
```

**What Gets Parsed:**
- Amount: Numerical value after "Rs"
- Last 3 digits: Last 3 digits from masked phone
- RRN: Transaction ID (used for duplicate prevention)
- Remark: Text before "/"
- Payment Method: Text after "/"

**Auto-Matching:**
System automatically matches SMS to orders based on:
1. Amount matches payment_amount
2. Last 3 digits match
3. RRN not previously used
4. Order in valid state (pending_payment, wallet_partial_paid, manual_review)

## Troubleshooting

### User Issues

**"Order stuck in pending payment"**
→ Complete payment verification form on order status page

**"Payment not matched"**
→ Check last 3 digits, amount, and wait few minutes for SMS

**"Wallet balance not updating"**
→ Refresh page or logout/login again

**"Can't change username"**
→ Usernames are permanent by design (security feature)

### Admin Issues

**"Can't login as admin"**
→ Use separate admin login page, not user login

**"Order automation failing"**
→ Check automation logs, retry manually if needed

**"Too many unmatched payments"**
→ Review SMS format, check parsing logic

**"Dashboard stats not updating"**
→ Refresh page, check database connection

## Security & Privacy

### User Data
- Passwords are encrypted (bcrypt)
- Only username is public
- Email/phone kept private
- Payment details only for matching

### Payment Security
- RRN prevents duplicate usage
- Amount verification required
- Manual review for suspicious patterns
- All transactions logged

### Admin Security
- Separate authentication
- All actions logged
- Password reset available
- Role-based access

## Need Help?

**For Users:**
- Check order status page for updates
- Review this guide
- Contact support through admin

**For Admins:**
- Check admin action logs
- Review payment inbox
- Check automation logs
- Consult technical documentation

---

**Platform Version:** 1.0.0  
**Last Updated:** January 2025
