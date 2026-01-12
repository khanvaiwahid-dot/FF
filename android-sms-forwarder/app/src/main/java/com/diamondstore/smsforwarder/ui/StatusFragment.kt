package com.diamondstore.smsforwarder.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.diamondstore.smsforwarder.SMSForwarderApp
import com.diamondstore.smsforwarder.databinding.FragmentStatusBinding
import com.diamondstore.smsforwarder.network.ApiClient
import com.diamondstore.smsforwarder.util.PrefsManager
import com.diamondstore.smsforwarder.worker.SMSForwardWorker
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class StatusFragment : Fragment() {
    
    private var _binding: FragmentStatusBinding? = null
    private val binding get() = _binding!!
    
    private lateinit var prefs: PrefsManager
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentStatusBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        prefs = PrefsManager.getInstance(requireContext())
        
        setupUI()
        observeData()
    }
    
    override fun onResume() {
        super.onResume()
        updateStatus()
    }
    
    private fun setupUI() {
        binding.switchForwarding.setOnCheckedChangeListener { _, isChecked ->
            prefs.forwardingEnabled = isChecked
            updateStatus()
            
            if (isChecked) {
                SMSForwardWorker.enqueue(requireContext())
                SMSForwardWorker.enqueuePeriodicSync(requireContext())
            }
        }
        
        binding.btnTestConnection.setOnClickListener {
            testConnection()
        }
        
        binding.btnRetryAll.setOnClickListener {
            SMSForwardWorker.enqueue(requireContext())
        }
    }
    
    private fun observeData() {
        val database = SMSForwarderApp.instance.database
        
        database.smsEventDao().getPendingCount().observe(viewLifecycleOwner) { count ->
            binding.tvPendingCount.text = count.toString()
        }
        
        database.smsEventDao().getSentCount().observe(viewLifecycleOwner) { count ->
            binding.tvSentCount.text = count.toString()
        }
        
        database.smsEventDao().getFailedCount().observe(viewLifecycleOwner) { count ->
            binding.tvFailedCount.text = count.toString()
        }
    }
    
    private fun updateStatus() {
        binding.switchForwarding.isChecked = prefs.forwardingEnabled
        
        // Configuration status
        val isConfigured = prefs.isConfigured()
        binding.tvConfigStatus.text = if (isConfigured) "Configured" else "Not Configured"
        binding.tvConfigStatus.setTextColor(
            if (isConfigured) 0xFF28A745.toInt() else 0xFFDC3545.toInt()
        )
        
        // Backend URL display
        binding.tvBackendUrl.text = prefs.backendUrl.ifEmpty { "Not set" }
        
        // Last sent time
        val lastSent = prefs.lastSentTime
        if (lastSent > 0) {
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            binding.tvLastSent.text = sdf.format(Date(lastSent))
        } else {
            binding.tvLastSent.text = "Never"
        }
    }
    
    private fun testConnection() {
        val backendUrl = prefs.backendUrl
        if (backendUrl.isBlank()) {
            binding.tvConnectionStatus.text = "Backend URL not set"
            binding.tvConnectionStatus.setTextColor(0xFFDC3545.toInt())
            return
        }
        
        binding.tvConnectionStatus.text = "Testing..."
        binding.tvConnectionStatus.setTextColor(0xFFFFC107.toInt())
        binding.btnTestConnection.isEnabled = false
        
        lifecycleScope.launch {
            try {
                val success = ApiClient.getInstance().healthCheck(backendUrl)
                if (success) {
                    binding.tvConnectionStatus.text = "Connected"
                    binding.tvConnectionStatus.setTextColor(0xFF28A745.toInt())
                } else {
                    binding.tvConnectionStatus.text = "Connection Failed"
                    binding.tvConnectionStatus.setTextColor(0xFFDC3545.toInt())
                }
            } catch (e: Exception) {
                binding.tvConnectionStatus.text = "Error: ${e.message}"
                binding.tvConnectionStatus.setTextColor(0xFFDC3545.toInt())
            } finally {
                binding.btnTestConnection.isEnabled = true
            }
        }
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
