# DiamondStore SMS Forwarder

Android app that automatically forwards payment SMS to your DiamondStore server for instant payment verification.

## Features

- ✅ Auto-detects payment SMS (FonePay, eSewa, Khalti, IME Pay, bank transfers)
- ✅ Instantly forwards to your server
- ✅ Runs in background with foreground service
- ✅ Auto-starts on device boot
- ✅ Tracks forwarded message count
- ✅ Test connection feature
- ✅ Retry mechanism for failed forwards

## Requirements

- Android 7.0 (API 24) or higher
- Android Studio Arctic Fox or newer
- JDK 17

## Build Instructions

### Option 1: Build with Android Studio

1. Open Android Studio
2. Select "Open an existing project"
3. Navigate to this folder and open it
4. Wait for Gradle sync to complete
5. Connect your Android device or start an emulator
6. Click "Run" (green play button) or press Shift+F10

### Option 2: Build from Command Line

```bash
# Navigate to project directory
cd android-sms-forwarder

# Build debug APK
./gradlew assembleDebug

# The APK will be at:
# app/build/outputs/apk/debug/app-debug.apk
```

### Option 3: Build Release APK

```bash
# Create signing key (first time only)
keytool -genkey -v -keystore my-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias my-alias

# Build release APK
./gradlew assembleRelease
```

## Installation

1. Build the APK using one of the methods above
2. Transfer APK to your Android device
3. Enable "Install from unknown sources" in Settings
4. Install the APK
5. Grant SMS permission when prompted
6. Grant notification permission (Android 13+)

## Setup

1. Open the DiamondStore SMS app
2. Enter your server URL (e.g., `https://garena-credits.preview.emergentagent.com`)
3. Tap "Save"
4. Tap "Test Connection" to verify
5. Enable "SMS Forwarding" switch
6. Keep the app running in background

## How It Works

1. App listens for incoming SMS messages
2. When SMS arrives, it checks for payment keywords:
   - `received`, `credited`, `deposited`
   - `payment`, `transfer`
   - `fonepay`, `esewa`, `khalti`, `imepay`
   - `Rs`, `NPR`, `RRN`
3. If payment SMS detected, it forwards to your server's `/api/sms/receive` endpoint
4. Server parses the SMS and matches it to pending orders
5. Order status is automatically updated

## SMS Format Support

The app and server support various SMS formats:

```
Rs 100.00 received from 98XXXXX910 for RRN 123456789, DiamondStore /FonePay
```

```
NPR 500 credited to your account from 900****123. Ref: ABC123456. Balance: NPR 1500
```

```
Payment of Rs 250.00 received via eSewa. Transaction ID: ES123456789
```

## Permissions Required

- **RECEIVE_SMS** - To receive SMS messages
- **READ_SMS** - To read SMS content
- **INTERNET** - To forward SMS to server
- **FOREGROUND_SERVICE** - To run in background
- **POST_NOTIFICATIONS** - To show service notification (Android 13+)
- **RECEIVE_BOOT_COMPLETED** - To auto-start on boot

## Troubleshooting

### SMS not being forwarded?

1. Check if SMS permission is granted
2. Verify forwarding is enabled (green switch)
3. Check if server URL is correct
4. Test connection to verify server is reachable
5. Check if SMS contains payment keywords

### App stops after some time?

1. Disable battery optimization for this app
2. Add app to "Don't optimize" list
3. Some manufacturers (Xiaomi, Huawei) have aggressive battery saving - check manufacturer-specific settings

### Connection test fails?

1. Verify server URL is correct (include https://)
2. Check if device has internet connection
3. Verify server is running and accessible

## Security Notes

- SMS content is sent only to your configured server
- No data is stored on external servers
- Server URL is stored locally on device
- Use HTTPS for secure communication

## Server API Endpoint

The app sends POST requests to `/api/sms/receive`:

```json
{
  "raw_message": "From: +9779812345678\nRs 100.00 received from 98XXXXX910 for RRN 123456789, DiamondStore /FonePay"
}
```

## License

MIT License - Use freely for your DiamondStore deployment.
