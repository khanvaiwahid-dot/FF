package com.diamondstore.smsforwarder.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.LinearLayoutManager
import com.diamondstore.smsforwarder.SMSForwarderApp
import com.diamondstore.smsforwarder.databinding.FragmentLogsBinding
import com.diamondstore.smsforwarder.worker.SMSForwardWorker

class LogsFragment : Fragment() {
    
    private var _binding: FragmentLogsBinding? = null
    private val binding get() = _binding!!
    
    private lateinit var adapter: SmsEventAdapter
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentLogsBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        setupRecyclerView()
        observeData()
        setupSwipeRefresh()
    }
    
    private fun setupRecyclerView() {
        adapter = SmsEventAdapter()
        binding.recyclerView.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerView.adapter = adapter
    }
    
    private fun observeData() {
        val database = SMSForwarderApp.instance.database
        
        database.smsEventDao().getAllEvents().observe(viewLifecycleOwner) { events ->
            adapter.submitList(events)
            binding.tvEmpty.visibility = if (events.isEmpty()) View.VISIBLE else View.GONE
        }
    }
    
    private fun setupSwipeRefresh() {
        binding.swipeRefresh.setOnRefreshListener {
            SMSForwardWorker.enqueue(requireContext())
            binding.swipeRefresh.isRefreshing = false
        }
        
        // Set orange color for refresh indicator
        binding.swipeRefresh.setColorSchemeColors(0xFFFF6B35.toInt())
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
