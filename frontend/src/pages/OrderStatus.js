import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Gem, CheckCircle, Clock, AlertCircle, Loader, ArrowLeft, RefreshCw } from 'lucide-react';

const OrderStatus = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { user, updateWalletBalance } = useAuth();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentForm, setPaymentForm] = useState({
    sent_amount: '',
    last_3_digits: '',
    payment_method: 'FonePay',
    payment_screenshot: '',
    remark: ''
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchOrder();
    const interval = setInterval(fetchOrder, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const fetchOrder = async () => {
    try {
      const response = await axios.get(`${API}/orders/${orderId}`);
      setOrder(response.data);
      
      // Pre-fill payment amount
      if (response.data.payment_amount > 0 && !paymentForm.sent_amount) {
        setPaymentForm(prev => ({
          ...prev,
          sent_amount: response.data.payment_amount.toString()
        }));
      }
    } catch (error) {
      toast.error('Failed to load order');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPayment = async () => {
    if (!paymentForm.sent_amount || !paymentForm.last_3_digits) {
      toast.error('Please fill in amount and last 3 digits');
      return;
    }

    setSubmitting(true);

    try {
      const response = await axios.post(`${API}/orders/verify-payment`, {
        order_id: orderId,
        sent_amount_rupees: parseFloat(paymentForm.sent_amount),
        last_3_digits: paymentForm.last_3_digits,
        payment_method: paymentForm.payment_method || 'FonePay',
        payment_screenshot: paymentForm.payment_screenshot || null,
        remark: paymentForm.remark || null
      });

      toast.success(response.data.message);
      
      // Refresh wallet balance
      try {
        const walletResponse = await axios.get(`${API}/user/wallet`);
        updateWalletBalance(walletResponse.data.balance);
      } catch (e) {}
      
      fetchOrder();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Payment verification failed');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusConfig = (status) => {
    const configs = {
      pending_payment: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-100', border: 'border-yellow-200', label: 'Waiting for Payment' },
      wallet_partial_paid: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-100', border: 'border-yellow-200', label: 'Partial Payment (Wallet)' },
      wallet_fully_paid: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', border: 'border-green-200', label: 'Paid via Wallet' },
      paid: { icon: CheckCircle, color: 'text-blue-600', bg: 'bg-blue-100', border: 'border-blue-200', label: 'Payment Confirmed' },
      queued: { icon: Loader, color: 'text-blue-600', bg: 'bg-blue-100', border: 'border-blue-200', label: 'In Queue' },
      processing: { icon: RefreshCw, color: 'text-blue-600', bg: 'bg-blue-100', border: 'border-blue-200', label: 'Processing' },
      success: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', border: 'border-green-200', label: 'Completed Successfully' },
      failed: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200', label: 'Failed' },
      manual_review: { icon: Clock, color: 'text-orange-600', bg: 'bg-orange-100', border: 'border-orange-200', label: 'Under Review' },
      suspicious: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200', label: 'Suspicious Activity' },
      duplicate_payment: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200', label: 'Duplicate Payment' },
      expired: { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', border: 'border-gray-200', label: 'Expired' },
      invalid_uid: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200', label: 'Invalid Player UID' }
    };
    return configs[status] || configs.pending_payment;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading order...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-600">Order not found</div>
      </div>
    );
  }

  const statusConfig = getStatusConfig(order.status);
  const StatusIcon = statusConfig.icon;
  const needsPayment = ['pending_payment', 'wallet_partial_paid', 'manual_review'].includes(order.status);

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            data-testid="back-button"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="order-status-title">Order Status</h1>
            <p className="text-xs text-gray-600 font-mono">#{order.id.slice(0, 8)}</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Status Card */}
        <div className={`${statusConfig.bg} border-2 ${statusConfig.border} rounded-2xl p-6`}>
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-sm`}>
              <StatusIcon className={`w-8 h-8 ${statusConfig.color} ${order.status === 'processing' || order.status === 'queued' ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <p className="text-sm text-gray-600">Current Status</p>
              <p className={`text-2xl font-heading font-bold ${statusConfig.color}`} data-testid="order-status">{statusConfig.label}</p>
            </div>
          </div>
        </div>

        {/* Order Details */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900">Order Details</h2>
          
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Player UID</span>
              <span className="text-gray-900 font-mono font-semibold" data-testid="order-player-uid">{order.player_uid}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Server</span>
              <span className="text-gray-900 font-semibold">🇧🇩 Bangladesh</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Package</span>
              <span className="text-gray-900 font-semibold">{order.package_name}</span>
            </div>
            {order.amount > 0 && (
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Diamonds</span>
                <span className="text-primary font-bold flex items-center gap-1">
                  <Gem className="w-4 h-4" />
                  {order.amount}
                </span>
              </div>
            )}
            <div className="pt-3">
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Total Amount</span>
                <span className="text-gray-900 font-semibold">₹{order.locked_price?.toFixed(2) || order.amount}</span>
              </div>
              {order.wallet_used > 0 && (
                <div className="flex justify-between py-2">
                  <span className="text-gray-600">Wallet Used</span>
                  <span className="text-green-600 font-semibold">-₹{order.wallet_used?.toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between py-2 border-t border-gray-200 mt-2 pt-3">
                <span className="text-gray-900 font-bold">Payment Required</span>
                <span className="text-primary font-bold text-xl">₹{order.payment_amount?.toFixed(2) || '0.00'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Payment Form */}
        {needsPayment && order.payment_amount > 0 && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4 shadow-sm">
            <h2 className="text-xl font-heading font-bold text-gray-900">Verify Your Payment</h2>
            <p className="text-sm text-gray-600">
              After sending ₹{order.payment_amount?.toFixed(2)} via FonePay, enter the details below to confirm.
            </p>

            <div className="space-y-4">
              <div>
                <label htmlFor="sent_amount" className="block text-sm font-semibold text-gray-900 mb-2">
                  Amount Sent (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  id="sent_amount"
                  data-testid="payment-amount-input"
                  type="number"
                  step="0.01"
                  placeholder="Amount you sent"
                  value={paymentForm.sent_amount}
                  onChange={(e) => setPaymentForm({ ...paymentForm, sent_amount: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                />
              </div>

              <div>
                <label htmlFor="last_3_digits" className="block text-sm font-semibold text-gray-900 mb-2">
                  Last 3 Digits of Phone <span className="text-red-500">*</span>
                </label>
                <input
                  id="last_3_digits"
                  data-testid="payment-last3digits-input"
                  type="text"
                  maxLength={3}
                  placeholder="e.g., 910"
                  value={paymentForm.last_3_digits}
                  onChange={(e) => setPaymentForm({ ...paymentForm, last_3_digits: e.target.value.replace(/\D/g, '') })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                />
                <p className="text-xs text-gray-500 mt-1">Last 3 digits of phone linked to payment</p>
              </div>

              <div>
                <label htmlFor="remark" className="block text-sm font-semibold text-gray-900 mb-2">
                  Remarks (Optional)
                </label>
                <input
                  id="remark"
                  data-testid="payment-remark-input"
                  type="text"
                  placeholder="Any remark you added"
                  value={paymentForm.remark}
                  onChange={(e) => setPaymentForm({ ...paymentForm, remark: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <p className="text-sm text-blue-800">
                  ℹ️ We'll automatically verify your payment using SMS notifications.
                </p>
              </div>

              <Button
                onClick={handleVerifyPayment}
                data-testid="verify-payment-button"
                disabled={submitting}
                className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full transition-all disabled:opacity-50"
              >
                {submitting ? 'Verifying...' : 'Check Payment'}
              </Button>
            </div>
          </div>
        )}

        {/* Success Message */}
        {order.status === 'success' && (
          <div className="bg-green-50 border-2 border-green-200 rounded-2xl p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h3 className="text-2xl font-heading font-bold text-gray-900 mb-2">Diamonds Delivered!</h3>
            <p className="text-gray-600">Your {order.amount} diamonds have been added to your account.</p>
            <Button
              onClick={() => navigate('/')}
              data-testid="new-order-button"
              className="mt-6 bg-primary hover:bg-primary-hover text-white font-bold h-12 px-8 rounded-full"
            >
              Make Another Order
            </Button>
          </div>
        )}

        {/* Failed/Error Messages */}
        {['failed', 'invalid_uid', 'suspicious', 'duplicate_payment'].includes(order.status) && (
          <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-xl font-heading font-bold text-gray-900 mb-2">Order Issue</h3>
            <p className="text-gray-600 mb-4">
              {order.status === 'invalid_uid' && 'The player UID was not found in Free Fire. Please check and try again.'}
              {order.status === 'suspicious' && 'This order has been flagged for review. Our team will contact you.'}
              {order.status === 'duplicate_payment' && 'This payment appears to be a duplicate. Please contact support.'}
              {order.status === 'failed' && 'Something went wrong with this order. Our team is looking into it.'}
            </p>
            <Button
              onClick={() => navigate('/')}
              variant="outline"
              className="border-gray-300 text-gray-700 hover:bg-gray-50 h-10 px-6 rounded-full"
            >
              Back to Home
            </Button>
          </div>
        )}

        {/* Expired Message */}
        {order.status === 'expired' && (
          <div className="bg-gray-100 border border-gray-200 rounded-2xl p-6 text-center">
            <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-heading font-bold text-gray-900 mb-2">Order Expired</h3>
            <p className="text-gray-600 mb-4">This order has expired due to no payment received within 24 hours.</p>
            {order.wallet_used > 0 && (
              <p className="text-green-600 font-semibold mb-4">₹{order.wallet_used?.toFixed(2)} has been refunded to your wallet.</p>
            )}
            <Button
              onClick={() => navigate('/')}
              className="bg-primary hover:bg-primary-hover text-white font-bold h-10 px-6 rounded-full"
            >
              Create New Order
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrderStatus;
