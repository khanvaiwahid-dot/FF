import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Package, LayoutDashboard, AlertTriangle, Inbox, ArrowLeft, Search } from 'lucide-react';
import { Input } from '@/components/ui/input';

const AdminOrders = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchOrders();
  }, []);

  useEffect(() => {
    filterOrders();
  }, [filterStatus, searchTerm, orders]);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/admin/orders`);
      setOrders(response.data);
      setFilteredOrders(response.data);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const filterOrders = () => {
    let filtered = orders;

    if (filterStatus !== 'all') {
      filtered = filtered.filter(order => order.status === filterStatus);
    }

    if (searchTerm) {
      filtered = filtered.filter(order => 
        order.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.player_uid.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredOrders(filtered);
  };

  const handleRetry = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/retry`);
      toast.success('Order added to queue for retry');
      fetchOrders();
    } catch (error) {
      toast.error('Failed to retry order');
    }
  };

  const handleCompleteManual = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/complete-manual`);
      toast.success('Order marked as success');
      fetchOrders();
    } catch (error) {
      toast.error('Failed to complete order');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending_payment: 'text-warning bg-warning/10',
      paid: 'text-success bg-success/10',
      queued: 'text-info bg-info/10',
      processing: 'text-info bg-info/10',
      wallet_partial_paid: 'text-warning bg-warning/10',
      wallet_fully_paid: 'text-success bg-success/10',
      success: 'text-success bg-success/10',
      failed: 'text-error bg-error/10',
      manual_review: 'text-warning bg-warning/10',
      suspicious: 'text-error bg-error/10',
      duplicate_payment: 'text-error bg-error/10',
      expired: 'text-gray-400 bg-gray-400/10'
    };
    return colors[status] || 'text-gray-400 bg-gray-400/10';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-primary">Loading orders...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20">
      {/* Header */}
      <div className="bg-card/80 backdrop-blur-sm border-b border-white/5 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/dashboard')}
            data-testid="back-button"
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-white" data-testid="admin-orders-title">All Orders</h1>
            <p className="text-xs text-gray-400">{filteredOrders.length} orders</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Filters */}
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 space-y-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input
                  data-testid="search-orders-input"
                  type="text"
                  placeholder="Search by order ID, username, or UID"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                />
              </div>
            </div>
            <div className="flex gap-2 overflow-x-auto">
              {['all', 'success', 'pending_payment', 'processing', 'failed', 'manual_review'].map(status => (
                <button
                  key={status}
                  data-testid={`filter-${status}`}
                  onClick={() => setFilterStatus(status)}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                    filterStatus === status
                      ? 'bg-primary text-black'
                      : 'bg-white/5 text-gray-400 hover:text-white'
                  }`}
                >
                  {status.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Orders List */}
        <div className="space-y-3">
          {filteredOrders.length === 0 ? (
            <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-8 text-center">
              <Package className="w-12 h-12 mx-auto mb-2 text-gray-400 opacity-50" />
              <p className="text-gray-400">No orders found</p>
            </div>
          ) : (
            filteredOrders.map((order) => (
              <div
                key={order.id}
                data-testid={`order-${order.id}`}
                className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 hover:border-white/10 transition-colors"
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <p className="text-white font-bold font-mono">#{order.id.slice(0, 8)}</p>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="space-y-1 text-sm">
                      <p className="text-gray-400">
                        <span className="text-white">@{order.username}</span> • {order.package_name}
                      </p>
                      <p className="text-gray-400">UID: {order.player_uid}</p>
                      <p className="text-gray-400">{formatDate(order.created_at)}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-2xl font-bold text-primary">₹{order.amount}</p>
                    {order.wallet_used > 0 && (
                      <p className="text-xs text-success">Wallet: -₹{order.wallet_used}</p>
                    )}
                  </div>

                  {(order.status === 'failed' || order.status === 'manual_review') && (
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleRetry(order.id)}
                        data-testid={`retry-${order.id}`}
                        size="sm"
                        className="bg-info/20 text-info hover:bg-info/30"
                      >
                        Retry
                      </Button>
                      <Button
                        onClick={() => handleCompleteManual(order.id)}
                        data-testid={`complete-${order.id}`}
                        size="sm"
                        className="bg-success/20 text-success hover:bg-success/30"
                      >
                        Complete
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-card/80 backdrop-blur-xl border-t border-white/5 z-20">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => navigate('/admin/dashboard')}
            data-testid="nav-dashboard"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="text-xs">Dashboard</span>
          </button>
          <button
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-secondary"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs font-medium">Orders</span>
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

export default AdminOrders;