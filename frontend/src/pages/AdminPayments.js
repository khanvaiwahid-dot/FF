import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { API } from '@/App';
import { Button } from '@/components/ui/button';
import { Inbox, LayoutDashboard, Package, AlertTriangle, ArrowLeft, CheckCircle, MessageSquare } from 'lucide-react';

const AdminPayments = () => {
  const navigate = useNavigate();
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      const response = await axios.get(`${API}/admin/sms`);
      // Filter to only show unmatched payments
      const unmatched = response.data.filter(p => !p.used);
      setPayments(unmatched);
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading payments...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/admin/dashboard')}
              data-testid="back-button"
              className="text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-lg font-heading font-bold text-gray-900" data-testid="admin-payments-title">Payment Inbox</h1>
              <p className="text-xs text-gray-600">{payments.length} unmatched payments</p>
            </div>
          </div>
          <Button
            onClick={() => navigate('/admin/sms-inbox')}
            data-testid="input-sms-btn"
            className="bg-primary hover:bg-primary-hover text-white"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Input SMS
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {payments.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center shadow-sm">
            <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-400" />
            <p className="text-gray-700 font-semibold">No unmatched payments</p>
            <p className="text-sm text-gray-500 mt-2">All payments have been matched to orders</p>
          </div>
        ) : (
          payments.map((payment) => (
            <div
              key={payment.id}
              data-testid={`payment-${payment.id}`}
              className="bg-white border border-gray-200 rounded-xl p-5 hover:border-orange-300 hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-gray-900 font-bold font-mono">SMS #{payment.id.slice(0, 8).toUpperCase()}</p>
                  <p className="text-sm text-gray-500 mt-1">{formatDate(payment.parsed_at)}</p>
                </div>
                {payment.amount && (
                  <p className="text-2xl font-bold text-orange-600">₹{payment.amount?.toFixed(2)}</p>
                )}
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-4">
                <p className="text-xs text-gray-500 mb-1">Raw Message:</p>
                <p className="text-sm text-gray-700 font-mono break-all">{payment.raw_message}</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {payment.amount && (
                  <div>
                    <p className="text-gray-500">Amount</p>
                    <p className="text-gray-900 font-semibold">₹{payment.amount?.toFixed(2)}</p>
                  </div>
                )}
                {payment.last3digits && (
                  <div>
                    <p className="text-gray-500">Last 3 Digits</p>
                    <p className="text-gray-900 font-semibold">{payment.last3digits}</p>
                  </div>
                )}
                {payment.rrn && (
                  <div>
                    <p className="text-gray-500">RRN</p>
                    <p className="text-gray-900 font-mono text-xs">{payment.rrn}</p>
                  </div>
                )}
                {payment.method && (
                  <div>
                    <p className="text-gray-500">Payment Method</p>
                    <p className="text-gray-900 font-semibold">{payment.method}</p>
                  </div>
                )}
                {payment.remark && (
                  <div>
                    <p className="text-gray-500">Remark</p>
                    <p className="text-gray-900 font-semibold">{payment.remark}</p>
                  </div>
                )}
              </div>

              <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <p className="text-sm text-orange-700">
                  ⚠️ This payment couldn't be automatically matched to any order. Go to SMS Inbox to manually match.
                </p>
              </div>
            </div>
          ))
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
            onClick={() => navigate('/admin/review')}
            data-testid="nav-review"
            className="flex flex-col items-center gap-1 text-gray-500 hover:text-primary transition-colors"
          >
            <AlertTriangle className="w-5 h-5" />
            <span className="text-xs">Review</span>
          </button>
          <button
            data-testid="nav-payments"
            className="flex flex-col items-center gap-1 text-primary"
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
