package com.diamondstore.smsforwarder.network

import android.util.Log
import com.diamondstore.smsforwarder.data.SmsEvent
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class ApiClient {
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    private val gson = Gson()
    
    data class IngestRequest(
        val raw_message: String,
        val sender: String?,
        val received_at: String,
        val amount_paisa: Int?,
        val last3digits: String?,
        val rrn: String?,
        val remark: String?,
        val method: String?,
        val sms_fingerprint: String,
        val device_id: String?,
        val app_version: String
    )
    
    data class IngestResponse(
        val ok: Boolean,
        val status: String,
        val matched: Boolean? = null,
        val reason: String? = null
    )
    
    sealed class ApiResult {
        data class Success(val response: IngestResponse) : ApiResult()
        data class Duplicate(val reason: String) : ApiResult()
        data class AuthError(val message: String) : ApiResult()
        data class NetworkError(val message: String) : ApiResult()
        data class ServerError(val code: Int, val message: String) : ApiResult()
    }
    
    suspend fun sendSMS(
        baseUrl: String,
        token: String,
        event: SmsEvent,
        deviceId: String,
        appVersion: String
    ): ApiResult = withContext(Dispatchers.IO) {
        try {
            val url = "${baseUrl.trimEnd('/')}/api/sms/ingest"
            
            val requestBody = IngestRequest(
                raw_message = event.rawMessage,
                sender = event.sender,
                received_at = event.receivedAt,
                amount_paisa = event.amountPaisa,
                last3digits = event.last3digits,
                rrn = event.rrn,
                remark = event.remark,
                method = event.method,
                sms_fingerprint = event.fingerprint,
                device_id = deviceId,
                app_version = appVersion
            )
            
            val jsonBody = gson.toJson(requestBody)
            Log.d(TAG, "Sending SMS to $url: $jsonBody")
            
            val request = Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer $token")
                .addHeader("Content-Type", "application/json")
                .post(jsonBody.toRequestBody("application/json".toMediaType()))
                .build()
            
            val response = client.newCall(request).execute()
            val responseBody = response.body?.string() ?: ""
            
            Log.d(TAG, "Response: ${response.code} - $responseBody")
            
            when (response.code) {
                200 -> {
                    val ingestResponse = gson.fromJson(responseBody, IngestResponse::class.java)
                    ApiResult.Success(ingestResponse)
                }
                409 -> {
                    val ingestResponse = gson.fromJson(responseBody, IngestResponse::class.java)
                    ApiResult.Duplicate(ingestResponse.reason ?: "duplicate")
                }
                401, 403 -> {
                    ApiResult.AuthError("Invalid token or unauthorized")
                }
                else -> {
                    ApiResult.ServerError(response.code, responseBody)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error: ${e.message}", e)
            ApiResult.NetworkError(e.message ?: "Unknown network error")
        }
    }
    
    suspend fun healthCheck(baseUrl: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = "${baseUrl.trimEnd('/')}/api/sms/health"
            val request = Request.Builder()
                .url(url)
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            response.code == 200
        } catch (e: Exception) {
            Log.e(TAG, "Health check failed: ${e.message}")
            false
        }
    }
    
    companion object {
        private const val TAG = "ApiClient"
        
        @Volatile
        private var INSTANCE: ApiClient? = null
        
        fun getInstance(): ApiClient {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: ApiClient().also { INSTANCE = it }
            }
        }
    }
}
