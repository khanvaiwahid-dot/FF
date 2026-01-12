package com.diamondstore.smsforwarder.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.diamondstore.smsforwarder.SMSForwarderApp
import com.diamondstore.smsforwarder.data.SmsEvent
import com.diamondstore.smsforwarder.databinding.FragmentSettingsBinding
import com.diamondstore.smsforwarder.util.PrefsManager
import com.diamondstore.smsforwarder.util.SMSParser
import com.diamondstore.smsforwarder.worker.SMSForwardWorker
import kotlinx.coroutines.launch

class SettingsFragment : Fragment() {
    
    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    
    private lateinit var prefs: PrefsManager
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        prefs = PrefsManager.getInstance(requireContext())
        
        loadSettings()
        setupListeners()
    }
    
    private fun loadSettings() {
        binding.etBackendUrl.setText(prefs.backendUrl)
        binding.etApiToken.setText(prefs.apiToken)
        binding.etKeywords.setText(prefs.filterKeywords)
        binding.tvDeviceId.text = "Device ID: ${prefs.deviceId}"
    }
    
    private fun setupListeners() {
        binding.btnSave.setOnClickListener {
            saveSettings()
        }
        
        binding.btnResetKeywords.setOnClickListener {
            binding.etKeywords.setText(SMSParser.DEFAULT_KEYWORDS.joinToString(","))
        }
        
        binding.btnTestSms.setOnClickListener {
            sendTestSms()
        }
    }
    
    private fun saveSettings() {
        val backendUrl = binding.etBackendUrl.text.toString().trim()
        val apiToken = binding.etApiToken.text.toString().trim()
        val keywords = binding.etKeywords.text.toString().trim()
        
        // Validate URL
        if (backendUrl.isNotEmpty() && !backendUrl.startsWith("http")) {
            Toast.makeText(context, "Backend URL must start with http:// or https://", Toast.LENGTH_SHORT).show()
            return
        }
        
        prefs.backendUrl = backendUrl
        prefs.apiToken = apiToken
        prefs.filterKeywords = keywords
        
        Toast.makeText(context, "Settings saved", Toast.LENGTH_SHORT).show()
    }
    
    private fun sendTestSms() {
        val testMessage = "You have received Rs 125.00 from 900****910 for RRN TEST123abc, test payment /FonepayQR. For QR support, toll-free no: 18105000131"
        
        val parsed = SMSParser.parse(testMessage)
        val fingerprint = SMSParser.generateFingerprint("TEST_SENDER", testMessage, System.currentTimeMillis())
        val receivedAt = SMSParser.getISO8601Timestamp()
        
        val event = SmsEvent(
            rawMessage = testMessage,
            sender = "TEST_SENDER",
            receivedAt = receivedAt,
            amountPaisa = parsed.amountPaisa,
            last3digits = parsed.last3digits,
            rrn = parsed.rrn,
            remark = parsed.remark,
            method = parsed.method,
            fingerprint = fingerprint,
            status = "pending"
        )
        
        lifecycleScope.launch {
            try {
                val database = SMSForwarderApp.instance.database
                val id = database.smsEventDao().insert(event)
                
                if (id > 0) {
                    Toast.makeText(context, "Test SMS created (ID: $id). Check Logs tab.", Toast.LENGTH_SHORT).show()
                    SMSForwardWorker.enqueue(requireContext())
                } else {
                    Toast.makeText(context, "Test SMS already exists (duplicate)", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
