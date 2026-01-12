import { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Upload, CreditCard } from 'lucide-react';

const PaymentDetails = () => {
  const { orderId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { updateWalletBalance } = useAuth();
  const [order, setOrder] = useState(location.state?.order || null);
  const [loading, setLoading] = useState(!order);
  const [submitting, setSubmitting] = useState(false);
  
  const useWallet = location.state?.useWallet || false;
  const paymentMethod = location.state?.paymentMethod || 'FonePay';
  
  const [paymentForm, setPaymentForm] = useState({
    sent_amount: '',
    last_3_digits: '',
    remark: '',
    payment_screenshot: ''
  });

  useEffect(() => {
    if (!order) {
      fetchOrder();
    } else {
      // Pre-fill amount
      const walletAmount = useWallet ? Math.min(order.wallet_balance || 0, order.payment_amount) : 0;
      const fonepayAmount = order.payment_amount - walletAmount;
      setPaymentForm(prev => ({
        ...prev,
        sent_amount: fonepayAmount > 0 ? fonepayAmount.toString() : order.payment_amount.toString()
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId, order]);

  const fetchOrder = async () => {
    try {
      const response = await axios.get(`${API}/orders/${orderId}`);
      setOrder(response.data);
      setPaymentForm(prev => ({
        ...prev,
        sent_amount: response.data.payment_amount.toString()
      }));
    } catch (error) {
      toast.error('Failed to load order');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPayment = async () => {
    if (!paymentForm.sent_amount || !paymentForm.last_3_digits) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);

    try {
      const response = await axios.post(`${API}/orders/verify-payment`, {
        order_id: orderId,
        sent_amount: parseFloat(paymentForm.sent_amount),
        last_3_digits: paymentForm.last_3_digits,
        payment_method: paymentMethod,
        payment_screenshot: paymentForm.payment_screenshot || null,
        remark: paymentForm.remark || null
      });

      toast.success(response.data.message);
      
      // Refresh wallet balance
      const walletResponse = await axios.get(`${API}/user/wallet`);
      updateWalletBalance(walletResponse.data.balance);
      
      navigate(`/order/${orderId}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Payment verification failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading...</div>
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

  const walletAmount = useWallet ? Math.min(order.wallet_balance || 0, order.payment_amount) : 0;
  const fonepayAmount = order.payment_amount - walletAmount;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            data-testid="back-button"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="payment-details-title">Payment Details</h1>
            <p className="text-xs text-gray-600">Step 2 of 2</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* FonePay QR Code Section */}
        {fonepayAmount > 0 && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <CreditCard className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-heading font-bold text-gray-900">Scan to Pay with FonePay</h2>
            </div>
            <p className="text-sm text-gray-600 mb-6 text-center">
              Please scan the QR code using your FonePay-supported banking app to complete the payment.
            </p>
            
            {/* QR Code */}
            <div className="bg-gray-100 p-6 rounded-2xl mb-4 flex items-center justify-center">
              <div className="text-center">
                <img 
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=fonepay://pay?amount=${fonepayAmount}&merchant=DiamondStore&ref=${orderId}`}
                  alt="FonePay QR Code"
                  className="w-48 h-48 mx-auto"
                  data-testid="fonepay-qr"
                />
                <p className="text-gray-900 font-bold text-2xl mt-4">₹{fonepayAmount.toFixed(2)}</p>
                <p className="text-gray-600 text-sm">Scan with FonePay App</p>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <p className="text-sm text-yellow-800">
                ⚠️ Please send exactly <strong>₹{fonepayAmount.toFixed(2)}</strong> to ensure automatic payment verification.
              </p>
            </div>
          </div>
        )}

        {/* Payment Summary */}
        <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6">
          <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Payment Summary</h2>
          <div className="space-y-3">
            {useWallet && walletAmount > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-700">Wallet Payment</span>
                <span className="text-green-600 font-semibold">₹{walletAmount.toFixed(2)}</span>
              </div>
            )}
            {fonepayAmount > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-700">FonePay Payment</span>
                <span className="text-primary font-semibold">₹{fonepayAmount.toFixed(2)}</span>
              </div>
            )}
            <div className="border-t border-orange-200 pt-3">
              <div className="flex justify-between">
                <span className="text-gray-900 font-bold">Total Amount</span>
                <span className="text-primary font-bold text-xl">₹{order.payment_amount?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Payment Confirmation Form */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900 mb-2">Confirm Your Payment</h2>
          <p className="text-sm text-gray-600 mb-6">
            After completing the payment, please fill in the details below to verify your transaction.
          </p>

          <div className="space-y-5">
            {/* Amount Sent */}
            <div>
              <label htmlFor="sent_amount" className="block text-sm font-semibold text-gray-900 mb-2">
                Amount Sent (₹) <span className="text-red-500">*</span>
              </label>
              <input
                id="sent_amount"
                data-testid="payment-amount-input"
                type="number"
                step="0.01"
                placeholder="Enter amount you sent"
                value={paymentForm.sent_amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, sent_amount: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                required
              />
            </div>

            {/* Last 3 Digits */}
            <div>
              <label htmlFor="last_3_digits" className="block text-sm font-semibold text-gray-900 mb-2">
                Last 3 Digits of Phone Number <span className="text-red-500">*</span>
              </label>
              <input
                id="last_3_digits"
                data-testid="payment-last3digits-input"
                type="text"
                maxLength={3}
                placeholder="e.g., 910"
                value={paymentForm.last_3_digits}
                onChange={(e) => setPaymentForm({ ...paymentForm, last_3_digits: e.target.value.replace(/\D/g, '') })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                required
              />
              <p className="mt-1 text-xs text-gray-500">Last 3 digits of phone linked to your payment bank/wallet</p>
            </div>

            {/* Remarks */}
            <div>
              <label htmlFor="remark" className="block text-sm font-semibold text-gray-900 mb-2">
                Remarks (Optional)
              </label>
              <input
                id="remark"
                data-testid="payment-remark-input"
                type="text"
                placeholder="Any remark you added during payment"
                value={paymentForm.remark}
                onChange={(e) => setPaymentForm({ ...paymentForm, remark: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
              />
            </div>

            {/* Screenshot */}
            <div>
              <label htmlFor="screenshot" className="block text-sm font-semibold text-gray-900 mb-2">
                Payment Screenshot (Optional)
              </label>
              <div className="relative">
                <input
                  id="screenshot"
                  data-testid="payment-screenshot-input"
                  type="text"
                  placeholder="Upload to imgur and paste URL here"
                  value={paymentForm.payment_screenshot}
                  onChange={(e) => setPaymentForm({ ...paymentForm, payment_screenshot: e.target.value })}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl text-gray-900 bg-white placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                />
                <Upload className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              </div>
              <p className="mt-1 text-xs text-gray-500">Upload screenshot to imgur.com and paste the URL here</p>
            </div>

            {/* Info Box */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <p className="text-sm text-blue-800">
                ℹ️ We will automatically verify your payment using SMS notifications. This usually takes a few seconds.
              </p>
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleVerifyPayment}
              data-testid="verify-payment-button"
              disabled={submitting}
              className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-14 rounded-full transition-all disabled:opacity-50 text-lg"
            >
              {submitting ? 'Verifying Payment...' : 'Check Payment'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentDetails;
