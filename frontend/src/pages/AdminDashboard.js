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
  Clock,
  Shield,
  Users,
  MessageSquare
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading dashboard...</div>
      </div>
    );
  }

  const chartData = [
    { name: 'Success', value: stats.success_orders, fill: '#28A745' },
    { name: 'Pending', value: stats.pending_orders, fill: '#FFC107' },
    { name: 'Failed', value: stats.failed_orders, fill: '#DC3545' },
    { name: 'Review', value: stats.suspicious_orders, fill: '#FF6B35' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
              <LayoutDashboard className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="admin-dashboard-title">Admin Dashboard</h1>
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

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm" data-testid="stat-card-sales">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-primary" />
              </div>
            </div>
            <p className="text-gray-600 text-sm">Total Sales</p>
            <p className="text-3xl font-heading font-bold text-gray-900">₹{stats.total_sales.toFixed(2)}</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm" data-testid="stat-card-orders">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <Package className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-gray-600 text-sm">Total Orders</p>
            <p className="text-3xl font-heading font-bold text-gray-900">{stats.total_orders}</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm" data-testid="stat-card-failed">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
            </div>
            <p className="text-gray-600 text-sm">Failed Orders</p>
            <p className="text-3xl font-heading font-bold text-gray-900">{stats.failed_orders}</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm" data-testid="stat-card-wallet">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                <Wallet className="w-5 h-5 text-orange-600" />
              </div>
            </div>
            <p className="text-gray-600 text-sm">Wallet Balance</p>
            <p className="text-3xl font-heading font-bold text-gray-900">₹{stats.total_wallet_balance.toFixed(2)}</p>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900 mb-4">Order Status Overview</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Quick Actions - Management */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/admin/products"
            data-testid="quick-action-products"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-primary hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                <Package className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Products</p>
                <p className="text-xs text-gray-600">Manage pricing</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Create, edit, and manage product prices</p>
          </Link>

          <Link
            to="/admin/garena-accounts"
            data-testid="quick-action-garena"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-secondary hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-secondary/10 rounded-lg flex items-center justify-center">
                <Shield className="w-6 h-6 text-secondary" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Garena Accounts</p>
                <p className="text-xs text-gray-600">Automation credentials</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Manage Garena accounts for automation</p>
          </Link>

          <Link
            to="/admin/users"
            data-testid="quick-action-users"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-accent hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-accent" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Users</p>
                <p className="text-xs text-gray-600">User management</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Create, block, and manage users</p>
          </Link>
        </div>

        {/* Order Management Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/admin/orders"
            data-testid="quick-action-orders"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-primary hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                <Package className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Manage Orders</p>
                <p className="text-xs text-gray-600">{stats.total_orders} total orders</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">View and manage all orders</p>
          </Link>

          <Link
            to="/admin/review"
            data-testid="quick-action-review"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-warning hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Manual Review</p>
                <p className="text-xs text-gray-600">{stats.suspicious_orders + stats.duplicate_orders + stats.failed_orders} need review</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Review flagged orders</p>
          </Link>

          <Link
            to="/admin/payments"
            data-testid="quick-action-payments"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-secondary hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-secondary/10 rounded-full flex items-center justify-center">
                <Inbox className="w-6 h-6 text-secondary" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Payment Inbox</p>
                <p className="text-xs text-gray-600">Unmatched payments</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Match pending payments</p>
          </Link>
        </div>

        {/* Status Breakdown */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-xl font-heading font-bold text-gray-900 mb-4">Order Status Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-green-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <p className="text-sm text-gray-600">Success</p>
              </div>
              <p className="text-2xl font-bold text-green-600">{stats.success_orders}</p>
            </div>
            <div className="bg-yellow-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-yellow-600" />
                <p className="text-sm text-gray-600">Pending</p>
              </div>
              <p className="text-2xl font-bold text-yellow-600">{stats.pending_orders}</p>
            </div>
            <div className="bg-red-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <p className="text-sm text-gray-600">Failed</p>
              </div>
              <p className="text-2xl font-bold text-red-600">{stats.failed_orders}</p>
            </div>
            <div className="bg-orange-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-orange-600" />
                <p className="text-sm text-gray-600">Suspicious</p>
              </div>
              <p className="text-2xl font-bold text-orange-600">{stats.suspicious_orders}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-20 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-around">
          <button
            data-testid="nav-dashboard"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="text-xs font-medium">Dashboard</span>
          </button>
          <button
            onClick={() => navigate('/admin/orders')}
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs">Orders</span>
          </button>
          <button
            onClick={() => navigate('/admin/review')}
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs">Review</span>
          </button>
          <button
            onClick={() => navigate('/admin/payments')}
            data-testid="nav-payments"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
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
