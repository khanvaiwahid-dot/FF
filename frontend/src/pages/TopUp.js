import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Gem, Wallet as WalletIcon, LogOut, ChevronRight } from 'lucide-react';

const TopUp = () => {
  const navigate = useNavigate();
  const { user, logout, updateWalletBalance } = useAuth();
  const [packages, setPackages] = useState([]);
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [playerUID, setPlayerUID] = useState('');
  const [loading, setLoading] = useState(false);
  const [walletBalance, setWalletBalance] = useState(user?.walletBalance || 0);

  useEffect(() => {
    fetchPackages();
    fetchUserProfile();
  }, []);

  const fetchPackages = async () => {
    try {
      const response = await axios.get(`${API}/packages/list`);
      setPackages(response.data);
    } catch (error) {
      toast.error('Failed to load packages');
    }
  };

  const fetchUserProfile = async () => {
    try {
      const response = await axios.get(`${API}/user/profile`);
      setWalletBalance(response.data.wallet_balance);
      updateWalletBalance(response.data.wallet_balance);
    } catch (error) {
      console.error('Failed to fetch profile');
    }
  };

  const handleCreateOrder = async () => {
    if (!selectedPackage) {
      toast.error('Please select a diamond package');
      return;
    }

    if (!playerUID) {
      toast.error('Please enter your Player UID');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(`${API}/orders/create`, {
        player_uid: playerUID,
        package_id: selectedPackage.id
      });

      const { order_id, status, payment_amount } = response.data;

      if (status === 'wallet_fully_paid') {
        toast.success('Order paid using wallet! Processing your diamonds...');
        fetchUserProfile();
        navigate(`/order/${order_id}`);
      } else {
        // Navigate to payment method selection
        navigate(`/payment/${order_id}`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-gradient-to-b from-card/80 to-transparent backdrop-blur-sm border-b border-white/5 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
              <Gem className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-heading font-bold text-white" data-testid="topup-title">DiamondStore</h1>
              <p className="text-xs text-gray-400">@{user?.username}</p>
            </div>
          </div>
          <Button
            onClick={logout}
            data-testid="logout-button"
            variant="ghost"
            size="sm"
            className="text-gray-400 hover:text-white"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Wallet Card */}
        <div
          onClick={() => navigate('/wallet')}
          data-testid="wallet-card"
          className="bg-gradient-to-r from-primary/20 to-secondary/20 backdrop-blur-xl border border-white/10 rounded-2xl p-6 cursor-pointer hover:border-primary/30 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center">
                <WalletIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-gray-300 text-sm">Wallet Balance</p>
                <p className="text-2xl font-heading font-bold text-white" data-testid="wallet-balance">₹{walletBalance.toFixed(2)}</p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </div>
        </div>

        {/* Player UID Section */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
          <h2 className="text-xl font-heading font-bold text-white">Player Details</h2>
          
          <div className="space-y-2">
            <Label htmlFor="playerUID" className="text-gray-300">Free Fire Player UID *</Label>
            <Input
              id="playerUID"
              data-testid="player-uid-input"
              type="text"
              placeholder="Enter your Player UID"
              value={playerUID}
              onChange={(e) => setPlayerUID(e.target.value)}
              className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Server</Label>
            <div className="bg-white/5 border border-white/10 rounded-xl h-12 flex items-center px-4">
              <span className="text-white font-semibold">🇧🇩 Bangladesh</span>
            </div>
            <p className="text-xs text-gray-500">Server is fixed to Bangladesh</p>
          </div>
        </div>

        {/* Packages Section */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
          <h2 className="text-xl font-heading font-bold text-white">Select Diamond Package</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {packages.map((pkg) => (
              <button
                key={pkg.id}
                data-testid={`package-${pkg.diamonds}`}
                onClick={() => setSelectedPackage(pkg)}
                className={`relative p-4 rounded-xl border-2 transition-all ${
                  selectedPackage?.id === pkg.id
                    ? 'bg-primary/10 border-primary shadow-[0_0_20px_rgba(0,240,255,0.3)]'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-2">
                    <Gem className={`w-5 h-5 ${selectedPackage?.id === pkg.id ? 'text-primary' : 'text-accent'}`} />
                    <p className="text-2xl font-heading font-bold text-white">{pkg.diamonds}</p>
                  </div>
                  <p className="text-xs text-gray-400 mb-1">{pkg.name}</p>
                  <p className="text-lg font-bold text-primary">₹{pkg.price}</p>
                </div>
                {selectedPackage?.id === pkg.id && (
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Order Summary */}
        {selectedPackage && (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
            <h2 className="text-xl font-heading font-bold text-white">Order Summary</h2>
            
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Package</span>
                <span className="text-white font-semibold">{selectedPackage.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Server</span>
                <span className="text-white font-semibold">🇧🇩 Bangladesh</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Amount</span>
                <span className="text-white font-semibold">₹{selectedPackage.price}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Wallet Balance</span>
                <span className="text-primary font-semibold">₹{walletBalance.toFixed(2)}</span>
              </div>
            </div>

            <Button
              onClick={handleCreateOrder}
              data-testid="create-order-button"
              disabled={loading}
              className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
            >
              {loading ? 'Creating Order...' : 'Continue to Payment'}
            </Button>
          </div>
        )}
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-card/80 backdrop-blur-xl border-t border-white/5 z-20">
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => navigate('/')}
            data-testid="nav-topup"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <Gem className="w-5 h-5" />
            <span className="text-xs font-medium">Top-Up</span>
          </button>
          <button
            onClick={() => navigate('/wallet')}
            data-testid="nav-wallet"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <WalletIcon className="w-5 h-5" />
            <span className="text-xs">Wallet</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TopUp;