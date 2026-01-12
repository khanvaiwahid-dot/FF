package com.diamondstore.smsforwarder.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.diamondstore.smsforwarder.util.PrefsManager
import com.diamondstore.smsforwarder.worker.SMSForwardWorker

class BootReceiver : BroadcastReceiver() {
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == "android.intent.action.QUICKBOOT_POWERON") {
            
            Log.d(TAG, "Boot completed, checking if we need to start worker")
            
            val prefs = PrefsManager.getInstance(context)
            if (prefs.forwardingEnabled && prefs.isConfigured()) {
                Log.d(TAG, "Forwarding enabled, starting worker")
                SMSForwardWorker.enqueue(context)
            }
        }
    }
    
    companion object {
        private const val TAG = "BootReceiver"
    }
}
