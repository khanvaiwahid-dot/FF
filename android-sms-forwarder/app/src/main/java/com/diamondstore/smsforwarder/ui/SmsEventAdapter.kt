package com.diamondstore.smsforwarder.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.diamondstore.smsforwarder.R
import com.diamondstore.smsforwarder.data.SmsEvent
import java.text.SimpleDateFormat
import java.util.*

class SmsEventAdapter : ListAdapter<SmsEvent, SmsEventAdapter.ViewHolder>(
    SmsEventDiffCallback()
) {
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_sms_event, parent, false)
        return ViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position))
    }
    
    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvStatus: TextView = itemView.findViewById(R.id.tvStatus)
        private val tvAmount: TextView = itemView.findViewById(R.id.tvAmount)
        private val tvRrn: TextView = itemView.findViewById(R.id.tvRrn)
        private val tvMessage: TextView = itemView.findViewById(R.id.tvMessage)
        private val tvTime: TextView = itemView.findViewById(R.id.tvTime)
        private val tvError: TextView = itemView.findViewById(R.id.tvError)
        
        private val sdf = SimpleDateFormat("MM/dd HH:mm:ss", Locale.getDefault())
        
        fun bind(event: SmsEvent) {
            // Status badge
            tvStatus.text = event.status.uppercase()
            tvStatus.setBackgroundColor(when (event.status) {
                "sent" -> 0xFF28A745.toInt()  // Green
                "pending" -> 0xFFFFC107.toInt()  // Yellow
                "failed" -> 0xFFDC3545.toInt()  // Red
                "duplicate" -> 0xFF6C757D.toInt()  // Gray
                else -> 0xFF6C757D.toInt()
            })
            
            // Amount
            val amountRs = (event.amountPaisa ?: 0) / 100.0
            tvAmount.text = "Rs %.2f".format(amountRs)
            
            // RRN and last 3 digits
            tvRrn.text = buildString {
                event.rrn?.let { append("RRN: $it") }
                event.last3digits?.let {
                    if (isNotEmpty()) append(" | ")
                    append("Last3: $it")
                }
            }
            
            // Message preview
            tvMessage.text = event.rawMessage.take(100) + if (event.rawMessage.length > 100) "..." else ""
            
            // Time
            tvTime.text = sdf.format(Date(event.createdAt))
            
            // Error message
            if (event.errorMessage != null) {
                tvError.visibility = View.VISIBLE
                tvError.text = event.errorMessage
            } else {
                tvError.visibility = View.GONE
            }
        }
    }
    
    class SmsEventDiffCallback : DiffUtil.ItemCallback<SmsEvent>() {
        override fun areItemsTheSame(oldItem: SmsEvent, newItem: SmsEvent): Boolean {
            return oldItem.id == newItem.id
        }
        
        override fun areContentsTheSame(oldItem: SmsEvent, newItem: SmsEvent): Boolean {
            return oldItem == newItem
        }
    }
}
