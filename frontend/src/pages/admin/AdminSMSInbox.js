import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  ArrowLeft, 
  MessageSquare, 
  Send, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Copy,
  Link as LinkIcon
} from 'lucide-react';

const AdminSMSInbox = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [pendingOrders, setPendingOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [smsInput, setSmsInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [selectedSms, setSelectedSms] = useState(null);
  const [selectedOrderForMatch, setSelectedOrderForMatch] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [smsResponse, ordersResponse] = await Promise.all([
        axios.get(`${API}/admin/sms`),
        axios.get(`${API}/admin/orders`)
      ]);
      setMessages(smsResponse.data);
      // Filter only pending orders
      setPendingOrders(ordersResponse.data.filter(o => 
        ['pending_payment', 'wallet_partial_paid', 'manual_review'].includes(o.status)
      ));
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitSMS = async () => {
    if (!smsInput.trim()) {
      toast.error('Please paste the SMS message');
      return;
    }

    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/admin/sms/input`, {
        raw_message: smsInput
      });
      
      if (response.data.matched) {
        toast.success(response.data.message);
        if (response.data.overpayment_credited > 0) {
          toast.info(`₹${response.data.overpayment_credited.toFixed(2)} credited to user wallet as overpayment`);
        }
      } else if (response.data.duplicate_rrn) {
        toast.error(response.data.message);
      } else {
        toast.info(response.data.message);
      }
      
      setSmsInput('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to process SMS');
    } finally {
      setSubmitting(false);
    }
  };

  const handleManualMatch = async () => {
    if (!selectedSms || !selectedOrderForMatch) {
      toast.error('Please select both SMS and order');
      return;
    }

    try {
      const response = await axios.post(`${API}/admin/sms/match/${selectedSms.id}?order_id=${selectedOrderForMatch}`);
      toast.success(response.data.message);
      if (response.data.overpayment_credited > 0) {
        toast.info(`₹${response.data.overpayment_credited.toFixed(2)} credited to user wallet as overpayment`);
      }
      setSelectedSms(null);
      setSelectedOrderForMatch('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to match SMS');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-primary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/admin/dashboard')}
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            <h1 className="text-lg font-heading font-bold text-gray-900">SMS Payment Inbox</h1>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Input SMS Section */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Paste Payment SMS</h2>
          <p className="text-sm text-gray-600 mb-4">
            Copy and paste the payment confirmation SMS here. The system will automatically parse the amount, phone digits, and transaction reference.
          </p>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-gray-700">SMS Message *</Label>
              <Textarea
                value={smsInput}
                onChange={(e) => setSmsInput(e.target.value)}
                placeholder="Paste payment SMS here...&#10;&#10;Example: Rs 100.00 received from XXX****910 for RRN 123456789, DiamondStore /FonePay"
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl min-h-[120px] text-gray-900"
                data-testid="sms-input"
              />
            </div>
            
            <Button
              onClick={handleSubmitSMS}
              disabled={submitting || !smsInput.trim()}
              className="bg-primary hover:bg-primary-hover text-white font-bold rounded-full"
              data-testid="submit-sms-btn"
            >
              <Send className="w-4 h-4 mr-2" />
              {submitting ? 'Processing...' : 'Process SMS'}
            </Button>
          </div>
        </div>

        {/* Pending Orders for Manual Match */}
        {pendingOrders.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6">
            <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">
              Pending Orders ({pendingOrders.length})
            </h2>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {pendingOrders.map((order) => (
                <div
                  key={order.id}
                  className="bg-white border border-orange-200 rounded-lg p-3 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-gray-900">#{order.id.slice(0, 8).toUpperCase()}</span>
                      <button onClick={() => copyToClipboard(order.id)} className="text-gray-400 hover:text-primary">
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                    <p className="text-sm text-gray-600">
                      {order.package_name} • ₹{order.payment_amount} • 
                      Last 3: {order.payment_last3digits || 'N/A'}
                    </p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-yellow-100 text-yellow-800">
                    {order.status.replace('_', ' ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SMS Messages List */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <h2 className="text-lg font-heading font-bold text-gray-900 mb-4">Recent SMS Messages</h2>
          
          {messages.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No SMS messages yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((sms) => (
                <div
                  key={sms.id}
                  className={`border rounded-xl p-4 ${
                    sms.used 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {sms.used ? (
                        <CheckCircle className="w-5 h-5 text-green-600" />
                      ) : (
                        <Clock className="w-5 h-5 text-yellow-600" />
                      )}
                      <span className="text-sm font-semibold text-gray-900">
                        {sms.used ? 'Matched' : 'Unmatched'}
                      </span>
                      {sms.matched_order_id && (
                        <span className="text-xs text-gray-500">
                          → #{sms.matched_order_id.slice(0, 8).toUpperCase()}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">{formatDate(sms.parsed_at)}</span>
                  </div>
                  
                  <div className="bg-white rounded-lg p-3 mb-3 border border-gray-200">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{sms.raw_message}</p>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                    <div className="bg-gray-100 rounded-lg p-2">
                      <span className="text-gray-500">Amount:</span>
                      <span className="ml-1 text-gray-900 font-semibold">₹{sms.amount || 'N/A'}</span>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-2">
                      <span className="text-gray-500">Last 3:</span>
                      <span className="ml-1 text-gray-900 font-semibold">{sms.last3digits || 'N/A'}</span>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-2">
                      <span className="text-gray-500">RRN:</span>
                      <span className="ml-1 text-gray-900 font-semibold">{sms.rrn || 'N/A'}</span>
                    </div>
                    <div className="bg-gray-100 rounded-lg p-2">
                      <span className="text-gray-500">Method:</span>
                      <span className="ml-1 text-gray-900 font-semibold">{sms.method || 'N/A'}</span>
                    </div>
                  </div>
                  
                  {!sms.used && pendingOrders.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="flex items-center gap-2">
                        <select
                          className="flex-1 border border-gray-300 rounded-lg p-2 text-sm text-gray-900"
                          value={selectedSms?.id === sms.id ? selectedOrderForMatch : ''}
                          onChange={(e) => {
                            setSelectedSms(sms);
                            setSelectedOrderForMatch(e.target.value);
                          }}
                          data-testid={`match-select-${sms.id}`}
                        >
                          <option value="">Select order to match...</option>
                          {pendingOrders.map((order) => (
                            <option key={order.id} value={order.id}>
                              #{order.id.slice(0, 8).toUpperCase()} - {order.package_name} - ₹{order.payment_amount} - Last3: {order.payment_last3digits || 'N/A'}
                            </option>
                          ))}
                        </select>
                        <Button
                          onClick={handleManualMatch}
                          disabled={selectedSms?.id !== sms.id || !selectedOrderForMatch}
                          size="sm"
                          className="bg-primary hover:bg-primary-hover text-white"
                          data-testid={`match-btn-${sms.id}`}
                        >
                          <LinkIcon className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminSMSInbox;
