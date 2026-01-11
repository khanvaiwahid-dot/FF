import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, Wallet as WalletIcon } from 'lucide-react';
import { toast } from 'sonner';

const WalletAddFunds = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [amount, setAmount] = useState('');

  const handleContinue = () => {
    const parsedAmount = parseFloat(amount);
    
    if (!amount || parsedAmount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    if (parsedAmount < 10) {
      toast.error('Minimum top-up amount is ₹10');
      return;
    }

    // Navigate to payment details
    navigate('/wallet/payment-details', {
      state: {
        amount: parsedAmount,
        type: 'wallet_topup'
      }
    });
  };

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-card/80 backdrop-blur-sm border-b border-white/5 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/wallet')}
            data-testid="back-button"
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-white" data-testid="add-funds-title">Add Funds to Wallet</h1>
            <p className="text-xs text-gray-400">Step 1 of 2</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Amount Input */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
              <WalletIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-heading font-bold text-white">Enter Amount</h2>
              <p className="text-sm text-gray-400">Minimum ₹10</p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="amount" className="text-gray-300">Amount to Add (₹) *</Label>
            <Input
              id="amount"
              data-testid="wallet-amount-input"
              type="number"
              step="0.01"
              min="10"
              placeholder="Enter amount (min ₹10)"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-16 text-white text-2xl text-center"
              autoFocus
            />
          </div>

          {/* Quick Amount Buttons */}
          <div>
            <p className="text-sm text-gray-400 mb-3">Quick Select:</p>
            <div className="grid grid-cols-3 gap-3">
              {[100, 500, 1000, 2000, 5000, 10000].map((quickAmount) => (
                <button
                  key={quickAmount}
                  onClick={() => setAmount(quickAmount.toString())}
                  data-testid={`quick-amount-${quickAmount}`}
                  className="p-3 bg-white/5 hover:bg-primary/10 border border-white/10 hover:border-primary rounded-xl transition-all"
                >
                  <p className="text-white font-semibold">₹{quickAmount}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Payment Method Info */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
          <h3 className="text-lg font-heading font-bold text-white mb-3">Payment Method</h3>
          <div className="flex items-center gap-3 p-4 bg-primary/10 border border-primary/20 rounded-xl">
            <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <div>
              <p className="text-white font-semibold">FonePay QR</p>
              <p className="text-sm text-gray-400">Scan & Pay with your banking app</p>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-info/10 border border-info/20 rounded-xl p-4">
          <p className="text-sm text-info">
            ℹ️ Funds will be added to your wallet after payment verification. You can use wallet balance for faster checkout on future orders.
          </p>
        </div>

        {/* Continue Button */}
        <Button
          onClick={handleContinue}
          data-testid="continue-to-payment-button"
          disabled={!amount || parseFloat(amount) < 10}
          className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
        >
          Continue to Payment
        </Button>
      </div>
    </div>
  );
};

export default WalletAddFunds;