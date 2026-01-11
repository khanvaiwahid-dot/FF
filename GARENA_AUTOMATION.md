# Garena Automation Integration Guide

## Overview

The Free Fire diamonds top-up platform now includes full integration with the official Garena shop (https://shop.garena.my/) for automated diamond delivery.

## Automation Flow

The system uses Playwright browser automation to complete diamond purchases on the Garena shop. The automation follows these exact steps:

### Step-by-Step Process

1. **Open Garena Shop**
   - Navigate to https://shop.garena.my/
   - Wait for page load

2. **Select FreeFire**
   - Find and click on FreeFire game option
   - Wait for game page to load

3. **Insert Player ID (UID)**
   - Locate UID input field
   - Fill in the customer's Player UID from order
   - Verify input is visible

4. **Select Redeem Option**
   - Click on "Redeem" option if available
   - This step may be optional depending on UI

5. **Login Check**
   - Check if already logged in
   - If not, proceed with login:
     - Email: thenexkshetriempire01@gmail.com
     - Password: Theone164@
   - Wait for login completion

6. **Proceed to Payment**
   - Click "Proceed" or "Continue" button
   - Navigate to payment selection page

7. **Select Amount**
   - Find diamond package matching order
   - Click on the correct diamond amount (100, 310, 520, etc.)
   - Verify selection

8. **Select Wallet**
   - Choose "Wallet" as payment method
   - Wait for wallet options to load

9. **Select UP Points**
   - Choose "UP Points" as wallet type
   - Proceed to payment confirmation

10. **Authentication (if required)**
    - Enter login credentials if prompted:
      - ID: thenexkshetriempire01@gmail.com
      - Password: Theone164@

11. **Security PIN**
    - Enter security PIN: 164164
    - This confirms the transaction

12. **Confirm Purchase**
    - Click final "Confirm" or "Purchase" button
    - Wait for transaction processing

13. **Verify Success**
    - Look for success indicators:
      - Success message
      - Completion text
      - Success page elements
    - Mark order as complete

## Automation States

The system tracks automation progress through these states:

- `INIT` - Automation initialized
- `OPEN_SITE` - Opening Garena shop
- `INPUT_UID` - Entering Player UID
- `SELECT_PACKAGE` - Selecting diamond package
- `CONFIRM_PURCHASE` - Confirming purchase
- `VERIFY_SUCCESS` - Verifying transaction
- `DONE` - Successfully completed
- `FAILED` - Automation failed

## Credentials Configuration

**Garena Account:**
- Email: thenexkshetriempire01@gmail.com
- Password: Theone164@
- Security PIN: 164164

⚠️ **Security Note:** These credentials are hardcoded in the backend. For production, consider:
- Using environment variables
- Implementing credential rotation
- Adding multi-account support
- Using a secrets manager

## Error Handling

The automation includes comprehensive error handling:

1. **Login Detection**
   - Automatically detects if login is required
   - Handles both pre-logged and logged-out states

2. **Element Not Found**
   - Waits up to 10 seconds for elements
   - Logs detailed error messages
   - Marks order for manual review

3. **Transaction Verification**
   - Waits up to 15 seconds for success confirmation
   - Multiple success indicator checks
   - Falls back to manual review if uncertain

4. **Retry Logic**
   - Failed orders can be retried up to 3 times
   - Each retry is logged
   - After 3 failures, marked for manual admin review

## Testing the Automation

### Manual Testing

Use the provided test script:

```bash
cd /app
python3 test_automation.py
```

This will:
1. Create or find a test order
2. Display order details
3. Give you 10 seconds to cancel
4. Run the automation with browser visible
5. Report success or failure

### Important for Testing

- Use a **real Free Fire Player UID** for testing
- Ensure the Garena account has sufficient UP Points
- The browser runs in **headed mode** (visible) for debugging
- Watch the automation progress in real-time

### Testing with Real Orders

1. Create a real order through the UI
2. Complete payment verification
3. Order will automatically enter the queue
4. Watch admin panel for order status updates
5. Check automation_state field for progress

## Monitoring Automation

### Check Automation Status

Via Admin Panel:
- Go to Admin Dashboard
- View orders in "Processing" state
- Check automation_state field
- Monitor for failed orders

Via Database:
```bash
# Connect to MongoDB
mongo mongodb://localhost:27017/free_fire_topup

# Check processing orders
db.orders.find({status: "processing"})

# Check failed orders
db.orders.find({status: "failed"})
```

### Backend Logs

Check automation logs:
```bash
# View backend logs
tail -f /var/log/supervisor/backend.out.log

# Check for automation errors
tail -f /var/log/supervisor/backend.err.log | grep "automation"
```

## Troubleshooting

### Common Issues

1. **UID Input Not Found**
   - Garena site may have updated UI
   - Check selector: `input[placeholder*="ID"]`
   - Update selector in code if needed

2. **Login Required Every Time**
   - Cookies may not be persisting
   - Consider using persistent browser context
   - May need to handle session management

3. **Package Selection Fails**
   - Package name/amount may not match exactly
   - Check Garena site for current package names
   - Update selectors if UI changed

4. **Success Verification Timeout**
   - Transaction may take longer than 15 seconds
   - Increase timeout if needed
   - Check for alternative success indicators

5. **Security PIN Prompt**
   - PIN input location may vary
   - Check selector: `input[type="password"]`
   - May need more specific selector

### Debugging Steps

1. **Run in Headed Mode**
   - Browser is visible by default
   - Watch automation progress
   - Pause at any step to inspect

2. **Check Selectors**
   - Use browser DevTools
   - Inspect element selectors
   - Update code if UI changed

3. **Increase Timeouts**
   - If elements load slowly
   - Adjust wait_for_selector timeouts
   - Add explicit waits with asyncio.sleep()

4. **Review Logs**
   - Check backend logs for errors
   - Look for "automation error" messages
   - Note which step failed

## Production Considerations

### Before Going Live

1. **Test Thoroughly**
   - Test with multiple UIDs
   - Test all diamond packages
   - Verify success detection

2. **Monitor Initially**
   - Watch first 10-20 orders manually
   - Check success rate
   - Identify any patterns in failures

3. **Set Up Alerts**
   - Alert on high failure rate
   - Alert on stuck orders
   - Alert on automation exceptions

4. **Backup Plan**
   - Train admin on manual completion
   - Document manual top-up process
   - Keep manual review queue monitored

### Security Best Practices

1. **Credential Management**
   - Move credentials to environment variables
   - Use secrets management service
   - Implement credential rotation

2. **Account Security**
   - Enable 2FA on Garena account
   - Monitor account for suspicious activity
   - Keep backup authentication method

3. **Rate Limiting**
   - Don't process too many orders simultaneously
   - Add delays between orders if needed
   - Monitor for account restrictions

### Scalability

For high volume:

1. **Multiple Accounts**
   - Use multiple Garena accounts
   - Distribute orders across accounts
   - Implement account rotation

2. **Parallel Processing**
   - Run multiple automation instances
   - Use separate browser contexts
   - Implement proper queue management

3. **Failure Recovery**
   - Automatic retry on transient failures
   - Exponential backoff
   - Dead letter queue for persistent failures

## API Integration

The automation is triggered automatically when:
- Order status becomes "paid"
- Payment verification completes
- Order enters the processing queue

Manual trigger via API:
```bash
POST /api/admin/orders/{order_id}/retry
Authorization: Bearer <admin_token>
```

## Success Criteria

An order is marked successful when:
1. All automation steps complete without errors
2. Success indicator found on Garena site
3. Order status updated to "success"
4. Completed timestamp recorded

## Support

For issues with automation:
1. Check order status and automation_state
2. Review backend logs
3. Verify Garena account status
4. Test with manual automation script
5. Contact development team if issue persists

---

**Last Updated:** January 2025
**Garena Site:** https://shop.garena.my/
**Automation Engine:** Playwright (Chromium)
