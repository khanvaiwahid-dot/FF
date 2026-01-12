package com.diamondstore.smsforwarder.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.diamondstore.smsforwarder.SMSForwarderApp
import com.diamondstore.smsforwarder.data.SmsEvent
import com.diamondstore.smsforwarder.util.PrefsManager
import com.diamondstore.smsforwarder.util.SMSParser
import com.diamondstore.smsforwarder.worker.SMSForwardWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SMSReceiver : BroadcastReceiver() {
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            return
        }
        
        val prefs = PrefsManager.getInstance(context)
        
        // Check if forwarding is enabled
        if (!prefs.forwardingEnabled) {
            Log.d(TAG, "SMS forwarding is disabled, ignoring")
            return
        }
        
        // Check if configured
        if (!prefs.isConfigured()) {
            Log.d(TAG, "App not configured, ignoring SMS")
            return
        }
        
        // Extract SMS messages
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) {
            Log.d(TAG, "No messages in intent")
            return
        }
        
        // Combine multi-part messages
        val sender = messages[0].originatingAddress
        val fullMessage = messages.joinToString("") { it.messageBody ?: "" }
        val timestamp = messages[0].timestampMillis
        
        Log.d(TAG, "Received SMS from $sender: $fullMessage")
        
        // Check if message matches keywords
        val keywords = prefs.getKeywordsList()
        if (!SMSParser.matchesKeywords(fullMessage, keywords)) {
            Log.d(TAG, "SMS does not match keywords, ignoring")
            return
        }
        
        Log.d(TAG, "SMS matches keywords, processing...")
        
        // Parse message
        val parsed = SMSParser.parse(fullMessage)
        val fingerprint = SMSParser.generateFingerprint(sender, fullMessage, timestamp)
        val receivedAt = SMSParser.getISO8601Timestamp()
        
        // Create SMS event
        val event = SmsEvent(
            rawMessage = fullMessage,
            sender = sender,
            receivedAt = receivedAt,
            amountPaisa = parsed.amountPaisa,
            last3digits = parsed.last3digits,
            rrn = parsed.rrn,
            remark = parsed.remark,
            method = parsed.method,
            fingerprint = fingerprint,
            status = "pending"
        )
        
        // Save to database and trigger worker
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val database = SMSForwarderApp.instance.database
                
                // Check if duplicate (by fingerprint)
                val existing = database.smsEventDao().getByFingerprint(fingerprint)
                if (existing != null) {
                    Log.d(TAG, "Duplicate SMS detected by fingerprint, ignoring")
                    return@launch
                }
                
                // Insert new event
                val id = database.smsEventDao().insert(event)
                if (id > 0) {
                    Log.d(TAG, "SMS saved with ID: $id, triggering forward worker")
                    SMSForwardWorker.enqueue(context)
                } else {
                    Log.d(TAG, "SMS insert returned $id (possible duplicate)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error saving SMS: ${e.message}", e)
            }
        }
    }
    
    companion object {
        private const val TAG = "SMSReceiver"
    }
}
