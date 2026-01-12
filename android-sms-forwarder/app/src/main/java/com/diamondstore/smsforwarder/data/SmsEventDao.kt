package com.diamondstore.smsforwarder.data

import androidx.lifecycle.LiveData
import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface SmsEventDao {
    
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(event: SmsEvent): Long
    
    @Update
    suspend fun update(event: SmsEvent)
    
    @Query("SELECT * FROM sms_events ORDER BY createdAt DESC LIMIT 100")
    fun getAllEvents(): LiveData<List<SmsEvent>>
    
    @Query("SELECT * FROM sms_events ORDER BY createdAt DESC LIMIT 100")
    fun getAllEventsFlow(): Flow<List<SmsEvent>>
    
    @Query("SELECT * FROM sms_events WHERE status = 'pending' OR (status = 'failed' AND retryCount < 5) ORDER BY createdAt ASC")
    suspend fun getPendingEvents(): List<SmsEvent>
    
    @Query("SELECT COUNT(*) FROM sms_events WHERE status = 'pending'")
    fun getPendingCount(): LiveData<Int>
    
    @Query("SELECT COUNT(*) FROM sms_events WHERE status = 'sent'")
    fun getSentCount(): LiveData<Int>
    
    @Query("SELECT COUNT(*) FROM sms_events WHERE status = 'failed'")
    fun getFailedCount(): LiveData<Int>
    
    @Query("SELECT * FROM sms_events WHERE fingerprint = :fingerprint LIMIT 1")
    suspend fun getByFingerprint(fingerprint: String): SmsEvent?
    
    @Query("UPDATE sms_events SET status = :status, errorMessage = :error, sentAt = :sentAt WHERE id = :id")
    suspend fun updateStatus(id: Long, status: String, error: String?, sentAt: Long?)
    
    @Query("UPDATE sms_events SET retryCount = retryCount + 1 WHERE id = :id")
    suspend fun incrementRetryCount(id: Long)
    
    @Query("SELECT * FROM sms_events WHERE status = 'sent' ORDER BY sentAt DESC LIMIT 1")
    suspend fun getLastSentEvent(): SmsEvent?
    
    @Query("DELETE FROM sms_events WHERE createdAt < :timestamp")
    suspend fun deleteOldEvents(timestamp: Long)
}
