import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { 
  Gem, 
  Wallet as WalletIcon, 
  ArrowLeft, 
  History,
  Copy,
  CheckCircle,
  Clock,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Package
} from 'lucide-react';

const UserOrders = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/user/orders`);
      setOrders(response.data);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success('Order ID copied!');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getStatusConfig = (status) => {
    const configs = {
      success: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Completed' },
      pending_payment: { icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Pending Payment' },
      wallet_fully_paid: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Paid - Processing' },
      wallet_partial_paid: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Partial Paid' },
      queued: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Queued' },
      processing: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Processing' },
      failed: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-100', label: 'Failed' },
      suspicious: { icon: AlertTriangle, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Under Review' },
      refunded: { icon: CheckCircle, color: 'text-gray-600', bg: 'bg-gray-100', label: 'Refunded' }
    };
    return configs[status] || { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', label: status };
  };

  const getStatusTimeline = (order) => {
    const steps = [
      { key: 'created', label: 'Order Created', completed: true, time: order.created_at },
      { key: 'payment', label: 'Payment', completed: ['queued', 'processing', 'success', 'failed'].includes(order.status), time: order.payment_confirmed_at },
      { key: 'processing', label: 'Processing', completed: ['processing', 'success', 'failed'].includes(order.status), time: order.processing_started_at },
      { key: 'completed', label: 'Completed', completed: order.status === 'success', time: order.completed_at }
    ];
    return steps;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading orders...</div>
      </div>
    );
  }

  // Order Detail View
  if (selectedOrder) {
    const statusConfig = getStatusConfig(selectedOrder.status);
    const StatusIcon = statusConfig.icon;
    const timeline = getStatusTimeline(selectedOrder);

    return (
      <div className="min-h-screen bg-gray-50 pb-20">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
          <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
            <button
              onClick={() => setSelectedOrder(null)}
              data-testid="back-to-orders"
              className="text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-heading font-bold text-gray-900">Order Details</h1>
              <p className="text-xs text-gray-600">#{selectedOrder.id.slice(0, 8).toUpperCase()}</p>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
          {/* Status Card */}
          <div className={`${statusConfig.bg} border border-gray-200 rounded-2xl p-6`}>
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 ${statusConfig.bg} rounded-full flex items-center justify-center`}>
                <StatusIcon className={`w-7 h-7 ${statusConfig.color}`} />
              </div>
              <div>
                <p className={`text-2xl font-heading font-bold ${statusConfig.color}`}>{statusConfig.label}</p>
                <p className="text-gray-600 text-sm">{formatDate(selectedOrder.created_at)}</p>
              </div>
            </div>
          </div>

          {/* Order Info */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm space-y-4">
            <h2 className="text-lg font-heading font-bold text-gray-900">Order Information</h2>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Order ID</span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-900 font-mono text-sm">{selectedOrder.id.slice(0, 8).toUpperCase()}</span>
                  <button 
                    onClick={() => copyToClipboard(selectedOrder.id, selectedOrder.id)}
                    className="text-primary hover:text-primary-hover"
                    data-testid="copy-order-id-detail"
                  >
                    {copiedId === selectedOrder.id ? <CheckCircle className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Product</span>
                <span className="text-gray-900 font-semibold">{selectedOrder.package_name || 'Diamond Package'}</span>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Amount</span>
                <div className="flex items-center gap-1">
                  <Gem className="w-4 h-4 text-primary" />
                  <span className="text-gray-900 font-semibold">{selectedOrder.diamonds || selectedOrder.amount} {selectedOrder.type === 'diamond' ? 'Diamonds' : 'Days'}</span>
                </div>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Player UID</span>
                <span className="text-gray-900 font-mono">{selectedOrder.player_uid}</span>
              </div>
              
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
                <span className="text-gray-600">Server</span>
                <span className="text-gray-900">🇧🇩 Bangladesh</span>
              </div>
              
              <div className="flex justify-between items-center py-2">
                <span className="text-gray-600">Total Paid</span>
                <span className="text-xl font-bold text-primary">₹{selectedOrder.price_at_purchase?.toFixed(2) || selectedOrder.price?.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Status Timeline */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Order Timeline</h2>
            
            <div className="space-y-4">
              {timeline.map((step, index) => (
                <div key={step.key} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      step.completed ? 'bg-green-100' : 'bg-gray-100'
                    }`}>
                      {step.completed ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <div className="w-3 h-3 rounded-full bg-gray-300" />
                      )}
                    </div>
                    {index < timeline.length - 1 && (
                      <div className={`w-0.5 h-8 ${step.completed ? 'bg-green-300' : 'bg-gray-200'}`} />
                    )}
                  </div>
                  <div className="pt-1">
                    <p className={`font-semibold ${step.completed ? 'text-gray-900' : 'text-gray-400'}`}>{step.label}</p>
                    {step.time && step.completed && (
                      <p className="text-xs text-gray-500">{formatDate(step.time)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          {selectedOrder.status === 'pending_payment' && (
            <Button
              onClick={() => navigate(`/payment/${selectedOrder.id}`)}
              className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full"
              data-testid="continue-payment-btn"
            >
              Continue to Payment
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Orders List View
  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            data-testid="back-button"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="orders-title">My Orders</h1>
            <p className="text-xs text-gray-600">@{user?.username}</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {orders.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center">
            <Package className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 text-lg font-semibold mb-2">No orders yet</p>
            <p className="text-gray-400 text-sm mb-4">Start by purchasing some diamonds!</p>
            <Button
              onClick={() => navigate('/')}
              className="bg-primary hover:bg-primary-hover text-white font-bold rounded-full"
              data-testid="start-shopping-btn"
            >
              <Gem className="w-4 h-4 mr-2" />
              Buy Diamonds
            </Button>
          </div>
        ) : (
          orders.map((order) => {
            const statusConfig = getStatusConfig(order.status);
            const StatusIcon = statusConfig.icon;
            
            return (
              <div
                key={order.id}
                onClick={() => setSelectedOrder(order)}
                data-testid={`order-card-${order.id}`}
                className="bg-white border border-gray-200 rounded-xl p-4 hover:border-primary/50 hover:shadow-md transition-all cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 ${statusConfig.bg} rounded-full flex items-center justify-center`}>
                      <StatusIcon className={`w-6 h-6 ${statusConfig.color}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-gray-900 font-bold">{order.package_name || `${order.diamonds || order.amount} ${order.type === 'diamond' ? 'Diamonds' : 'Days'}`}</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="font-mono">#{order.id.slice(0, 8).toUpperCase()}</span>
                        <button 
                          onClick={(e) => { e.stopPropagation(); copyToClipboard(order.id, order.id); }}
                          className="text-primary hover:text-primary-hover"
                          data-testid={`copy-order-${order.id}`}
                        >
                          {copiedId === order.id ? <CheckCircle className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-2">
                    <div>
                      <p className="text-lg font-bold text-gray-900">₹{order.price_at_purchase?.toFixed(2) || order.price?.toFixed(2)}</p>
                      <p className="text-xs text-gray-500">{formatDate(order.created_at)}</p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
                
                {/* Status Badge */}
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${statusConfig.bg} ${statusConfig.color}`}>
                    <StatusIcon className="w-3 h-3" />
                    {statusConfig.label}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-20 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-around">
          <button
            onClick={() => navigate('/')}
            data-testid="nav-topup"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <Gem className="w-5 h-5" />
            <span className="text-xs">Top-Up</span>
          </button>
          <button
            data-testid="nav-orders"
            className="flex flex-col items-center gap-1 text-primary"
          >
            <History className="w-5 h-5" />
            <span className="text-xs font-medium">Orders</span>
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

export default UserOrders;
