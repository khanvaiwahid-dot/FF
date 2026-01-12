import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Package, LayoutDashboard, AlertTriangle, Inbox, ArrowLeft, Search, 
  CheckCircle, XCircle, Clock, RefreshCw, Edit, Eye, X, Save,
  Wallet, Gem, Copy
} from 'lucide-react';

const AdminOrders = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchOrders();
  }, []);

  useEffect(() => {
    filterOrders();
  }, [filterStatus, filterType, searchTerm, orders]);

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

    if (filterType !== 'all') {
      filtered = filtered.filter(order => order.order_type === filterType);
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
      setSelectedOrder(null);
    } catch (error) {
      toast.error('Failed to retry order');
    }
  };

  const handleMarkSuccess = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/mark-success`);
      toast.success('Order marked as success');
      fetchOrders();
      setSelectedOrder(null);
    } catch (error) {
      toast.error('Failed to complete order');
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedOrder) return;
    setSaving(true);
    
    try {
      const updatePayload = {};
      if (editData.player_uid !== selectedOrder.player_uid) {
        updatePayload.player_uid = editData.player_uid;
      }
      if (editData.status !== selectedOrder.status) {
        updatePayload.status = editData.status;
      }
      if (editData.notes !== selectedOrder.notes) {
        updatePayload.notes = editData.notes;
      }

      if (Object.keys(updatePayload).length > 0) {
        await axios.put(`${API}/admin/orders/${selectedOrder.id}`, updatePayload);
        toast.success('Order updated successfully');
        fetchOrders();
        // Refresh the selected order
        const response = await axios.get(`${API}/admin/orders/${selectedOrder.id}`);
        setSelectedOrder(response.data);
      }
      setEditMode(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update order');
    } finally {
      setSaving(false);
    }
  };

  const openOrderDetail = async (order) => {
    try {
      const response = await axios.get(`${API}/admin/orders/${order.id}`);
      setSelectedOrder(response.data);
      setEditData({
        player_uid: response.data.player_uid || '',
        status: response.data.status,
        notes: response.data.notes || ''
      });
      setEditMode(false);
    } catch (error) {
      toast.error('Failed to load order details');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
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
      wallet_partial_paid: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-100', label: 'Partial Paid' },
      wallet_fully_paid: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', label: 'Fully Paid' }
    };
    return configs[status] || { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-100', label: status?.replace(/_/g, ' ') || 'Unknown' };
  };

  const getOrderTypeConfig = (type) => {
    if (type === 'wallet_load') {
      return { icon: Wallet, color: 'text-purple-600', bg: 'bg-purple-100', label: 'Wallet Load' };
    }
    return { icon: Gem, color: 'text-orange-600', bg: 'bg-orange-100', label: 'Product Top-up' };
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const ORDER_STATUSES = [
    'pending_payment', 'paid', 'queued', 'processing', 'success', 'failed',
    'manual_review', 'suspicious', 'duplicate_payment', 'expired', 'invalid_uid', 'refunded'
  ];

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
            <p className="text-xs text-gray-600">{filteredOrders.length} of {orders.length} orders</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Filters */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4 shadow-sm">
          {/* Search */}
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

          {/* Order Type Filter */}
          <div>
            <p className="text-sm text-gray-600 mb-2">Order Type:</p>
            <div className="flex gap-2">
              {[
                { value: 'all', label: 'All Types' },
                { value: 'product_topup', label: 'Product Top-up' },
                { value: 'wallet_load', label: 'Wallet Load' }
              ].map(type => (
                <button
                  key={type.value}
                  data-testid={`filter-type-${type.value}`}
                  onClick={() => setFilterType(type.value)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    filterType === type.value
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-orange-50 hover:text-primary'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <p className="text-sm text-gray-600 mb-2">Status:</p>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {['all', 'success', 'pending_payment', 'paid', 'queued', 'processing', 'failed', 'manual_review'].map(status => (
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
                  {status === 'all' ? 'All Status' : status.replace(/_/g, ' ')}
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
              const typeConfig = getOrderTypeConfig(order.order_type);
              const TypeIcon = typeConfig.icon;
              
              return (
                <div
                  key={order.id}
                  data-testid={`order-${order.id}`}
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:border-primary/50 hover:shadow-md transition-all"
                >
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <p className="text-gray-900 font-bold font-mono">#{order.id.slice(0, 8).toUpperCase()}</p>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${typeConfig.bg} ${typeConfig.color}`}>
                          <TypeIcon className="w-3 h-3" />
                          {typeConfig.label}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {statusConfig.label}
                        </span>
                      </div>
                      <div className="space-y-1 text-sm">
                        <p className="text-gray-600">
                          <span className="text-gray-900 font-semibold">@{order.username}</span> • {order.package_name}
                        </p>
                        {order.player_uid && (
                          <p className="text-gray-500">UID: {order.player_uid}</p>
                        )}
                        <p className="text-gray-500">{formatDate(order.created_at)}</p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-2xl font-bold text-primary">₹{order.locked_price?.toFixed(2) || '0.00'}</p>
                      {order.wallet_used > 0 && (
                        <p className="text-xs text-green-600">Wallet: -₹{order.wallet_used?.toFixed(2)}</p>
                      )}
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={() => openOrderDetail(order)}
                        data-testid={`view-${order.id}`}
                        size="sm"
                        className="bg-gray-100 text-gray-700 hover:bg-gray-200"
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                      <Button
                        onClick={() => { openOrderDetail(order); setEditMode(true); }}
                        data-testid={`edit-${order.id}`}
                        size="sm"
                        className="bg-blue-100 text-blue-700 hover:bg-blue-200"
                      >
                        <Edit className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-xl">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-heading font-bold text-gray-900">
                  Order #{selectedOrder.id.slice(0, 8).toUpperCase()}
                </h2>
                <p className="text-sm text-gray-500">{formatDate(selectedOrder.created_at)}</p>
              </div>
              <div className="flex items-center gap-2">
                {editMode ? (
                  <>
                    <Button
                      onClick={() => setEditMode(false)}
                      size="sm"
                      variant="ghost"
                      disabled={saving}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveEdit}
                      size="sm"
                      className="bg-primary hover:bg-primary-hover text-white"
                      disabled={saving}
                    >
                      <Save className="w-4 h-4 mr-1" />
                      {saving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => setEditMode(true)}
                    size="sm"
                    className="bg-blue-100 text-blue-700 hover:bg-blue-200"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Edit
                  </Button>
                )}
                <button
                  onClick={() => { setSelectedOrder(null); setEditMode(false); }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-4 space-y-6">
              {/* Order ID with Copy */}
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Full Order ID:</span>
                <code className="bg-gray-100 px-2 py-1 rounded text-sm">{selectedOrder.id}</code>
                <button
                  onClick={() => copyToClipboard(selectedOrder.id)}
                  className="text-primary hover:text-primary-hover"
                >
                  <Copy className="w-4 h-4" />
                </button>
              </div>

              {/* Status & Type Badges */}
              <div className="flex gap-2 flex-wrap">
                {(() => {
                  const typeConfig = getOrderTypeConfig(selectedOrder.order_type);
                  const TypeIcon = typeConfig.icon;
                  return (
                    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${typeConfig.bg} ${typeConfig.color}`}>
                      <TypeIcon className="w-4 h-4" />
                      {typeConfig.label}
                    </span>
                  );
                })()}
                {(() => {
                  const statusConfig = getStatusConfig(selectedOrder.status);
                  const StatusIcon = statusConfig.icon;
                  return (
                    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                      <StatusIcon className="w-4 h-4" />
                      {statusConfig.label}
                    </span>
                  );
                })()}
              </div>

              {/* Order Details Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-gray-500">Customer</Label>
                  <p className="text-gray-900 font-semibold">@{selectedOrder.username}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Package</Label>
                  <p className="text-gray-900 font-semibold">{selectedOrder.package_name}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Player UID</Label>
                  {editMode && selectedOrder.order_type === 'product_topup' ? (
                    <Input
                      value={editData.player_uid}
                      onChange={(e) => setEditData({ ...editData, player_uid: e.target.value.replace(/\D/g, '') })}
                      className="mt-1"
                      placeholder="Enter UID (8+ digits)"
                    />
                  ) : (
                    <p className="text-gray-900 font-mono">{selectedOrder.player_uid || 'N/A'}</p>
                  )}
                </div>
                <div>
                  <Label className="text-gray-500">Server</Label>
                  <p className="text-gray-900">🇧🇩 {selectedOrder.server || 'Bangladesh'}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Locked Price</Label>
                  <p className="text-2xl font-bold text-primary">₹{selectedOrder.locked_price?.toFixed(2) || '0.00'}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Wallet Used</Label>
                  <p className="text-gray-900 font-semibold">₹{selectedOrder.wallet_used?.toFixed(2) || '0.00'}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Payment Required</Label>
                  <p className="text-gray-900 font-semibold">₹{selectedOrder.payment_required?.toFixed(2) || '0.00'}</p>
                </div>
                <div>
                  <Label className="text-gray-500">Payment Received</Label>
                  <p className="text-gray-900 font-semibold">₹{selectedOrder.payment_received?.toFixed(2) || '0.00'}</p>
                </div>
                {selectedOrder.overpayment_credited > 0 && (
                  <div>
                    <Label className="text-gray-500">Overpayment Credited</Label>
                    <p className="text-green-600 font-semibold">+₹{selectedOrder.overpayment_credited?.toFixed(2)}</p>
                  </div>
                )}
              </div>

              {/* Payment Details */}
              {(selectedOrder.payment_last3digits || selectedOrder.payment_rrn || selectedOrder.payment_method) && (
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Payment Details</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {selectedOrder.payment_last3digits && (
                      <div>
                        <Label className="text-gray-500">Last 3 Digits</Label>
                        <p className="text-gray-900 font-semibold">{selectedOrder.payment_last3digits}</p>
                      </div>
                    )}
                    {selectedOrder.payment_method && (
                      <div>
                        <Label className="text-gray-500">Payment Method</Label>
                        <p className="text-gray-900 font-semibold">{selectedOrder.payment_method}</p>
                      </div>
                    )}
                    {selectedOrder.payment_rrn && (
                      <div>
                        <Label className="text-gray-500">RRN</Label>
                        <p className="text-gray-900 font-mono text-sm">{selectedOrder.payment_rrn}</p>
                      </div>
                    )}
                    {selectedOrder.payment_remark && (
                      <div>
                        <Label className="text-gray-500">Remark</Label>
                        <p className="text-gray-900">{selectedOrder.payment_remark}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Status Edit */}
              {editMode && (
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-lg font-semibold text-gray-900 mb-3">Update Status</h3>
                  <select
                    value={editData.status}
                    onChange={(e) => setEditData({ ...editData, status: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:border-primary focus:ring-1 focus:ring-primary"
                  >
                    {ORDER_STATUSES.map(s => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Notes */}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-3">Admin Notes</h3>
                {editMode ? (
                  <textarea
                    value={editData.notes}
                    onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:border-primary focus:ring-1 focus:ring-primary"
                    rows={3}
                    placeholder="Add notes about this order..."
                  />
                ) : (
                  <p className="text-gray-700">{selectedOrder.notes || 'No notes'}</p>
                )}
              </div>

              {/* Suspicious Reason */}
              {selectedOrder.suspicious_reason && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="text-sm text-red-700">
                    <strong>Suspicious Reason:</strong> {selectedOrder.suspicious_reason}
                  </p>
                </div>
              )}

              {/* Actions */}
              {!editMode && ['failed', 'manual_review', 'invalid_uid', 'suspicious'].includes(selectedOrder.status) && (
                <div className="border-t border-gray-200 pt-4 flex gap-2">
                  {selectedOrder.order_type === 'product_topup' && (
                    <Button
                      onClick={() => handleRetry(selectedOrder.id)}
                      className="flex-1 bg-blue-100 text-blue-700 hover:bg-blue-200"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Retry Automation
                    </Button>
                  )}
                  <Button
                    onClick={() => handleMarkSuccess(selectedOrder.id)}
                    className="flex-1 bg-green-100 text-green-700 hover:bg-green-200"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Mark as Success
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
