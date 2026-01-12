package com.diamondstore.smsforwarder

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.work.Configuration
import androidx.work.WorkManager
import com.diamondstore.smsforwarder.data.AppDatabase

class SMSForwarderApp : Application(), Configuration.Provider {
    
    lateinit var database: AppDatabase
        private set
    
    override fun onCreate() {
        super.onCreate()
        instance = this
        
        // Initialize database
        database = AppDatabase.getInstance(this)
        
        // Create notification channels
        createNotificationChannels()
    }
    
    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_SERVICE,
                "SMS Forwarder Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows when SMS forwarder is running"
            }
            
            val alertChannel = NotificationChannel(
                CHANNEL_ALERTS,
                "SMS Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts for SMS forwarding status"
            }
            
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(serviceChannel)
            notificationManager.createNotificationChannel(alertChannel)
        }
    }
    
    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setMinimumLoggingLevel(android.util.Log.INFO)
            .build()
    
    companion object {
        const val CHANNEL_SERVICE = "sms_forwarder_service"
        const val CHANNEL_ALERTS = "sms_forwarder_alerts"
        
        lateinit var instance: SMSForwarderApp
            private set
    }
}
