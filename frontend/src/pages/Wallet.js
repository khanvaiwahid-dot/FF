import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Wallet as WalletIcon, ArrowLeft, Plus, Minus, Gem } from 'lucide-react';

const Wallet = () => {
  const navigate = useNavigate();
  const { user, updateWalletBalance } = useAuth();
  const [walletData, setWalletData] = useState({ balance: 0, transactions: [] });
  const [loading, setLoading] = useState(true);
  const [showAddFunds, setShowAddFunds] = useState(false);
  const [addFundsForm, setAddFundsForm] = useState({
    amount: '',
    last_3_digits: '',
    payment_method: '',
    remark: ''
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchWallet();
  }, []);

  const fetchWallet = async () => {
    try {
      const response = await axios.get(`${API}/user/wallet`);
      setWalletData(response.data);
      updateWalletBalance(response.data.balance);
    } catch (error) {
      toast.error('Failed to load wallet');
    } finally {
      setLoading(false);
    }
  };

  const handleAddFunds = async () => {
    if (!addFundsForm.amount || !addFundsForm.last_3_digits || !addFundsForm.payment_method) {
      toast.error('Please fill in all required fields');
      return;
    }

    setSubmitting(true);

    try {
      // Create a wallet top-up order (similar to regular orders but for wallet)
      const response = await axios.post(`${API}/sms/receive`, {
        raw_message: `Wallet top-up: Rs ${addFundsForm.amount} from XXX****${addFundsForm.last_3_digits} for RRN ${Date.now()}, ${addFundsForm.remark} /${addFundsForm.payment_method}`
      });

      toast.success('Payment submitted! We\'ll verify and add to your wallet shortly.');
      setShowAddFunds(false);
      setAddFundsForm({ amount: '', last_3_digits: '', payment_method: '', remark: '' });
      
      // Refresh wallet
      setTimeout(fetchWallet, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit payment');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary">Loading wallet...</div>
      </div>
    );
  }

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
            <h1 className="text-lg font-heading font-bold text-white" data-testid="wallet-title">My Wallet</h1>
            <p className="text-xs text-gray-400">@{user?.username}</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Balance Card */}
        <div className="bg-gradient-to-br from-primary/20 to-secondary/20 backdrop-blur-xl border border-white/10 rounded-2xl p-8">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center">
              <WalletIcon className="w-8 h-8 text-white" />
            </div>
          </div>
          <div className="text-center">
            <p className="text-gray-300 text-sm mb-2">Available Balance</p>
            <p className="text-5xl font-heading font-bold text-white mb-6" data-testid="wallet-balance">₹{walletData.balance.toFixed(2)}</p>
            <Button
              onClick={() => setShowAddFunds(!showAddFunds)}
              data-testid="add-funds-button"
              className="bg-primary text-black font-bold h-12 px-8 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
            >
              <Plus className="w-5 h-5 mr-2" />
              Add Funds
            </Button>
          </div>
        </div>

        {/* Add Funds Form */}
        {showAddFunds && (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
            <h2 className="text-xl font-heading font-bold text-white">Add Funds to Wallet</h2>
            <p className="text-sm text-gray-400">
              Send money to our payment account and enter details below
            </p>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="amount" className="text-gray-300">Amount *</Label>
                <Input
                  id="amount"
                  data-testid="add-funds-amount-input"
                  type="number"
                  step="0.01"
                  placeholder="Enter amount"
                  value={addFundsForm.amount}
                  onChange={(e) => setAddFundsForm({ ...addFundsForm, amount: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="last_3_digits_wallet" className="text-gray-300">Last 3 Digits of Your Phone *</Label>
                <Input
                  id="last_3_digits_wallet"
                  data-testid="add-funds-last3digits-input"
                  type="text"
                  maxLength={3}
                  placeholder="e.g., 910"
                  value={addFundsForm.last_3_digits}
                  onChange={(e) => setAddFundsForm({ ...addFundsForm, last_3_digits: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="payment_method_wallet" className="text-gray-300">Payment Method *</Label>
                <Input
                  id="payment_method_wallet"
                  data-testid="add-funds-method-input"
                  type="text"
                  placeholder="e.g., PhonePe, GPay"
                  value={addFundsForm.payment_method}
                  onChange={(e) => setAddFundsForm({ ...addFundsForm, payment_method: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="remark_wallet" className="text-gray-300">Remark (Optional)</Label>
                <Input
                  id="remark_wallet"
                  data-testid="add-funds-remark-input"
                  type="text"
                  placeholder="Any remark"
                  value={addFundsForm.remark}
                  onChange={(e) => setAddFundsForm({ ...addFundsForm, remark: e.target.value })}
                  className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>

              <Button
                onClick={handleAddFunds}
                data-testid="submit-funds-button"
                disabled={submitting}
                className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
              >
                {submitting ? 'Submitting...' : 'Submit Payment'}
              </Button>
            </div>
          </div>
        )}

        {/* Transaction History */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
          <h2 className="text-xl font-heading font-bold text-white">Transaction History</h2>
          
          {walletData.transactions.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <WalletIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No transactions yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {walletData.transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  data-testid={`transaction-${transaction.id}`}
                  className="bg-white/5 border border-white/5 rounded-xl p-4 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        transaction.amount > 0 ? 'bg-success/10' : 'bg-error/10'
                      }`}>
                        {transaction.amount > 0 ? (
                          <Plus className="w-5 h-5 text-success" />
                        ) : (
                          <Minus className="w-5 h-5 text-error" />
                        )}
                      </div>
                      <div>
                        <p className="text-white font-semibold">
                          {transaction.type === 'order_payment' ? 'Order Payment' : 
                           transaction.type === 'wallet_topup' ? 'Wallet Top-up' : 
                           transaction.type}
                        </p>
                        <p className="text-xs text-gray-400">{formatDate(transaction.created_at)}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${
                        transaction.amount > 0 ? 'text-success' : 'text-error'
                      }`}>
                        {transaction.amount > 0 ? '+' : ''}₹{Math.abs(transaction.amount).toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-400">Balance: ₹{transaction.balance_after.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-card/80 backdrop-blur-xl border-t border-white/5 z-20">
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => navigate('/')}
            data-testid="nav-topup"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <Gem className="w-5 h-5" />
            <span className="text-xs">Top-Up</span>
          </button>
          <button
            data-testid="nav-wallet"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <WalletIcon className="w-5 h-5" />
            <span className="text-xs font-medium">Wallet</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Wallet;