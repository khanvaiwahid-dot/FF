import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, Wallet as WalletIcon, CreditCard } from 'lucide-react';
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
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/wallet')}
            data-testid="back-button"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="add-funds-title">Add Funds to Wallet</h1>
            <p className="text-xs text-gray-600">Step 1 of 2</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Amount Input */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-6 shadow-sm">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
              <WalletIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-heading font-bold text-gray-900">Enter Amount</h2>
              <p className="text-sm text-gray-600">Minimum ₹10</p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="amount" className="text-gray-700">Amount to Add (₹) *</Label>
            <Input
              id="amount"
              data-testid="wallet-amount-input"
              type="number"
              step="0.01"
              min="10"
              placeholder="Enter amount (min ₹10)"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-16 text-gray-900 text-2xl text-center"
              autoFocus
            />
          </div>

          {/* Quick Amount Buttons */}
          <div>
            <p className="text-sm text-gray-600 mb-3">Quick Select:</p>
            <div className="grid grid-cols-3 gap-3">
              {[100, 500, 1000, 2000, 5000, 10000].map((quickAmount) => (
                <button
                  key={quickAmount}
                  onClick={() => setAmount(quickAmount.toString())}
                  data-testid={`quick-amount-${quickAmount}`}
                  className={`p-3 rounded-xl border-2 transition-all ${
                    amount === quickAmount.toString()
                      ? 'bg-primary/10 border-primary'
                      : 'bg-gray-50 hover:bg-orange-50 border-gray-200 hover:border-primary/50'
                  }`}
                >
                  <p className="text-gray-900 font-semibold">₹{quickAmount.toLocaleString()}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Payment Method Info */}
        <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6">
          <h3 className="text-lg font-heading font-bold text-gray-900 mb-3">Payment Method</h3>
          <div className="flex items-center gap-3 p-4 bg-white border border-orange-200 rounded-xl">
            <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-primary" />
            </div>
            <div>
              <p className="text-gray-900 font-semibold">FonePay QR</p>
              <p className="text-sm text-gray-600">Scan & Pay with your banking app</p>
            </div>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm text-blue-800">
            ℹ️ Funds will be added to your wallet after payment verification. You can use wallet balance for faster checkout on future orders.
          </p>
        </div>

        {/* Continue Button */}
        <Button
          onClick={handleContinue}
          data-testid="continue-to-payment-button"
          disabled={!amount || parseFloat(amount) < 10}
          className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full transition-all disabled:opacity-50"
        >
          Continue to Payment
        </Button>
      </div>
    </div>
  );
};

export default WalletAddFunds;
