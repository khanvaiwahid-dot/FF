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
        navigate(`/payment/${order_id}`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  // Group packages by type
  const diamondPackages = packages.filter(p => p.type === 'diamond');
  const membershipPackages = packages.filter(p => p.type === 'membership');
  const evoPackages = packages.filter(p => p.type === 'evo_access');

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
              <Gem className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="topup-title">DiamondStore</h1>
              <p className="text-xs text-gray-600">@{user?.username}</p>
            </div>
          </div>
          <Button
            onClick={logout}
            data-testid="logout-button"
            variant="ghost"
            size="sm"
            className="text-gray-600 hover:text-gray-900"
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
          className="garena-gradient rounded-2xl p-6 cursor-pointer hover:shadow-lg transition-all"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                <WalletIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <p className="text-white/80 text-sm">Wallet Balance</p>
                <p className="text-2xl font-heading font-bold text-white" data-testid="wallet-balance">₹{walletBalance.toFixed(2)}</p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-white/60" />
          </div>
        </div>

        {/* Player UID Section */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900">Player Details</h2>
          
          <div className="space-y-2">
            <Label htmlFor="playerUID" className="text-gray-700">Free Fire Player UID *</Label>
            <Input
              id="playerUID"
              data-testid="player-uid-input"
              type="text"
              placeholder="Enter your Player UID"
              value={playerUID}
              onChange={(e) => setPlayerUID(e.target.value)}
              className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-700">Server</Label>
            <div className="bg-gray-100 border border-gray-200 rounded-xl h-12 flex items-center px-4">
              <span className="text-gray-900 font-semibold">🇧🇩 Bangladesh</span>
            </div>
            <p className="text-xs text-gray-500">Server is fixed to Bangladesh</p>
          </div>
        </div>

        {/* Diamond Packages */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900">Diamond Packages</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {diamondPackages.map((pkg) => (
              <button
                key={pkg.id}
                data-testid={`package-${pkg.amount}`}
                onClick={() => setSelectedPackage(pkg)}
                className={`relative p-4 rounded-xl border-2 transition-all ${
                  selectedPackage?.id === pkg.id
                    ? 'bg-primary/10 border-primary shadow-md'
                    : 'bg-white border-gray-200 hover:border-primary/50'
                }`}
              >
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 mb-2">
                    <Gem className={`w-5 h-5 ${selectedPackage?.id === pkg.id ? 'text-primary' : 'text-orange-500'}`} />
                    <p className="text-xl font-heading font-bold text-gray-900">{pkg.amount}</p>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">{pkg.name}</p>
                  <p className="text-lg font-bold text-primary">₹{pkg.price}</p>
                </div>
                {selectedPackage?.id === pkg.id && (
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Membership & Evo Access */}
        {(membershipPackages.length > 0 || evoPackages.length > 0) && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
            <h2 className="text-xl font-heading font-bold text-gray-900">Memberships & Evo Access</h2>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {[...membershipPackages, ...evoPackages].map((pkg) => (
                <button
                  key={pkg.id}
                  data-testid={`package-${pkg.type}-${pkg.amount}`}
                  onClick={() => setSelectedPackage(pkg)}
                  className={`relative p-4 rounded-xl border-2 transition-all ${
                    selectedPackage?.id === pkg.id
                      ? 'bg-secondary/10 border-secondary shadow-md'
                      : 'bg-white border-gray-200 hover:border-secondary/50'
                  }`}
                >
                  <div className="text-center">
                    <p className="text-sm font-bold text-gray-900 mb-1">{pkg.name}</p>
                    <p className="text-xs text-gray-600 mb-2">{pkg.amount} days</p>
                    <p className="text-lg font-bold text-secondary">₹{pkg.price}</p>
                  </div>
                  {selectedPackage?.id === pkg.id && (
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-secondary rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Order Summary */}
        {selectedPackage && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4 shadow-sm">
            <h2 className="text-xl font-heading font-bold text-gray-900">Order Summary</h2>
            
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Package</span>
                <span className="text-gray-900 font-semibold">{selectedPackage.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Server</span>
                <span className="text-gray-900 font-semibold">Bangladesh</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Wallet Balance</span>
                <span className="text-gray-900 font-semibold">₹{walletBalance.toFixed(2)}</span>
              </div>
              <div className="border-t border-gray-200 pt-3 flex justify-between">
                <span className="text-gray-900 font-bold">Total</span>
                <span className="text-xl font-bold text-primary">₹{selectedPackage.price}</span>
              </div>
              {walletBalance > 0 && walletBalance < selectedPackage.price && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                  <p className="text-sm text-orange-800">
                    Wallet will cover ₹{walletBalance.toFixed(2)}. Remaining ₹{(selectedPackage.price - walletBalance).toFixed(2)} via payment.
                  </p>
                </div>
              )}
              {walletBalance >= selectedPackage.price && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm text-green-800">
                    Your wallet has sufficient balance. Order will be paid using wallet.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Proceed Button */}
        <Button
          onClick={handleCreateOrder}
          data-testid="proceed-button"
          disabled={loading || !selectedPackage || !playerUID}
          className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-14 rounded-full transition-all disabled:opacity-50"
        >
          {loading ? 'Creating Order...' : 'Proceed to Payment'}
        </Button>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-20 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-around">
          <button
            data-testid="nav-home"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <Gem className="w-5 h-5" />
            <span className="text-xs font-medium">Top Up</span>
          </button>
          <button
            onClick={() => navigate('/wallet')}
            data-testid="nav-wallet"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
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
