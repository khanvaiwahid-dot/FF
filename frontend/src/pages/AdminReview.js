import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { AlertTriangle, LayoutDashboard, Package, Inbox, ArrowLeft } from 'lucide-react';

const AdminReview = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReviewOrders();
  }, []);

  const fetchReviewOrders = async () => {
    try {
      const response = await axios.get(`${API}/admin/orders`);
      const reviewOrders = response.data.filter(order => 
        ['failed', 'manual_review', 'suspicious', 'duplicate_payment'].includes(order.status)
      );
      setOrders(reviewOrders);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/retry`);
      toast.success('Order added to queue for retry');
      fetchReviewOrders();
    } catch (error) {
      toast.error('Failed to retry order');
    }
  };

  const handleCompleteManual = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/complete-manual`);
      toast.success('Order marked as success');
      fetchReviewOrders();
    } catch (error) {
      toast.error('Failed to complete order');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      failed: 'text-error bg-error/10 border-error/20',
      manual_review: 'text-warning bg-warning/10 border-warning/20',
      suspicious: 'text-error bg-error/10 border-error/20',
      duplicate_payment: 'text-error bg-error/10 border-error/20'
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
        <div className="text-primary">Loading review queue...</div>
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
            <h1 className="text-lg font-heading font-bold text-white" data-testid="admin-review-title">Manual Review</h1>
            <p className="text-xs text-gray-400">{orders.length} orders need attention</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {orders.length === 0 ? (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-8 text-center">
            <AlertTriangle className="w-12 h-12 mx-auto mb-2 text-gray-400 opacity-50" />
            <p className="text-gray-400">No orders need review</p>
            <p className="text-sm text-gray-500 mt-2">All orders are processing normally</p>
          </div>
        ) : (
          orders.map((order) => (
            <div
              key={order.id}
              data-testid={`review-order-${order.id}`}
              className={`bg-card/60 backdrop-blur-xl border-2 rounded-2xl p-6 ${getStatusColor(order.status)}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-warning" />
                    <p className="text-white font-bold font-mono">#{order.id.slice(0, 8)}</p>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-400">{formatDate(order.created_at)}</p>
                </div>
                <p className="text-2xl font-bold text-primary">₹{order.amount}</p>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Customer</span>
                  <span className="text-white">@{order.username}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Player UID</span>
                  <span className="text-white font-mono">{order.player_uid}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Package</span>
                  <span className="text-white">{order.package_name}</span>
                </div>
                {order.wallet_used > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Wallet Used</span>
                    <span className="text-success">₹{order.wallet_used}</span>
                  </div>
                )}
                {order.payment_last3digits && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Payment Last 3</span>
                    <span className="text-white">{order.payment_last3digits}</span>
                  </div>
                )}
                {order.payment_method && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Payment Method</span>
                    <span className="text-white">{order.payment_method}</span>
                  </div>
                )}
                {order.payment_rrn && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">RRN</span>
                    <span className="text-white font-mono">{order.payment_rrn}</span>
                  </div>
                )}
                {order.automation_state && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Automation State</span>
                    <span className="text-info">{order.automation_state}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Retry Count</span>
                  <span className="text-white">{order.retry_count}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={() => handleRetry(order.id)}
                  data-testid={`retry-${order.id}`}
                  className="flex-1 bg-info/20 text-info hover:bg-info/30"
                >
                  Retry Automation
                </Button>
                <Button
                  onClick={() => handleCompleteManual(order.id)}
                  data-testid={`complete-${order.id}`}
                  className="flex-1 bg-success/20 text-success hover:bg-success/30"
                >
                  Mark as Complete
                </Button>
              </div>
            </div>
          ))
        )}
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
            onClick={() => navigate('/admin/orders')}
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs">Orders</span>
          </button>
          <button
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-secondary"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs font-medium">Review</span>
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

export default AdminReview;