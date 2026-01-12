package com.diamondstore.smsforwarder.util

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class PrefsManager(context: Context) {
    
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val securePrefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    private val regularPrefs: SharedPreferences = context.getSharedPreferences(
        "app_prefs",
        Context.MODE_PRIVATE
    )
    
    // Backend URL
    var backendUrl: String
        get() = regularPrefs.getString(KEY_BACKEND_URL, DEFAULT_BACKEND_URL) ?: DEFAULT_BACKEND_URL
        set(value) = regularPrefs.edit().putString(KEY_BACKEND_URL, value).apply()
    
    // API Token (stored securely)
    var apiToken: String
        get() = securePrefs.getString(KEY_API_TOKEN, "") ?: ""
        set(value) = securePrefs.edit().putString(KEY_API_TOKEN, value).apply()
    
    // Forwarding enabled
    var forwardingEnabled: Boolean
        get() = regularPrefs.getBoolean(KEY_FORWARDING_ENABLED, false)
        set(value) = regularPrefs.edit().putBoolean(KEY_FORWARDING_ENABLED, value).apply()
    
    // Device ID (generated once)
    var deviceId: String
        get() {
            var id = regularPrefs.getString(KEY_DEVICE_ID, null)
            if (id == null) {
                id = java.util.UUID.randomUUID().toString()
                regularPrefs.edit().putString(KEY_DEVICE_ID, id).apply()
            }
            return id
        }
        set(value) = regularPrefs.edit().putString(KEY_DEVICE_ID, value).apply()
    
    // Filter keywords (comma separated)
    var filterKeywords: String
        get() = regularPrefs.getString(KEY_FILTER_KEYWORDS, DEFAULT_KEYWORDS) ?: DEFAULT_KEYWORDS
        set(value) = regularPrefs.edit().putString(KEY_FILTER_KEYWORDS, value).apply()
    
    fun getKeywordsList(): List<String> {
        return filterKeywords.split(",").map { it.trim() }.filter { it.isNotEmpty() }
    }
    
    // Last successful send time
    var lastSentTime: Long
        get() = regularPrefs.getLong(KEY_LAST_SENT_TIME, 0)
        set(value) = regularPrefs.edit().putLong(KEY_LAST_SENT_TIME, value).apply()
    
    // Check if configured
    fun isConfigured(): Boolean {
        return backendUrl.isNotBlank() && apiToken.isNotBlank()
    }
    
    companion object {
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_API_TOKEN = "api_token"
        private const val KEY_FORWARDING_ENABLED = "forwarding_enabled"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_FILTER_KEYWORDS = "filter_keywords"
        private const val KEY_LAST_SENT_TIME = "last_sent_time"
        
        private const val DEFAULT_BACKEND_URL = ""
        private const val DEFAULT_KEYWORDS = "You have received,RRN,FonepayQR,Fonepay"
        
        @Volatile
        private var INSTANCE: PrefsManager? = null
        
        fun getInstance(context: Context): PrefsManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: PrefsManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }
}
