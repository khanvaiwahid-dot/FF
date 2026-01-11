import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { 
  LayoutDashboard, 
  Package, 
  AlertTriangle, 
  DollarSign, 
  Wallet,
  LogOut,
  FileText,
  Inbox,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API}/admin/dashboard`);
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary">Loading dashboard...</div>
      </div>
    );
  }

  const chartData = [
    { name: 'Success', value: stats.success_orders, fill: '#00FF94' },
    { name: 'Pending', value: stats.pending_orders, fill: '#FFBA00' },
    { name: 'Failed', value: stats.failed_orders, fill: '#FF2E2E' },
    { name: 'Review', value: stats.suspicious_orders, fill: '#B026FF' }
  ];

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-card/80 backdrop-blur-sm border-b border-white/5 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-secondary/10 rounded-full flex items-center justify-center">
              <LayoutDashboard className="w-5 h-5 text-secondary" />
            </div>
            <div>
              <h1 className="text-lg font-heading font-bold text-white" data-testid="admin-dashboard-title">Admin Dashboard</h1>
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

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6" data-testid="stat-card-sales">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-primary" />
              </div>
            </div>
            <p className="text-gray-400 text-sm">Total Sales</p>
            <p className="text-3xl font-heading font-bold text-white">₹{stats.total_sales.toFixed(2)}</p>
          </div>

          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6" data-testid="stat-card-orders">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-success/10 rounded-full flex items-center justify-center">
                <Package className="w-5 h-5 text-success" />
              </div>
            </div>
            <p className="text-gray-400 text-sm">Total Orders</p>
            <p className="text-3xl font-heading font-bold text-white">{stats.total_orders}</p>
          </div>

          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6" data-testid="stat-card-failed">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-error/10 rounded-full flex items-center justify-center">
                <XCircle className="w-5 h-5 text-error" />
              </div>
            </div>
            <p className="text-gray-400 text-sm">Failed Orders</p>
            <p className="text-3xl font-heading font-bold text-white">{stats.failed_orders}</p>
          </div>

          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6" data-testid="stat-card-wallet">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-accent/10 rounded-full flex items-center justify-center">
                <Wallet className="w-5 h-5 text-accent" />
              </div>
            </div>
            <p className="text-gray-400 text-sm">Wallet Balance</p>
            <p className="text-3xl font-heading font-bold text-white">₹{stats.total_wallet_balance.toFixed(2)}</p>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-heading font-bold text-white mb-4">Order Status Overview</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="name" stroke="#999" />
              <YAxis stroke="#999" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#121218', 
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/admin/orders"
            data-testid="quick-action-orders"
            className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-white font-bold">Manage Orders</p>
                <p className="text-xs text-gray-400">{stats.total_orders} total orders</p>
              </div>
            </div>
            <p className="text-sm text-gray-400">View and manage all orders</p>
          </Link>

          <Link
            to="/admin/review"
            data-testid="quick-action-review"
            className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 hover:border-warning/30 transition-colors"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-warning/10 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-warning" />
              </div>
              <div>
                <p className="text-white font-bold">Manual Review</p>
                <p className="text-xs text-gray-400">{stats.suspicious_orders + stats.duplicate_orders + stats.failed_orders} need review</p>
              </div>
            </div>
            <p className="text-sm text-gray-400">Review flagged orders</p>
          </Link>

          <Link
            to="/admin/payments"
            data-testid="quick-action-payments"
            className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 hover:border-secondary/30 transition-colors"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-secondary/10 rounded-full flex items-center justify-center">
                <Inbox className="w-6 h-6 text-secondary" />
              </div>
              <div>
                <p className="text-white font-bold">Payment Inbox</p>
                <p className="text-xs text-gray-400">Unmatched payments</p>
              </div>
            </div>
            <p className="text-sm text-gray-400">Match pending payments</p>
          </Link>
        </div>

        {/* Status Breakdown */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-heading font-bold text-white mb-4">Order Status Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-success" />
                <p className="text-sm text-gray-400">Success</p>
              </div>
              <p className="text-2xl font-bold text-success">{stats.success_orders}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-warning" />
                <p className="text-sm text-gray-400">Pending</p>
              </div>
              <p className="text-2xl font-bold text-warning">{stats.pending_orders}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-4 h-4 text-error" />
                <p className="text-sm text-gray-400">Failed</p>
              </div>
              <p className="text-2xl font-bold text-error">{stats.failed_orders}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-secondary" />
                <p className="text-sm text-gray-400">Suspicious</p>
              </div>
              <p className="text-2xl font-bold text-secondary">{stats.suspicious_orders}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-card/80 backdrop-blur-xl border-t border-white/5 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-around">
          <button
            data-testid="nav-dashboard"
            className="flex flex-col items-center gap-1 text-secondary"
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="text-xs font-medium">Dashboard</span>
          </button>
          <button
            onClick={() => navigate('/admin/orders')}
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs">Orders</span>
          </button>
          <button
            onClick={() => navigate('/admin/review')}
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs">Review</span>
          </button>
          <button
            onClick={() => navigate('/admin/payments')}
            data-testid="nav-payments"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <Inbox className="w-5 h-5" />
            <span className="text-xs">Payments</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
