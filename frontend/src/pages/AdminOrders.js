import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Package, LayoutDashboard, AlertTriangle, Inbox, ArrowLeft, Search, CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';
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
        order.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.player_uid?.toLowerCase().includes(searchTerm.toLowerCase())
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

  const handleMarkSuccess = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/mark-success`);
      toast.success('Order marked as success');
      fetchOrders();
    } catch (error) {
      toast.error('Failed to complete order');
    }
  };

  const getStatusConfig = (status) => {
    const configs = {
      success: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Success' },
      pending_payment: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Pending Payment' },
      paid: { icon: CheckCircle, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Paid' },
      queued: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Queued' },
      processing: { icon: RefreshCw, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Processing' },
      failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Failed' },
      manual_review: { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Manual Review' },
      suspicious: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100', label: 'Suspicious' },
      duplicate_payment: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Duplicate' },
      expired: { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', label: 'Expired' },
      invalid_uid: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Invalid UID' },
      refunded: { icon: CheckCircle, color: 'text-gray-600', bg: 'bg-gray-100', label: 'Refunded' },
      // Legacy statuses for backward compatibility
      wallet_partial_paid: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Partial Paid' },
      wallet_fully_paid: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Fully Paid' }
    };
    return configs[status] || { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', label: status?.replace('_', ' ') || 'Unknown' };
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading orders...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/dashboard')}
            data-testid="back-button"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="admin-orders-title">All Orders</h1>
            <p className="text-xs text-gray-600">{filteredOrders.length} orders</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Filters */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4 shadow-sm">
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
                  className="pl-10 border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
                />
              </div>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {['all', 'success', 'pending_payment', 'processing', 'failed', 'manual_review'].map(status => (
                <button
                  key={status}
                  data-testid={`filter-${status}`}
                  onClick={() => setFilterStatus(status)}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                    filterStatus === status
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-orange-50 hover:text-primary'
                  }`}
                >
                  {status === 'all' ? 'All' : status.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Orders List */}
        <div className="space-y-3">
          {filteredOrders.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center shadow-sm">
              <Package className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p className="text-gray-500">No orders found</p>
            </div>
          ) : (
            filteredOrders.map((order) => {
              const statusConfig = getStatusConfig(order.status);
              const StatusIcon = statusConfig.icon;
              
              return (
                <div
                  key={order.id}
                  data-testid={`order-${order.id}`}
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:border-primary/50 hover:shadow-md transition-all"
                >
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <p className="text-gray-900 font-bold font-mono">#{order.id.slice(0, 8).toUpperCase()}</p>
                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {statusConfig.label}
                        </span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <p className="text-gray-600">
                          <span className="text-gray-900 font-semibold">@{order.username}</span> • {order.package_name}
                        </p>
                        <p className="text-gray-500">UID: {order.player_uid || 'N/A'}</p>
                        <p className="text-gray-500">{formatDate(order.created_at)}</p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-2xl font-bold text-primary">₹{order.locked_price?.toFixed(2) || '0.00'}</p>
                      {order.wallet_used > 0 && (
                        <p className="text-xs text-green-600">Wallet: -₹{order.wallet_used?.toFixed(2)}</p>
                      )}
                    </div>

                    {(order.status === 'failed' || order.status === 'manual_review' || order.status === 'invalid_uid') && (
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleRetry(order.id)}
                          data-testid={`retry-${order.id}`}
                          size="sm"
                          className="bg-blue-100 text-blue-700 hover:bg-blue-200"
                        >
                          <RefreshCw className="w-4 h-4 mr-1" />
                          Retry
                        </Button>
                        <Button
                          onClick={() => handleMarkSuccess(order.id)}
                          data-testid={`complete-${order.id}`}
                          size="sm"
                          className="bg-green-100 text-green-700 hover:bg-green-200"
                        >
                          <CheckCircle className="w-4 h-4 mr-1" />
                          Mark Success
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-20 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => navigate('/admin/dashboard')}
            data-testid="nav-dashboard"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <LayoutDashboard className="w-5 h-5" />
            <span className="text-xs">Dashboard</span>
          </button>
          <button
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs font-medium">Orders</span>
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

export default AdminOrders;
