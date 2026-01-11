import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Wallet as WalletIcon, CreditCard } from 'lucide-react';

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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary">Loading...</div>
      </div>
    );
  }

  const walletCanCoverFull = walletBalance >= order.payment_amount;
  const walletAmount = useWallet ? Math.min(walletBalance, order.payment_amount) : 0;
  const fonepayAmount = order.payment_amount - walletAmount;

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
            <h1 className="text-lg font-heading font-bold text-white" data-testid="payment-method-title">Payment Method</h1>
            <p className="text-xs text-gray-400">Step 1 of 2</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Order Summary */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
          <h2 className="text-lg font-heading font-bold text-white mb-4">Order Summary</h2>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Package</span>
              <span className="text-white">{order.package_name}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Order Amount</span>
              <span className="text-white font-bold">₹{order.amount}</span>
            </div>
            {order.wallet_used > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Wallet Used</span>
                <span className="text-success">-₹{order.wallet_used}</span>
              </div>
            )}
            <div className="border-t border-white/10 pt-2 mt-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Payment Required</span>
                <span className="text-primary font-bold text-lg">₹{order.payment_amount}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Wallet Option */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
          <h2 className="text-lg font-heading font-bold text-white mb-4">Your Wallet</h2>
          
          <div className="bg-gradient-to-r from-primary/10 to-secondary/10 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <WalletIcon className="w-8 h-8 text-primary" />
                <div>
                  <p className="text-sm text-gray-400">Available Balance</p>
                  <p className="text-xl font-heading font-bold text-white">₹{walletBalance.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>

          {walletBalance > 0 && (
            <button
              onClick={() => setUseWallet(!useWallet)}
              data-testid="use-wallet-toggle"
              className={`w-full p-4 rounded-xl border-2 transition-all ${
                useWallet
                  ? 'bg-primary/10 border-primary'
                  : 'bg-white/5 border-white/10 hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="text-left">
                  <p className="text-white font-semibold">
                    {walletCanCoverFull ? 'Pay Full Amount with Wallet' : 'Use Wallet (Partial Payment)'}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    {walletCanCoverFull 
                      ? `Pay ₹${order.payment_amount} from wallet`
                      : `Pay ₹${walletBalance.toFixed(2)} from wallet + ₹${(order.payment_amount - walletBalance).toFixed(2)} via FonePay`
                    }
                  </p>
                </div>
                {useWallet && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>
            </button>
          )}
        </div>

        {/* FonePay Option */}
        {(!useWallet || !walletCanCoverFull) && (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
            <h2 className="text-lg font-heading font-bold text-white mb-4">Payment Method</h2>
            
            <button
              onClick={() => setSelectedMethod('FonePay')}
              data-testid="select-fonepay"
              className={`w-full p-4 rounded-xl border-2 transition-all ${
                selectedMethod === 'FonePay'
                  ? 'bg-primary/10 border-primary'
                  : 'bg-white/5 border-white/10 hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
                    <CreditCard className="w-6 h-6 text-primary" />
                  </div>
                  <div className="text-left">
                    <p className="text-white font-semibold">FonePay QR</p>
                    <p className="text-sm text-gray-400">Scan & Pay</p>
                  </div>
                </div>
                {selectedMethod === 'FonePay' && (
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
            <h2 className="text-lg font-heading font-bold text-white mb-4">Payment Breakdown</h2>
            <div className="space-y-3">
              {useWallet && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Wallet Payment</span>
                  <span className="text-success font-semibold">₹{walletAmount.toFixed(2)}</span>
                </div>
              )}
              {fonepayAmount > 0 && selectedMethod && (
                <div className="flex justify-between">
                  <span className="text-gray-400">FonePay Payment</span>
                  <span className="text-primary font-semibold">₹{fonepayAmount.toFixed(2)}</span>
                </div>
              )}
              <div className="border-t border-white/10 pt-3">
                <div className="flex justify-between">
                  <span className="text-white font-bold">Total</span>
                  <span className="text-primary font-bold text-xl">₹{order.payment_amount}</span>
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
          className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
        >
          Continue to Payment Details
        </Button>
      </div>
    </div>
  );
};

export default PaymentMethod;