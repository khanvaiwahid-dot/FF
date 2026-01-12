package com.diamondstore.smsforwarder.data

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "sms_events",
    indices = [Index(value = ["fingerprint"], unique = true)]
)
data class SmsEvent(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    
    val rawMessage: String,
    val sender: String?,
    val receivedAt: String,
    
    // Parsed fields
    val amountPaisa: Int?,
    val last3digits: String?,
    val rrn: String?,
    val remark: String?,
    val method: String?,
    
    // Fingerprint for duplicate detection
    val fingerprint: String,
    
    // Status: pending, sent, failed, duplicate
    val status: String = "pending",
    
    // Error message if failed
    val errorMessage: String? = null,
    
    // Retry count
    val retryCount: Int = 0,
    
    // Timestamps
    val createdAt: Long = System.currentTimeMillis(),
    val sentAt: Long? = null
)
