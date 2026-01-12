# SMS Forwarder Android App

## Overview
Android app that automatically reads incoming SMS payment notifications and forwards them to the backend API for automatic payment matching.

## Features
- ✅ Real-time SMS reading via BroadcastReceiver
- ✅ Smart parsing of payment SMS (amount, RRN, sender)
- ✅ Secure API token storage (EncryptedSharedPreferences)
- ✅ Offline queue with automatic retry (WorkManager)
- ✅ Duplicate prevention (SHA-256 fingerprint)
- ✅ Configurable keyword filters
- ✅ Works after device reboot
- ✅ Clean UI with Status/Settings/Logs tabs

## Supported SMS Format
```
You have received Rs 125.00 from 900****910 for RRN 11672918bccl, cake /FonepayQR.
For QR support, toll-free no: 18105000131
```

### Parsed Fields:
- **amount**: Rs 125.00 → 12500 paisa
- **last3digits**: 910 (from masked sender)
- **rrn**: 11672918bccl
- **remark**: cake (optional)
- **method**: FonepayQR (optional)

## Build Instructions

### Prerequisites
- Android Studio Arctic Fox or newer
- JDK 17
- Android SDK 34

### Steps

1. **Open in Android Studio**
   ```bash
   cd /app/android-sms-forwarder
   # Open this folder in Android Studio
   ```

2. **Sync Gradle**
   - Android Studio will prompt to sync Gradle
   - Click "Sync Now" or File → Sync Project with Gradle Files

3. **Build Debug APK**
   ```bash
   # From command line:
   ./gradlew assembleDebug
   
   # APK location:
   # app/build/outputs/apk/debug/app-debug.apk
   ```

4. **Build Release APK** (requires signing key)
   ```bash
   ./gradlew assembleRelease
   ```

### Install APK

**Via ADB:**
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

**Manual:**
1. Copy APK to device
2. Enable "Install from unknown sources"
3. Open APK file to install

## Configuration

### In-App Setup (Settings Tab)

1. **Backend URL**: Enter your backend URL
   - Example: `https://your-app.emergent.app`
   - Must include protocol (http:// or https://)

2. **API Token**: Enter the SMS Forwarder token
   - Get this from your backend `.env` file: `SMS_FORWARDER_TOKEN`
   - Default: `sms-forwarder-secure-token-2024`

3. **Filter Keywords**: Comma-separated list of keywords
   - Default: `You have received,RRN,FonepayQR,Fonepay`
   - Only SMS containing at least one keyword will be captured

4. Click **Save Settings**

5. Go to **Status** tab and enable **SMS Forwarding**

### Permissions Required
- **RECEIVE_SMS**: Read incoming SMS
- **READ_SMS**: Access SMS content
- **INTERNET**: Send data to backend
- **POST_NOTIFICATIONS** (Android 13+): Show service notification

## Backend API

The app sends SMS to: `POST {BASE_URL}/api/sms/ingest`

### Request Format
```json
{
  "raw_message": "You have received Rs 125.00...",
  "sender": "BankName",
  "received_at": "2024-01-12T10:30:00.000Z",
  "amount_paisa": 12500,
  "last3digits": "910",
  "rrn": "11672918bccl",
  "remark": "cake",
  "method": "FonepayQR",
  "sms_fingerprint": "sha256_hash",
  "device_id": "uuid",
  "app_version": "1.0.0"
}
```

### Response Format
```json
// Success
{"ok": true, "status": "accepted", "matched": true}

// Duplicate
{"ok": false, "status": "duplicate", "reason": "fingerprint_exists"}
```

## Test Checklist

- [ ] App installs successfully
- [ ] Permissions are granted
- [ ] Backend URL and token saved
- [ ] Forwarding enabled
- [ ] Send test SMS from Settings tab
- [ ] Check Logs tab - event appears as "pending"
- [ ] Event changes to "sent" after successful forward
- [ ] Backend receives SMS (check admin panel)
- [ ] Duplicate SMS not resent
- [ ] App works after device reboot
- [ ] Offline mode: SMS queued, sent when online

## Troubleshooting

### SMS not captured
- Check if forwarding is enabled (Status tab)
- Verify keywords match your bank's SMS format
- Check if SMS permissions are granted
- Try adding more keywords that match your SMS

### Failed to send
- Check backend URL is correct
- Verify API token matches backend
- Check device has internet connection
- View error message in Logs tab

### Auth Error
- Token mismatch - check `SMS_FORWARDER_TOKEN` in backend `.env`
- Restart backend after changing token

## Security Notes

- API token stored in EncryptedSharedPreferences
- SMS fingerprint prevents replay attacks
- RRN uniqueness enforced on backend
- HTTPS recommended for production

## File Structure
```
app/src/main/java/com/diamondstore/smsforwarder/
├── SMSForwarderApp.kt          # Application class
├── MainActivity.kt             # Main activity with tabs
├── data/
│   ├── AppDatabase.kt          # Room database
│   ├── SmsEvent.kt             # SMS event entity
│   └── SmsEventDao.kt          # Database operations
├── network/
│   └── ApiClient.kt            # HTTP client
├── receiver/
│   ├── SMSReceiver.kt          # SMS broadcast receiver
│   └── BootReceiver.kt         # Boot completed receiver
├── ui/
│   ├── MainPagerAdapter.kt     # ViewPager adapter
│   ├── StatusFragment.kt       # Status tab
│   ├── SettingsFragment.kt     # Settings tab
│   ├── LogsFragment.kt         # Logs tab
│   └── SmsEventAdapter.kt      # RecyclerView adapter
├── util/
│   ├── SMSParser.kt            # SMS parsing logic
│   └── PrefsManager.kt         # Preferences manager
└── worker/
    └── SMSForwardWorker.kt     # Background sync worker
```

## Version History

- **1.0.0** - Initial release
  - SMS reading and forwarding
  - Room database for offline queue
  - WorkManager for reliable sync
  - 3-tab UI (Status/Settings/Logs)
