package com.diamondstore.smsforwarder.util

import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.*
import java.util.regex.Pattern

object SMSParser {
    
    // Default keywords to filter payment SMS
    val DEFAULT_KEYWORDS = listOf(
        "You have received",
        "RRN",
        "FonepayQR",
        "Fonepay",
        "received Rs",
        "received NPR"
    )
    
    data class ParsedSMS(
        val amountPaisa: Int?,
        val last3digits: String?,
        val rrn: String?,
        val remark: String?,
        val method: String?
    )
    
    /**
     * Check if SMS matches any of the keywords
     */
    fun matchesKeywords(message: String, keywords: List<String>): Boolean {
        val lowerMessage = message.lowercase()
        return keywords.any { keyword ->
            lowerMessage.contains(keyword.lowercase())
        }
    }
    
    /**
     * Parse SMS message to extract payment details
     */
    fun parse(message: String): ParsedSMS {
        return ParsedSMS(
            amountPaisa = parseAmount(message),
            last3digits = parseLast3Digits(message),
            rrn = parseRRN(message),
            remark = parseRemark(message),
            method = parseMethod(message)
        )
    }
    
    /**
     * Parse amount from SMS (supports Rs, NPR, रु)
     * Returns amount in paisa (integer)
     */
    private fun parseAmount(message: String): Int? {
        // Pattern: Rs 125.00, NPR 125.00, रु 125.00, Rs.125, etc.
        val patterns = listOf(
            "(?:Rs\\.?|NPR\\.?|रु\\.?)\\s*([\\d,]+(?:\\.\\d{1,2})?)",
            "received\\s+(?:Rs\\.?|NPR\\.?|रु\\.?)\\s*([\\d,]+(?:\\.\\d{1,2})?)",
            "([\\d,]+(?:\\.\\d{1,2})?)\\s*(?:Rs|NPR|रु)"
        )
        
        for (patternStr in patterns) {
            val pattern = Pattern.compile(patternStr, Pattern.CASE_INSENSITIVE)
            val matcher = pattern.matcher(message)
            if (matcher.find()) {
                val amountStr = matcher.group(1)?.replace(",", "") ?: continue
                try {
                    val amount = amountStr.toDouble()
                    return (amount * 100).toInt()  // Convert to paisa
                } catch (e: NumberFormatException) {
                    continue
                }
            }
        }
        return null
    }
    
    /**
     * Extract last 3 digits from masked phone number
     * Examples: 900****910 -> 910, 98XXXXXX10 -> X10 (last 3)
     */
    private fun parseLast3Digits(message: String): String? {
        // Pattern for masked numbers like 900****910, 98XXXXXX10
        val patterns = listOf(
            "from\\s+\\d+[*X]+([\\d]{3})",
            "([\\d]{3})\\s+for\\s+RRN",
            "\\d+[*X]+([\\d]{3})"
        )
        
        for (patternStr in patterns) {
            val pattern = Pattern.compile(patternStr, Pattern.CASE_INSENSITIVE)
            val matcher = pattern.matcher(message)
            if (matcher.find()) {
                return matcher.group(1)
            }
        }
        return null
    }
    
    /**
     * Extract RRN (Reference Number)
     * Examples: RRN 11672918bccl
     */
    private fun parseRRN(message: String): String? {
        val pattern = Pattern.compile("RRN\\s+([A-Za-z0-9]+)", Pattern.CASE_INSENSITIVE)
        val matcher = pattern.matcher(message)
        if (matcher.find()) {
            return matcher.group(1)
        }
        return null
    }
    
    /**
     * Extract remark (text after comma, before /)
     * Example: "for RRN 123, cake /FonepayQR" -> "cake"
     */
    private fun parseRemark(message: String): String? {
        // Look for pattern: , remark /
        val pattern = Pattern.compile(",\\s*([^/]+?)\\s*/", Pattern.CASE_INSENSITIVE)
        val matcher = pattern.matcher(message)
        if (matcher.find()) {
            return matcher.group(1)?.trim()
        }
        return null
    }
    
    /**
     * Extract payment method (after /)
     * Example: "/FonepayQR" -> "FonepayQR"
     */
    private fun parseMethod(message: String): String? {
        // Look for /MethodName or /MethodName.
        val pattern = Pattern.compile("/([A-Za-z0-9]+)", Pattern.CASE_INSENSITIVE)
        val matcher = pattern.matcher(message)
        if (matcher.find()) {
            return matcher.group(1)
        }
        return null
    }
    
    /**
     * Generate unique fingerprint for SMS
     * SHA256(sender + "|" + raw_message + "|" + received_at_rounded_to_minute)
     */
    fun generateFingerprint(sender: String?, message: String, receivedAt: Long): String {
        // Round timestamp to minute
        val roundedTime = (receivedAt / 60000) * 60000
        val input = "${sender ?: ""}|$message|$roundedTime"
        
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(input.toByteArray())
        return digest.joinToString("") { "%02x".format(it) }
    }
    
    /**
     * Get current timestamp in ISO8601 format
     */
    fun getISO8601Timestamp(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date())
    }
}
