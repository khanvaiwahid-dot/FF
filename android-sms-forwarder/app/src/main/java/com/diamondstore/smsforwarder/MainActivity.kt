package com.diamondstore.smsforwarder

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.diamondstore.smsforwarder.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private val PERMISSION_REQUEST_CODE = 123
    
    private val requiredPermissions = mutableListOf(
        Manifest.permission.RECEIVE_SMS,
        Manifest.permission.READ_SMS
    ).apply {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupUI()
        checkPermissions()
    }
    
    private fun setupUI() {
        // Load saved API URL
        val prefs = getSharedPreferences("sms_forwarder", MODE_PRIVATE)
        val savedUrl = prefs.getString("api_url", "")
        val isEnabled = prefs.getBoolean("forwarding_enabled", false)
        
        binding.editApiUrl.setText(savedUrl)
        binding.switchEnable.isChecked = isEnabled
        
        // Save button
        binding.btnSave.setOnClickListener {
            val apiUrl = binding.editApiUrl.text.toString().trim()
            
            if (apiUrl.isEmpty()) {
                Toast.makeText(this, "Please enter API URL", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            prefs.edit()
                .putString("api_url", apiUrl)
                .apply()
            
            Toast.makeText(this, "Settings saved!", Toast.LENGTH_SHORT).show()
        }
        
        // Enable/Disable switch
        binding.switchEnable.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit()
                .putBoolean("forwarding_enabled", isChecked)
                .apply()
            
            if (isChecked) {
                startForwarderService()
                binding.statusText.text = "Status: Active"
                binding.statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_dark))
            } else {
                stopForwarderService()
                binding.statusText.text = "Status: Inactive"
                binding.statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_dark))
            }
        }
        
        // Test button
        binding.btnTest.setOnClickListener {
            testConnection()
        }
        
        // Update status
        updateStatus()
    }
    
    private fun updateStatus() {
        val prefs = getSharedPreferences("sms_forwarder", MODE_PRIVATE)
        val isEnabled = prefs.getBoolean("forwarding_enabled", false)
        val forwardedCount = prefs.getInt("forwarded_count", 0)
        val lastForwarded = prefs.getString("last_forwarded", "Never")
        
        if (isEnabled) {
            binding.statusText.text = "Status: Active"
            binding.statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_dark))
        } else {
            binding.statusText.text = "Status: Inactive"
            binding.statusText.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_dark))
        }
        
        binding.statsText.text = "Messages forwarded: $forwardedCount\nLast forwarded: $lastForwarded"
    }
    
    private fun checkPermissions() {
        val permissionsToRequest = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                permissionsToRequest.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
        } else {
            onPermissionsGranted()
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            val allGranted = grantResults.all { it == PackageManager.PERMISSION_GRANTED }
            
            if (allGranted) {
                onPermissionsGranted()
            } else {
                Toast.makeText(
                    this,
                    "SMS permission is required for this app to work",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
    
    private fun onPermissionsGranted() {
        binding.permissionStatus.text = "✓ All permissions granted"
        binding.permissionStatus.setTextColor(ContextCompat.getColor(this, android.R.color.holo_green_dark))
        
        // Start service if enabled
        val prefs = getSharedPreferences("sms_forwarder", MODE_PRIVATE)
        if (prefs.getBoolean("forwarding_enabled", false)) {
            startForwarderService()
        }
    }
    
    private fun startForwarderService() {
        val intent = Intent(this, SMSForwarderService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }
    
    private fun stopForwarderService() {
        val intent = Intent(this, SMSForwarderService::class.java)
        stopService(intent)
    }
    
    private fun testConnection() {
        val apiUrl = binding.editApiUrl.text.toString().trim()
        
        if (apiUrl.isEmpty()) {
            Toast.makeText(this, "Please enter API URL first", Toast.LENGTH_SHORT).show()
            return
        }
        
        binding.btnTest.isEnabled = false
        binding.btnTest.text = "Testing..."
        
        Thread {
            try {
                val testMessage = "TEST: Rs 100.00 received from 98XXXXX910 for RRN TEST123, DiamondStore /FonePay"
                val result = APIClient.sendSMS(apiUrl, testMessage)
                
                runOnUiThread {
                    binding.btnTest.isEnabled = true
                    binding.btnTest.text = "Test Connection"
                    
                    if (result) {
                        Toast.makeText(this, "✓ Connection successful!", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this, "✗ Connection failed. Check URL.", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    binding.btnTest.isEnabled = true
                    binding.btnTest.text = "Test Connection"
                    Toast.makeText(this, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }.start()
    }
    
    override fun onResume() {
        super.onResume()
        updateStatus()
    }
}
