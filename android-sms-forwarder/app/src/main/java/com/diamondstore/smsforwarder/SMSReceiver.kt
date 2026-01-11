package com.diamondstore.smsforwarder

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log

class SMSReceiver : BroadcastReceiver() {
    
    companion object {
        private const val TAG = "SMSReceiver"
        
        // Keywords to filter payment SMS
        private val PAYMENT_KEYWORDS = listOf(
            "received",
            "credited",
            "deposited",
            "payment",
            "transfer",
            "fonepay",
            "esewa",
            "khalti",
            "imepay",
            "Rs",
            "NPR",
            "RRN"
        )
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            return
        }
        
        val prefs = context.getSharedPreferences("sms_forwarder", Context.MODE_PRIVATE)
        val isEnabled = prefs.getBoolean("forwarding_enabled", false)
        val apiUrl = prefs.getString("api_url", "") ?: ""
        
        if (!isEnabled || apiUrl.isEmpty()) {
            Log.d(TAG, "Forwarding disabled or API URL not set")
            return
        }
        
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        
        for (sms in messages) {
            val messageBody = sms.messageBody ?: continue
            val sender = sms.originatingAddress ?: "Unknown"
            
            Log.d(TAG, "Received SMS from $sender: $messageBody")
            
            // Check if this is a payment SMS
            if (isPaymentSMS(messageBody)) {
                Log.d(TAG, "Payment SMS detected, forwarding...")
                forwardSMS(context, apiUrl, messageBody, sender)
            } else {
                Log.d(TAG, "Not a payment SMS, skipping")
            }
        }
    }
    
    private fun isPaymentSMS(message: String): Boolean {
        val lowerMessage = message.lowercase()
        return PAYMENT_KEYWORDS.any { keyword -> 
            lowerMessage.contains(keyword.lowercase()) 
        }
    }
    
    private fun forwardSMS(context: Context, apiUrl: String, message: String, sender: String) {
        Thread {
            try {
                val fullMessage = "From: $sender\n$message"
                val success = APIClient.sendSMS(apiUrl, fullMessage)
                
                if (success) {
                    updateStats(context)
                    Log.d(TAG, "SMS forwarded successfully")
                } else {
                    Log.e(TAG, "Failed to forward SMS")
                    // Queue for retry
                    queueForRetry(context, message, sender)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error forwarding SMS: ${e.message}")
                queueForRetry(context, message, sender)
            }
        }.start()
    }
    
    private fun updateStats(context: Context) {
        val prefs = context.getSharedPreferences("sms_forwarder", Context.MODE_PRIVATE)
        val count = prefs.getInt("forwarded_count", 0) + 1
        val timestamp = java.text.SimpleDateFormat("MMM dd, HH:mm", java.util.Locale.getDefault())
            .format(java.util.Date())
        
        prefs.edit()
            .putInt("forwarded_count", count)
            .putString("last_forwarded", timestamp)
            .apply()
    }
    
    private fun queueForRetry(context: Context, message: String, sender: String) {
        // Store failed messages for retry
        val prefs = context.getSharedPreferences("sms_forwarder", Context.MODE_PRIVATE)
        val pendingMessages = prefs.getStringSet("pending_messages", mutableSetOf()) ?: mutableSetOf()
        pendingMessages.add("$sender|||$message|||${System.currentTimeMillis()}")
        
        prefs.edit()
            .putStringSet("pending_messages", pendingMessages)
            .apply()
    }
}
