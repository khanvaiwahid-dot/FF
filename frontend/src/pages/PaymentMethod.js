import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Wallet as WalletIcon, CreditCard, CheckCircle } from 'lucide-react';

const PaymentMethod = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { user, updateWalletBalance } = useAuth();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [walletBalance, setWalletBalance] = useState(0);
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [useWallet, setUseWallet] = useState(false);

  useEffect(() => {
    fetchOrder();
    fetchWallet();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  const fetchOrder = async () => {
    try {
      const response = await axios.get(`${API}/orders/${orderId}`);
      setOrder(response.data);
    } catch (error) {
      toast.error('Failed to load order');
    } finally {
      setLoading(false);
    }
  };

  const fetchWallet = async () => {
    try {
      const response = await axios.get(`${API}/user/wallet`);
      setWalletBalance(response.data.balance);
      updateWalletBalance(response.data.balance);
    } catch (error) {
      console.error('Failed to fetch wallet');
    }
  };

  const handleContinue = () => {
    if (!selectedMethod && !useWallet) {
      toast.error('Please select a payment method');
      return;
    }

    // Navigate to payment details
    navigate(`/payment-details/${orderId}`, {
      state: {
        useWallet,
        paymentMethod: selectedMethod,
        order
      }
    });
  };

  if (loading || !order) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading...</div>
      </div>
    );
  }

  // Check if order is already fully paid by wallet
  const alreadyPaidByWallet = order.wallet_used > 0 && order.payment_amount === 0;
  
  // Calculate potential wallet usage
  const walletCanCoverFull = walletBalance >= order.payment_amount && order.payment_amount > 0;
  const walletAmount = useWallet ? Math.min(walletBalance, order.payment_amount) : 0;
  const fonepayAmount = order.payment_amount - walletAmount;

  // If already paid by wallet, show success
  if (alreadyPaidByWallet) {
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
              <h1 className="text-lg font-heading font-bold text-gray-900">Payment Complete</h1>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          <div className="bg-green-50 border border-green-200 rounded-2xl p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-heading font-bold text-gray-900 mb-2">Payment Successful!</h2>
            <p className="text-gray-600 mb-4">Your order has been paid using your wallet balance.</p>
            
            <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6 inline-block">
              <div className="text-sm text-gray-600">Amount Paid</div>
              <div className="text-3xl font-bold text-green-600">₹{order.wallet_used?.toFixed(2)}</div>
              <div className="text-xs text-gray-500">from wallet</div>
            </div>

            <div className="space-y-3">
              <Button
                onClick={() => navigate(`/order/${orderId}`)}
                data-testid="view-order-button"
                className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full"
              >
                View Order Status
              </Button>
              <Button
                onClick={() => navigate('/')}
                variant="outline"
                className="w-full border-gray-300 text-gray-700 hover:bg-gray-50 h-12 rounded-full"
              >
                Back to Home
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="payment-method-title">Payment Method</h1>
            <p className="text-xs text-gray-600">Step 1 of 2</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Order Summary */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Order Summary</h2>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Package</span>
              <span className="text-gray-900 font-semibold">{order.package_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Order Amount</span>
              <span className="text-gray-900 font-bold">₹{order.locked_price?.toFixed(2) || order.amount}</span>
            </div>
            {order.wallet_used > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Wallet Used</span>
                <span className="text-green-600">-₹{order.wallet_used?.toFixed(2)}</span>
              </div>
            )}
            <div className="border-t border-gray-200 pt-2 mt-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Payment Required</span>
                <span className="text-primary font-bold text-lg">₹{order.payment_amount?.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Wallet Option */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Your Wallet</h2>
          
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <WalletIcon className="w-8 h-8 text-primary" />
                <div>
                  <p className="text-sm text-gray-600">Available Balance</p>
                  <p className="text-xl font-heading font-bold text-gray-900">₹{walletBalance.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>

          {walletBalance > 0 && order.payment_amount > 0 && (
            <button
              onClick={() => setUseWallet(!useWallet)}
              data-testid="use-wallet-toggle"
              className={`w-full p-4 rounded-xl border-2 transition-all ${
                useWallet
                  ? 'bg-primary/10 border-primary'
                  : 'bg-gray-50 border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-left">
                  <p className="text-gray-900 font-semibold">
                    {walletCanCoverFull ? 'Pay Full Amount with Wallet' : 'Use Wallet (Partial Payment)'}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {walletCanCoverFull 
                      ? `Pay ₹${order.payment_amount?.toFixed(2)} from your wallet`
                      : `Pay ₹${walletBalance.toFixed(2)} from wallet + ₹${(order.payment_amount - walletBalance).toFixed(2)} via FonePay`
                    }
                  </p>
                </div>
                {useWallet && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
            </button>
          )}

          {walletBalance === 0 && (
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
              <p className="text-gray-500 text-sm">No wallet balance available</p>
            </div>
          )}
        </div>

        {/* FonePay Option */}
        {(!useWallet || !walletCanCoverFull) && (
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Payment Method</h2>
            
            <button
              onClick={() => setSelectedMethod('FonePay')}
              data-testid="select-fonepay"
              className={`w-full p-4 rounded-xl border-2 transition-all ${
                selectedMethod === 'FonePay'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-gray-50 border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                    <CreditCard className="w-6 h-6 text-primary" />
                  </div>
                  <div className="text-left">
                    <p className="text-gray-900 font-semibold">FonePay QR</p>
                    <p className="text-sm text-gray-600">Scan & Pay</p>
                  </div>
                </div>
                {selectedMethod === 'FonePay' && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
            </button>
          </div>
        )}

        {/* Payment Breakdown */}
        {(useWallet || selectedMethod) && (
          <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6">
            <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Payment Breakdown</h2>
            <div className="space-y-3">
              {useWallet && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Wallet Payment</span>
                  <span className="text-green-600 font-semibold">₹{walletAmount.toFixed(2)}</span>
                </div>
              )}
              {fonepayAmount > 0 && selectedMethod && (
                <div className="flex justify-between">
                  <span className="text-gray-600">FonePay Payment</span>
                  <span className="text-primary font-semibold">₹{fonepayAmount.toFixed(2)}</span>
                </div>
              )}
              <div className="border-t border-orange-200 pt-3">
                <div className="flex justify-between">
                  <span className="text-gray-900 font-bold">Total</span>
                  <span className="text-primary font-bold text-xl">₹{order.payment_amount?.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Continue Button */}
        <Button
          onClick={handleContinue}
          data-testid="continue-button"
          disabled={!selectedMethod && !useWallet}
          className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full transition-all disabled:opacity-50"
        >
          Continue to Payment Details
        </Button>
      </div>
    </div>
  );
};

export default PaymentMethod;
