package com.diamondstore.smsforwarder.worker

import android.content.Context
import android.util.Log
import androidx.work.*
import com.diamondstore.smsforwarder.BuildConfig
import com.diamondstore.smsforwarder.SMSForwarderApp
import com.diamondstore.smsforwarder.network.ApiClient
import com.diamondstore.smsforwarder.util.PrefsManager
import java.util.concurrent.TimeUnit

class SMSForwardWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    override suspend fun doWork(): Result {
        Log.d(TAG, "SMS Forward Worker started")
        
        val prefs = PrefsManager.getInstance(applicationContext)
        
        // Check if configured
        if (!prefs.isConfigured()) {
            Log.d(TAG, "App not configured, skipping")
            return Result.success()
        }
        
        if (!prefs.forwardingEnabled) {
            Log.d(TAG, "Forwarding disabled, skipping")
            return Result.success()
        }
        
        val database = SMSForwarderApp.instance.database
        val apiClient = ApiClient.getInstance()
        
        val pendingEvents = database.smsEventDao().getPendingEvents()
        Log.d(TAG, "Found ${pendingEvents.size} pending events")
        
        var allSuccess = true
        
        for (event in pendingEvents) {
            Log.d(TAG, "Processing event ID: ${event.id}")
            
            val result = apiClient.sendSMS(
                baseUrl = prefs.backendUrl,
                token = prefs.apiToken,
                event = event,
                deviceId = prefs.deviceId,
                appVersion = getAppVersion()
            )
            
            when (result) {
                is ApiClient.ApiResult.Success -> {
                    Log.d(TAG, "SMS sent successfully: ${event.id}")
                    database.smsEventDao().updateStatus(
                        id = event.id,
                        status = "sent",
                        error = null,
                        sentAt = System.currentTimeMillis()
                    )
                    prefs.lastSentTime = System.currentTimeMillis()
                }
                
                is ApiClient.ApiResult.Duplicate -> {
                    Log.d(TAG, "SMS is duplicate, marking as sent: ${event.id}")
                    database.smsEventDao().updateStatus(
                        id = event.id,
                        status = "duplicate",
                        error = "Duplicate: ${result.reason}",
                        sentAt = System.currentTimeMillis()
                    )
                }
                
                is ApiClient.ApiResult.AuthError -> {
                    Log.e(TAG, "Auth error: ${result.message}")
                    database.smsEventDao().updateStatus(
                        id = event.id,
                        status = "failed",
                        error = "Auth error: ${result.message}",
                        sentAt = null
                    )
                    // Don't retry auth errors - need user to fix token
                    allSuccess = false
                }
                
                is ApiClient.ApiResult.NetworkError -> {
                    Log.e(TAG, "Network error: ${result.message}")
                    database.smsEventDao().incrementRetryCount(event.id)
                    database.smsEventDao().updateStatus(
                        id = event.id,
                        status = "failed",
                        error = "Network: ${result.message}",
                        sentAt = null
                    )
                    allSuccess = false
                }
                
                is ApiClient.ApiResult.ServerError -> {
                    Log.e(TAG, "Server error ${result.code}: ${result.message}")
                    database.smsEventDao().incrementRetryCount(event.id)
                    database.smsEventDao().updateStatus(
                        id = event.id,
                        status = "failed",
                        error = "Server ${result.code}: ${result.message}",
                        sentAt = null
                    )
                    allSuccess = false
                }
            }
        }
        
        return if (allSuccess) Result.success() else Result.retry()
    }
    
    private fun getAppVersion(): String {
        return try {
            BuildConfig.VERSION_NAME
        } catch (e: Exception) {
            "1.0.0"
        }
    }
    
    companion object {
        private const val TAG = "SMSForwardWorker"
        private const val WORK_NAME = "sms_forward_work"
        
        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            
            val workRequest = OneTimeWorkRequestBuilder<SMSForwardWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30, TimeUnit.SECONDS
                )
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniqueWork(
                    WORK_NAME,
                    ExistingWorkPolicy.REPLACE,
                    workRequest
                )
            
            Log.d(TAG, "Worker enqueued")
        }
        
        fun enqueuePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            
            val periodicWork = PeriodicWorkRequestBuilder<SMSForwardWorker>(
                15, TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    "${WORK_NAME}_periodic",
                    ExistingPeriodicWorkPolicy.KEEP,
                    periodicWork
                )
        }
    }
}
