import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  FileText, 
  ArrowLeft, 
  Filter, 
  Calendar,
  User,
  RefreshCw,
  DollarSign,
  PlusCircle,
  MinusCircle,
  CheckCircle,
  AlertTriangle,
  Package,
  MessageSquare,
  Shield,
  Clock
} from 'lucide-react';

const AdminAuditLogs = () => {
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionTypes, setActionTypes] = useState([]);
  const [adminUsers, setAdminUsers] = useState([]);
  
  // Filters
  const [filters, setFilters] = useState({
    adminUsername: '',
    actionType: '',
    startDate: '',
    endDate: ''
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchLogs();
    fetchFilterOptions();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.adminUsername) params.append('admin_username', filters.adminUsername);
      if (filters.actionType) params.append('action_type', filters.actionType);
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);

      const response = await axios.get(`${API}/admin/action-logs?${params.toString()}`);
      setLogs(response.data);
    } catch (error) {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const [typesRes, adminsRes] = await Promise.all([
        axios.get(`${API}/admin/action-logs/action-types`),
        axios.get(`${API}/admin/action-logs/admins`)
      ]);
      setActionTypes(typesRes.data);
      setAdminUsers(adminsRes.data);
    } catch (error) {
      console.error('Failed to load filter options');
    }
  };

  const handleApplyFilters = () => {
    fetchLogs();
    setShowFilters(false);
  };

  const handleClearFilters = () => {
    setFilters({
      adminUsername: '',
      actionType: '',
      startDate: '',
      endDate: ''
    });
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getActionIcon = (actionType) => {
    switch (actionType) {
      case 'wallet_recharge':
        return <PlusCircle className="w-5 h-5 text-green-600" />;
      case 'wallet_redeem':
        return <MinusCircle className="w-5 h-5 text-red-600" />;
      case 'mark_success':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'update_order':
        return <Package className="w-5 h-5 text-primary" />;
      case 'retry_order':
        return <RefreshCw className="w-5 h-5 text-primary" />;
      case 'trigger_automation':
        return <Shield className="w-5 h-5 text-purple-600" />;
      case 'batch_automation':
        return <Shield className="w-5 h-5 text-purple-600" />;
      case 'input_sms':
      case 'manual_match_sms':
        return <MessageSquare className="w-5 h-5 text-blue-600" />;
      case 'create_package':
        return <Package className="w-5 h-5 text-primary" />;
      case 'manual_job_run':
        return <Clock className="w-5 h-5 text-gray-600" />;
      default:
        return <FileText className="w-5 h-5 text-gray-600" />;
    }
  };

  const getActionBadgeColor = (actionType) => {
    // Destructive actions (red)
    if (actionType === 'wallet_redeem') {
      return 'bg-red-100 text-red-700 border-red-200';
    }
    // Positive actions (green)
    if (['wallet_recharge', 'mark_success'].includes(actionType)) {
      return 'bg-green-100 text-green-700 border-green-200';
    }
    // Financial/Wallet actions (orange)
    if (actionType.includes('wallet') || actionType.includes('payment')) {
      return 'bg-orange-100 text-orange-700 border-orange-200';
    }
    // Default (gray)
    return 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const formatActionType = (actionType) => {
    return actionType
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  const hasActiveFilters = filters.adminUsername || filters.actionType || filters.startDate || filters.endDate;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin/dashboard')} className="text-gray-600 hover:text-primary">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-heading font-bold text-gray-900" data-testid="admin-audit-logs-title">Admin Audit Logs</h1>
              <p className="text-sm text-gray-600">{logs.length} actions logged</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button 
              onClick={() => setShowFilters(!showFilters)} 
              variant={showFilters ? "default" : "outline"}
              className={showFilters ? "bg-primary text-white" : ""}
              data-testid="toggle-filters-button"
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters
              {hasActiveFilters && (
                <span className="ml-2 bg-primary text-white text-xs px-1.5 py-0.5 rounded-full">!</span>
              )}
            </Button>
            <Button onClick={fetchLogs} variant="outline" data-testid="refresh-logs-button">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label className="text-gray-700">Admin User</Label>
                <select
                  value={filters.adminUsername}
                  onChange={(e) => setFilters({...filters, adminUsername: e.target.value})}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white text-gray-900"
                  data-testid="filter-admin-select"
                >
                  <option value="">All Admins</option>
                  {adminUsers.map(admin => (
                    <option key={admin} value={admin}>{admin}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-gray-700">Action Type</Label>
                <select
                  value={filters.actionType}
                  onChange={(e) => setFilters({...filters, actionType: e.target.value})}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white text-gray-900"
                  data-testid="filter-action-type-select"
                >
                  <option value="">All Actions</option>
                  {actionTypes.map(type => (
                    <option key={type} value={type}>{formatActionType(type)}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-gray-700">Start Date</Label>
                <Input
                  type="date"
                  value={filters.startDate}
                  onChange={(e) => setFilters({...filters, startDate: e.target.value})}
                  className="mt-1"
                  data-testid="filter-start-date"
                />
              </div>
              <div>
                <Label className="text-gray-700">End Date</Label>
                <Input
                  type="date"
                  value={filters.endDate}
                  onChange={(e) => setFilters({...filters, endDate: e.target.value})}
                  className="mt-1"
                  data-testid="filter-end-date"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <Button onClick={handleApplyFilters} className="bg-primary hover:bg-primary-hover text-white" data-testid="apply-filters-button">
                Apply Filters
              </Button>
              <Button onClick={handleClearFilters} variant="outline" data-testid="clear-filters-button">
                Clear Filters
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Logs List */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 text-primary animate-spin" />
            <span className="ml-2 text-gray-600">Loading logs...</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Audit Logs Found</h3>
            <p className="text-gray-600">
              {hasActiveFilters 
                ? 'No logs match your current filters. Try adjusting your filter criteria.'
                : 'No admin actions have been logged yet.'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Timestamp</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Admin</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Action</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Target</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50" data-testid={`audit-log-${log.id}`}>
                      <td className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                            <User className="w-4 h-4 text-primary" />
                          </div>
                          <span className="font-medium text-gray-900">{log.admin_username || log.admin_id?.slice(0, 8) || 'System'}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          {getActionIcon(log.action_type)}
                          <span className={`px-2 py-1 rounded text-xs font-medium border ${getActionBadgeColor(log.action_type)}`}>
                            {formatActionType(log.action_type)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {log.target_username ? (
                          <div>
                            <div className="font-medium">{log.target_username}</div>
                            <div className="text-xs text-gray-500">User</div>
                          </div>
                        ) : log.target_id ? (
                          <div>
                            <div className="font-mono text-xs">{log.target_id.slice(0, 8).toUpperCase()}</div>
                            <div className="text-xs text-gray-500">Order/Item</div>
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {log.amount !== undefined && log.amount !== null ? (
                          <div className={`font-bold ${log.action_type === 'wallet_redeem' ? 'text-red-600' : 'text-green-600'}`}>
                            {log.action_type === 'wallet_redeem' ? '-' : '+'}₹{log.amount?.toFixed(2)}
                          </div>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="max-w-xs">
                          {log.reason ? (
                            <div>
                              <div className="text-sm text-gray-900 font-medium">Reason:</div>
                              <div className="text-sm text-gray-600 truncate" title={log.reason}>{log.reason}</div>
                            </div>
                          ) : log.details ? (
                            <div className="text-sm text-gray-600 truncate" title={log.details}>{log.details}</div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                          {log.balance_before !== undefined && log.balance_after !== undefined && (
                            <div className="text-xs text-gray-500 mt-1">
                              Balance: ₹{log.balance_before?.toFixed(2)} → ₹{log.balance_after?.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminAuditLogs;
