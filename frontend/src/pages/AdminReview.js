import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { AlertTriangle, LayoutDashboard, Package, Inbox, ArrowLeft, CheckCircle, RefreshCw, XCircle } from 'lucide-react';

const AdminReview = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReviewOrders();
  }, []);

  const fetchReviewOrders = async () => {
    try {
      const response = await axios.get(`${API}/admin/review-queue`);
      setOrders(response.data.orders || []);
    } catch (error) {
      toast.error('Failed to load review queue');
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

  const handleMarkSuccess = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/mark-success`);
      toast.success('Order marked as success');
      fetchReviewOrders();
    } catch (error) {
      toast.error('Failed to complete order');
    }
  };

  const getStatusConfig = (status) => {
    const configs = {
      failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200' },
      manual_review: { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', border: 'border-orange-200' },
      suspicious: { icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200' },
      duplicate_payment: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200' },
      invalid_uid: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', border: 'border-red-200' }
    };
    return configs[status] || { icon: AlertTriangle, color: 'text-gray-600', bg: 'bg-gray-100', border: 'border-gray-200' };
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
        <div className="text-primary">Loading review queue...</div>
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
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="admin-review-title">Manual Review</h1>
            <p className="text-xs text-gray-600">{orders.length} orders need attention</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {orders.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center shadow-sm">
            <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-400" />
            <p className="text-gray-700 font-semibold">No orders need review</p>
            <p className="text-sm text-gray-500 mt-2">All orders are processing normally</p>
          </div>
        ) : (
          orders.map((order) => {
            const statusConfig = getStatusConfig(order.status);
            const StatusIcon = statusConfig.icon;
            
            return (
              <div
                key={order.id}
                data-testid={`review-order-${order.id}`}
                className={`bg-white border-2 rounded-xl p-5 shadow-sm ${statusConfig.border}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <StatusIcon className={`w-5 h-5 ${statusConfig.color}`} />
                      <p className="text-gray-900 font-bold font-mono">#{order.id.slice(0, 8).toUpperCase()}</p>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                        {order.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">{formatDate(order.created_at)}</p>
                  </div>
                  <p className="text-2xl font-bold text-primary">₹{order.locked_price?.toFixed(2) || '0.00'}</p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4 text-sm">
                  <div>
                    <span className="text-gray-500">Customer</span>
                    <p className="text-gray-900 font-semibold">@{order.username}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Player UID</span>
                    <p className="text-gray-900 font-mono">{order.player_uid || 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Package</span>
                    <p className="text-gray-900 font-semibold">{order.package_name}</p>
                  </div>
                  {order.wallet_used > 0 && (
                    <div>
                      <span className="text-gray-500">Wallet Used</span>
                      <p className="text-green-600 font-semibold">₹{order.wallet_used?.toFixed(2)}</p>
                    </div>
                  )}
                  {order.payment_last3digits && (
                    <div>
                      <span className="text-gray-500">Payment Last 3</span>
                      <p className="text-gray-900 font-semibold">{order.payment_last3digits}</p>
                    </div>
                  )}
                  {order.payment_rrn && (
                    <div>
                      <span className="text-gray-500">RRN</span>
                      <p className="text-gray-900 font-mono text-xs">{order.payment_rrn}</p>
                    </div>
                  )}
                  {order.automation_state && (
                    <div>
                      <span className="text-gray-500">Automation State</span>
                      <p className="text-blue-600 font-semibold">{order.automation_state}</p>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-500">Retry Count</span>
                    <p className="text-gray-900 font-semibold">{order.retry_count || 0}</p>
                  </div>
                </div>

                {order.suspicious_reason && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-700">
                      <strong>Reason:</strong> {order.suspicious_reason}
                    </p>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    onClick={() => handleRetry(order.id)}
                    data-testid={`retry-${order.id}`}
                    className="flex-1 bg-blue-100 text-blue-700 hover:bg-blue-200"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry Automation
                  </Button>
                  <Button
                    onClick={() => handleMarkSuccess(order.id)}
                    data-testid={`complete-${order.id}`}
                    className="flex-1 bg-green-100 text-green-700 hover:bg-green-200"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark as Complete
                  </Button>
                </div>
              </div>
            );
          })
        )}
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
            onClick={() => navigate('/admin/orders')}
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <Package className="w-5 h-5" />
            <span className="text-xs">Orders</span>
          </button>
          <button
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs font-medium">Review</span>
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

export default AdminReview;
