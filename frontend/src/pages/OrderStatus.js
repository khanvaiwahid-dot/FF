import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Gem, CheckCircle, Clock, AlertCircle, Loader, ArrowLeft } from 'lucide-react';

const OrderStatus = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentForm, setPaymentForm] = useState({
    sent_amount: '',
    last_3_digits: '',
    payment_method: '',
    payment_screenshot: '',
    remark: ''
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchOrder();
    const interval = setInterval(fetchOrder, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
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
    if (!paymentForm.sent_amount || !paymentForm.last_3_digits || !paymentForm.payment_method) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);

    try {
      const response = await axios.post(`${API}/orders/verify-payment`, {
        order_id: orderId,
        sent_amount: parseFloat(paymentForm.sent_amount),
        last_3_digits: paymentForm.last_3_digits,
        payment_method: paymentForm.payment_method,
        payment_screenshot: paymentForm.payment_screenshot || null,
        remark: paymentForm.remark || null
      });

      toast.success(response.data.message);
      fetchOrder();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Payment verification failed');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusConfig = (status) => {
    const configs = {
      pending_payment: { icon: Clock, color: 'text-warning', bg: 'bg-warning/10', label: 'Waiting for Payment' },
      wallet_partial_paid: { icon: Clock, color: 'text-warning', bg: 'bg-warning/10', label: 'Partial Payment (Wallet)' },
      wallet_fully_paid: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10', label: 'Paid via Wallet' },
      paid: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10', label: 'Payment Confirmed' },
      queued: { icon: Loader, color: 'text-info', bg: 'bg-info/10', label: 'In Queue' },
      processing: { icon: Loader, color: 'text-info', bg: 'bg-info/10', label: 'Processing' },
      success: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10', label: 'Completed Successfully' },
      failed: { icon: AlertCircle, color: 'text-error', bg: 'bg-error/10', label: 'Failed' },
      manual_review: { icon: Clock, color: 'text-warning', bg: 'bg-warning/10', label: 'Under Review' },
      suspicious: { icon: AlertCircle, color: 'text-error', bg: 'bg-error/10', label: 'Suspicious Activity' },
      duplicate_payment: { icon: AlertCircle, color: 'text-error', bg: 'bg-error/10', label: 'Duplicate Payment' },
      expired: { icon: AlertCircle, color: 'text-gray-400', bg: 'bg-gray-400/10', label: 'Expired' }
    };
    return configs[status] || configs.pending_payment;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary">Loading order...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-error">Order not found</div>
      </div>
    );
  }

  const statusConfig = getStatusConfig(order.status);
  const StatusIcon = statusConfig.icon;
  const needsPayment = ['pending_payment', 'wallet_partial_paid', 'manual_review'].includes(order.status);

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-card/80 backdrop-blur-sm border-b border-white/5 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            data-testid="back-button"
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-white" data-testid="order-status-title">Order Status</h1>
            <p className="text-xs text-gray-400 font-mono">#{order.id.slice(0, 8)}</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Status Card */}
        <div className={`${statusConfig.bg} backdrop-blur-xl border border-white/10 rounded-2xl p-6`}>
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 ${statusConfig.bg} rounded-full flex items-center justify-center`}>
              <StatusIcon className={`w-8 h-8 ${statusConfig.color} ${order.status === 'processing' || order.status === 'queued' ? 'animate-spin' : ''}`} />
            </div>
            <div>
              <p className="text-sm text-gray-400">Current Status</p>
              <p className={`text-2xl font-heading font-bold ${statusConfig.color}`} data-testid="order-status">{statusConfig.label}</p>
            </div>
          </div>
        </div>

        {/* Order Details */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
          <h2 className="text-xl font-heading font-bold text-white">Order Details</h2>
          
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">Player UID</span>
              <span className="text-white font-mono" data-testid="order-player-uid">{order.player_uid}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Package</span>
              <span className="text-white">{order.package_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Diamonds</span>
              <span className="text-accent font-bold flex items-center gap-1">
                <Gem className="w-4 h-4" />
                {order.diamonds}
              </span>
            </div>
            <div className="border-t border-white/10 pt-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Total Amount</span>
                <span className="text-white">₹{order.amount}</span>
              </div>
              {order.wallet_used > 0 && (
                <div className="flex justify-between mt-2">
                  <span className="text-gray-400">Wallet Used</span>
                  <span className="text-success">-₹{order.wallet_used}</span>
                </div>
              )}
              <div className="flex justify-between mt-2 font-bold">
                <span className="text-white">Payment Required</span>
                <span className="text-primary">₹{order.payment_amount}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Payment Form */}
        {needsPayment && (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
            <h2 className="text-xl font-heading font-bold text-white">Verify Payment</h2>
            <p className="text-sm text-gray-400">
              Send ₹{order.payment_amount} to our payment account and enter the details below
            </p>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="sent_amount" className="text-gray-300">Amount Sent *</Label>
                <Input
                  id="sent_amount"
                  data-testid="payment-amount-input"
                  type="number"
                  step="0.01"
                  placeholder="Amount you sent"
                  value={paymentForm.sent_amount}
                  onChange={(e) => setPaymentForm({ ...paymentForm, sent_amount: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="last_3_digits" className="text-gray-300">Last 3 Digits of Your Phone *</Label>
                <Input
                  id="last_3_digits"
                  data-testid="payment-last3digits-input"
                  type="text"
                  maxLength={3}
                  placeholder="e.g., 910"
                  value={paymentForm.last_3_digits}
                  onChange={(e) => setPaymentForm({ ...paymentForm, last_3_digits: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
                <p className="text-xs text-gray-500">Last 3 digits of phone linked to payment account</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment_method" className="text-gray-300">Payment Method *</Label>
                <Input
                  id="payment_method"
                  data-testid="payment-method-input"
                  type="text"
                  placeholder="e.g., PhonePe, GPay, Paytm"
                  value={paymentForm.payment_method}
                  onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="remark" className="text-gray-300">Payment Remark (Optional)</Label>
                <Input
                  id="remark"
                  data-testid="payment-remark-input"
                  type="text"
                  placeholder="Any remark you added"
                  value={paymentForm.remark}
                  onChange={(e) => setPaymentForm({ ...paymentForm, remark: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="screenshot" className="text-gray-300">Payment Screenshot URL (Optional)</Label>
                <Input
                  id="screenshot"
                  data-testid="payment-screenshot-input"
                  type="text"
                  placeholder="Upload to imgur and paste URL"
                  value={paymentForm.payment_screenshot}
                  onChange={(e) => setPaymentForm({ ...paymentForm, payment_screenshot: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <Button
                onClick={handleVerifyPayment}
                data-testid="verify-payment-button"
                disabled={submitting}
                className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
              >
                {submitting ? 'Verifying...' : 'Check Payment'}
              </Button>
            </div>
          </div>
        )}

        {/* Success Message */}
        {order.status === 'success' && (
          <div className="bg-success/10 border border-success/20 rounded-2xl p-6 text-center">
            <CheckCircle className="w-16 h-16 text-success mx-auto mb-4" />
            <h3 className="text-2xl font-heading font-bold text-white mb-2">Diamonds Delivered!</h3>
            <p className="text-gray-300">Your {order.diamonds} diamonds have been added to your account.</p>
            <Button
              onClick={() => navigate('/')}
              data-testid="new-order-button"
              className="mt-4 bg-primary text-black font-bold h-10 px-6 rounded-full"
            >
              Make Another Order
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrderStatus;
