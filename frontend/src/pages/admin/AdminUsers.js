import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Users, Plus, Lock, Ban, Trash2, ArrowLeft, Unlock, PlusCircle, MinusCircle, Wallet } from 'lucide-react';

const AdminUsers = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(null);
  const [showRecharge, setShowRecharge] = useState(null);
  const [showRedeem, setShowRedeem] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phone: '',
    password: ''
  });
  const [newPassword, setNewPassword] = useState('');
  const [walletAction, setWalletAction] = useState({
    amount: '',
    reason: ''
  });
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`);
      setUsers(response.data.filter(u => !u.deleted));
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.username || !formData.password) {
      toast.error('Username and password are required');
      return;
    }

    try {
      await axios.post(`${API}/admin/users`, formData);
      toast.success('User created');
      setShowCreate(false);
      resetForm();
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleBlockToggle = async (user) => {
    try {
      await axios.put(`${API}/admin/users/${user.id}`, {
        blocked: !user.blocked
      });
      toast.success(user.blocked ? 'User unblocked' : 'User blocked');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to update user');
    }
  };

  const handleResetPassword = async (userId) => {
    if (!newPassword) {
      toast.error('Please enter new password');
      return;
    }

    try {
      await axios.put(`${API}/admin/users/${userId}`, {
        password: newPassword
      });
      toast.success('Password reset successful');
      setShowResetPassword(null);
      setNewPassword('');
    } catch (error) {
      toast.error('Failed to reset password');
    }
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`Delete user ${user.username}? This cannot be undone.`)) return;
    try {
      await axios.delete(`${API}/admin/users/${user.id}`);
      toast.success('User deleted');
      fetchUsers();
    } catch (error) {
      toast.error('Failed to delete user');
    }
  };

  const handleRecharge = async (user) => {
    const amountRupees = parseFloat(walletAction.amount);
    if (!amountRupees || amountRupees <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    if (!walletAction.reason || walletAction.reason.trim().length < 5) {
      toast.error('Reason is required (minimum 5 characters)');
      return;
    }

    setActionLoading(true);
    try {
      const amountPaisa = Math.round(amountRupees * 100);
      const response = await axios.post(`${API}/admin/users/${user.id}/wallet/recharge`, {
        amount_paisa: amountPaisa,
        reason: walletAction.reason.trim()
      });
      toast.success(response.data.message);
      setShowRecharge(null);
      resetWalletAction();
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to recharge wallet');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRedeem = async (user) => {
    const amountRupees = parseFloat(walletAction.amount);
    if (!amountRupees || amountRupees <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }
    if (!walletAction.reason || walletAction.reason.trim().length < 5) {
      toast.error('Reason is required (minimum 5 characters)');
      return;
    }

    setActionLoading(true);
    try {
      const amountPaisa = Math.round(amountRupees * 100);
      const response = await axios.post(`${API}/admin/users/${user.id}/wallet/redeem`, {
        amount_paisa: amountPaisa,
        reason: walletAction.reason.trim()
      });
      toast.success(response.data.message);
      setShowRedeem(null);
      resetWalletAction();
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to redeem from wallet');
    } finally {
      setActionLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({ username: '', email: '', phone: '', password: '' });
  };

  const resetWalletAction = () => {
    setWalletAction({ amount: '', reason: '' });
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin/dashboard')} className="text-gray-600 hover:text-primary">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-heading font-bold text-gray-900" data-testid="admin-users-title">User Management</h1>
              <p className="text-sm text-gray-600">{users.length} users</p>
            </div>
          </div>
          <Button onClick={() => setShowCreate(true)} className="bg-primary hover:bg-primary-hover text-white" data-testid="create-user-button">
            <Plus className="w-4 h-4 mr-2" />
            Create User
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Username</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Wallet</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Created</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50" data-testid={`user-row-${user.id}`}>
                    <td className="px-6 py-4">
                      <div className="font-semibold text-gray-900">{user.username}</div>
                      <div className="text-xs text-gray-500">ID: {user.id.slice(0, 8)}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {user.email && <div>{user.email}</div>}
                      {user.phone && <div>{user.phone}</div>}
                      {!user.email && !user.phone && <span className="text-gray-400">-</span>}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-primary">₹{user.wallet_balance?.toFixed(2) || '0.00'}</span>
                        <div className="flex gap-1">
                          <button
                            onClick={() => { setShowRecharge(user); resetWalletAction(); }}
                            className="p-1 rounded-full hover:bg-green-100 text-green-600 transition-colors"
                            title="Recharge Wallet"
                            data-testid={`recharge-wallet-${user.id}`}
                          >
                            <PlusCircle className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => { setShowRedeem(user); resetWalletAction(); }}
                            className="p-1 rounded-full hover:bg-red-100 text-red-600 transition-colors"
                            title="Redeem from Wallet"
                            data-testid={`redeem-wallet-${user.id}`}
                          >
                            <MinusCircle className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {user.blocked ? (
                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm">Blocked</span>
                      ) : (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">Active</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{formatDate(user.created_at)}</td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Button onClick={() => handleBlockToggle(user)} size="sm" variant="outline" data-testid={`block-user-${user.id}`}>
                        {user.blocked ? <Unlock className="w-4 h-4" /> : <Ban className="w-4 h-4" />}
                      </Button>
                      <Button onClick={() => setShowResetPassword(user)} size="sm" variant="outline" data-testid={`reset-password-${user.id}`}>
                        <Lock className="w-4 h-4" />
                      </Button>
                      <Button onClick={() => handleDelete(user)} size="sm" variant="destructive" data-testid={`delete-user-${user.id}`}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 text-gray-900">Create User</h2>
            <div className="space-y-4">
              <div>
                <Label className="text-gray-700">Username * (immutable)</Label>
                <Input value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} placeholder="username" data-testid="user-username-input" />
              </div>
              <div>
                <Label className="text-gray-700">Email</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} placeholder="email@example.com" data-testid="user-email-input" />
              </div>
              <div>
                <Label className="text-gray-700">Phone</Label>
                <Input type="tel" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} placeholder="+1234567890" data-testid="user-phone-input" />
              </div>
              <div>
                <Label className="text-gray-700">Password *</Label>
                <Input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} placeholder="Enter password" data-testid="user-password-input" />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreate} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-create-user">Create</Button>
                <Button onClick={() => { setShowCreate(false); resetForm(); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetPassword && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 text-gray-900">Reset Password</h2>
            <p className="text-sm text-gray-600 mb-4">Resetting password for: <strong className="text-gray-900">{showResetPassword.username}</strong></p>
            <div className="space-y-4">
              <div>
                <Label className="text-gray-700">New Password *</Label>
                <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Enter new password" data-testid="reset-password-input" />
              </div>
              <div className="flex gap-2">
                <Button onClick={() => handleResetPassword(showResetPassword.id)} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-reset-password">Reset Password</Button>
                <Button onClick={() => { setShowResetPassword(null); setNewPassword(''); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recharge Wallet Modal */}
      {showRecharge && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <PlusCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Recharge Wallet</h2>
                <p className="text-sm text-gray-600">Add funds to <strong className="text-gray-900">{showRecharge.username}</strong>'s wallet</p>
              </div>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-gray-700">Current Balance: <span className="font-bold text-primary">₹{showRecharge.wallet_balance?.toFixed(2) || '0.00'}</span></p>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="text-gray-700">Amount (₹) *</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  min="0.01"
                  value={walletAction.amount} 
                  onChange={(e) => setWalletAction({...walletAction, amount: e.target.value})} 
                  placeholder="Enter amount in rupees" 
                  data-testid="recharge-amount-input"
                />
              </div>
              <div>
                <Label className="text-gray-700">Reason * (min 5 characters)</Label>
                <Textarea 
                  value={walletAction.reason} 
                  onChange={(e) => setWalletAction({...walletAction, reason: e.target.value})} 
                  placeholder="Enter reason for recharge (e.g., Bonus credit, Refund adjustment)"
                  className="min-h-[80px]"
                  data-testid="recharge-reason-input"
                />
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={() => handleRecharge(showRecharge)} 
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white" 
                  disabled={actionLoading}
                  data-testid="submit-recharge"
                >
                  {actionLoading ? 'Processing...' : 'Recharge Wallet'}
                </Button>
                <Button onClick={() => { setShowRecharge(null); resetWalletAction(); }} variant="outline" className="flex-1" disabled={actionLoading}>Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Redeem Wallet Modal */}
      {showRedeem && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <MinusCircle className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Redeem from Wallet</h2>
                <p className="text-sm text-gray-600">Deduct funds from <strong className="text-gray-900">{showRedeem.username}</strong>'s wallet</p>
              </div>
            </div>
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-gray-700">Current Balance: <span className="font-bold text-primary">₹{showRedeem.wallet_balance?.toFixed(2) || '0.00'}</span></p>
              <p className="text-xs text-gray-500 mt-1">Maximum single redemption: ₹5,000.00</p>
            </div>
            <div className="space-y-4">
              <div>
                <Label className="text-gray-700">Amount (₹) *</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  min="0.01"
                  max={showRedeem.wallet_balance || 0}
                  value={walletAction.amount} 
                  onChange={(e) => setWalletAction({...walletAction, amount: e.target.value})} 
                  placeholder="Enter amount in rupees" 
                  data-testid="redeem-amount-input"
                />
              </div>
              <div>
                <Label className="text-gray-700">Reason * (min 5 characters)</Label>
                <Textarea 
                  value={walletAction.reason} 
                  onChange={(e) => setWalletAction({...walletAction, reason: e.target.value})} 
                  placeholder="Enter reason for redemption (e.g., Correction, Penalty, Refund reversal)"
                  className="min-h-[80px]"
                  data-testid="redeem-reason-input"
                />
              </div>
              <div className="flex gap-2">
                <Button 
                  onClick={() => handleRedeem(showRedeem)} 
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white" 
                  disabled={actionLoading}
                  data-testid="submit-redeem"
                >
                  {actionLoading ? 'Processing...' : 'Redeem from Wallet'}
                </Button>
                <Button onClick={() => { setShowRedeem(null); resetWalletAction(); }} variant="outline" className="flex-1" disabled={actionLoading}>Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
