package com.diamondstore.smsforwarder

import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object APIClient {
    
    private const val TAG = "APIClient"
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    fun sendSMS(baseUrl: String, rawMessage: String): Boolean {
        return try {
            val url = "${baseUrl.trimEnd('/')}/api/sms/receive"
            
            val json = JSONObject().apply {
                put("raw_message", rawMessage)
            }
            
            val mediaType = "application/json; charset=utf-8".toMediaType()
            val body = json.toString().toRequestBody(mediaType)
            
            val request = Request.Builder()
                .url(url)
                .post(body)
                .addHeader("Content-Type", "application/json")
                .build()
            
            Log.d(TAG, "Sending SMS to: $url")
            
            client.newCall(request).execute().use { response ->
                val responseBody = response.body?.string()
                Log.d(TAG, "Response: ${response.code} - $responseBody")
                
                response.isSuccessful
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error sending SMS: ${e.message}")
            false
        }
    }
}
