import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '@/App';
import { Inbox, LayoutDashboard, Package, AlertTriangle, ArrowLeft } from 'lucide-react';

const AdminPayments = () => {
  const navigate = useNavigate();
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      const response = await axios.get(`${API}/admin/payments/inbox`);
      setPayments(response.data);
    } catch (error) {
      toast.error('Failed to load payments');
    } finally {
      setLoading(false);
    }
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
        <div className="text-primary">Loading payments...</div>
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
            <h1 className="text-lg font-heading font-bold text-white" data-testid="admin-payments-title">Payment Inbox</h1>
            <p className="text-xs text-gray-400">{payments.length} unmatched payments</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {payments.length === 0 ? (
          <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-8 text-center">
            <Inbox className="w-12 h-12 mx-auto mb-2 text-gray-400 opacity-50" />
            <p className="text-gray-400">No unmatched payments</p>
            <p className="text-sm text-gray-500 mt-2">All payments have been matched to orders</p>
          </div>
        ) : (
          payments.map((payment) => (
            <div
              key={payment.id}
              data-testid={`payment-${payment.id}`}
              className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-6 hover:border-warning/30 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-white font-bold font-mono">SMS #{payment.id.slice(0, 8)}</p>
                  <p className="text-sm text-gray-400 mt-1">{formatDate(payment.parsed_at)}</p>
                </div>
                {payment.amount && (
                  <p className="text-2xl font-bold text-warning">₹{payment.amount}</p>
                )}
              </div>

              <div className="bg-white/5 rounded-xl p-4 mb-4">
                <p className="text-xs text-gray-400 mb-1">Raw Message:</p>
                <p className="text-sm text-white font-mono">{payment.raw_message}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {payment.amount && (
                  <div>
                    <p className="text-xs text-gray-400">Amount</p>
                    <p className="text-white font-semibold">₹{payment.amount}</p>
                  </div>
                )}
                {payment.last3digits && (
                  <div>
                    <p className="text-xs text-gray-400">Last 3 Digits</p>
                    <p className="text-white font-semibold">{payment.last3digits}</p>
                  </div>
                )}
                {payment.rrn && (
                  <div>
                    <p className="text-xs text-gray-400">RRN</p>
                    <p className="text-white font-mono text-sm">{payment.rrn}</p>
                  </div>
                )}
                {payment.method && (
                  <div>
                    <p className="text-xs text-gray-400">Payment Method</p>
                    <p className="text-white font-semibold">{payment.method}</p>
                  </div>
                )}
                {payment.remark && (
                  <div>
                    <p className="text-xs text-gray-400">Remark</p>
                    <p className="text-white font-semibold">{payment.remark}</p>
                  </div>
                )}
              </div>

              <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-xl">
                <p className="text-xs text-warning">
                  ⚠️ This payment couldn't be automatically matched to any order. Please manually verify.
                </p>
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
            onClick={() => navigate('/admin/review')}
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs">Review</span>
          </button>
          <button
            data-testid="nav-payments"
            className="flex flex-col items-center gap-1 text-secondary"
          >
            <Inbox className="w-5 h-5" />
            <span className="text-xs font-medium">Payments</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminPayments;