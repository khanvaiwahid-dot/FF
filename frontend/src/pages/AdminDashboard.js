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
  MessageSquare,
  ClipboardList
} from 'lucide-react';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [automationStatus, setAutomationStatus] = useState(null);
  const [processingOrder, setProcessingOrder] = useState(null);

  useEffect(() => {
    fetchDashboardStats();
    fetchAutomationStatus();
    // Poll automation status every 10 seconds
    const interval = setInterval(fetchAutomationStatus, 10000);
    return () => clearInterval(interval);
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

  const fetchAutomationStatus = async () => {
    try {
      const response = await axios.get(`${API}/admin/automation/queue`);
      setAutomationStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch automation status');
    }
  };

  const handleProcessOrder = async (orderId) => {
    setProcessingOrder(orderId);
    try {
      await axios.post(`${API}/admin/orders/${orderId}/process`);
      toast.success('Automation started');
      setTimeout(fetchAutomationStatus, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start automation');
    } finally {
      setProcessingOrder(null);
    }
  };

  const handleProcessAll = async () => {
    try {
      const response = await axios.post(`${API}/admin/automation/process-all`);
      toast.success(`Processing ${response.data.queued_count} orders`);
      setTimeout(fetchAutomationStatus, 2000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process orders');
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

        {/* Automation Status Panel */}
        {automationStatus && (automationStatus.queued_count > 0 || automationStatus.processing_count > 0) && (
          <div className="bg-white border-2 border-orange-400 rounded-xl p-6 shadow-md">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <Clock className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h2 className="text-lg font-heading font-bold text-gray-900">Automation Queue</h2>
                  <p className="text-sm text-gray-600">
                    {automationStatus.queued_count} queued, {automationStatus.processing_count} processing
                  </p>
                </div>
              </div>
              <Button 
                onClick={handleProcessAll}
                className="bg-orange-500 hover:bg-orange-600 text-white"
                disabled={automationStatus.queued_count === 0}
              >
                Process All
              </Button>
            </div>
            
            {/* Orders in Queue */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {automationStatus.orders?.slice(0, 10).map((order) => (
                <div 
                  key={order.id} 
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    order.status === 'processing' 
                      ? 'bg-blue-50 border-blue-200' 
                      : order.automation_state?.includes('error') || order.automation_state?.includes('failed')
                        ? 'bg-red-50 border-red-200'
                        : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-gray-900">
                        {order.id.slice(0, 8).toUpperCase()}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        order.status === 'processing' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'bg-orange-100 text-orange-700'
                      }`}>
                        {order.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {order.package_name} → UID: <span className="font-mono">{order.player_uid}</span>
                    </div>
                    {order.automation_state && (
                      <div className={`text-xs mt-1 ${
                        order.automation_state.includes('error') || order.automation_state.includes('failed')
                          ? 'text-red-600 font-medium'
                          : 'text-gray-500'
                      }`}>
                        State: {order.automation_state}
                      </div>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleProcessOrder(order.id)}
                    disabled={processingOrder === order.id || order.status === 'processing'}
                    className="ml-2"
                  >
                    {processingOrder === order.id ? 'Starting...' : order.status === 'processing' ? 'Running' : 'Process'}
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

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

          <Link
            to="/admin/audit-logs"
            data-testid="quick-action-audit-logs"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-orange-500 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <ClipboardList className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">Audit Logs</p>
                <p className="text-xs text-gray-600">Admin actions history</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">View all admin actions and wallet changes</p>
          </Link>
        </div>

        {/* Order Management Actions */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
            to="/admin/sms-inbox"
            data-testid="quick-action-sms"
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-green-500 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <MessageSquare className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-gray-900 font-bold">SMS Inbox</p>
                <p className="text-xs text-gray-600">Payment verification</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">Input & verify payment SMS</p>
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
