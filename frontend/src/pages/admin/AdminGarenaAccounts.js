import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Plus, Edit, Trash2, ArrowLeft, Eye, EyeOff } from 'lucide-react';

const AdminGarenaAccounts = () => {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editAccount, setEditAccount] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    pin: ''
  });

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await axios.get(`${API}/admin/garena-accounts`);
      setAccounts(response.data);
    } catch (error) {
      toast.error('Failed to load Garena accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.email || !formData.password || !formData.pin) {
      toast.error('Please fill all fields');
      return;
    }

    try {
      await axios.post(`${API}/admin/garena-accounts`, formData);
      toast.success('Garena account created');
      setShowCreate(false);
      resetForm();
      fetchAccounts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create account');
    }
  };

  const handleUpdate = async () => {
    try {
      const updateData = { active: formData.active };
      if (formData.name) updateData.name = formData.name;
      if (formData.email) updateData.email = formData.email;
      if (formData.password) updateData.password = formData.password;
      if (formData.pin) updateData.pin = formData.pin;

      await axios.put(`${API}/admin/garena-accounts/${editAccount.id}`, updateData);
      toast.success('Garena account updated');
      setEditAccount(null);
      resetForm();
      fetchAccounts();
    } catch (error) {
      toast.error('Failed to update account');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this Garena account?')) return;
    try {
      await axios.delete(`${API}/admin/garena-accounts/${id}`);
      toast.success('Garena account deleted');
      fetchAccounts();
    } catch (error) {
      toast.error('Failed to delete account');
    }
  };

  const openEdit = (account) => {
    setEditAccount(account);
    setFormData({
      name: account.name,
      email: account.email,
      password: '',
      pin: '',
      active: account.active
    });
  };

  const resetForm = () => {
    setFormData({ name: '', email: '', password: '', pin: '', active: true });
  };

  const formatDate = (date) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
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
              <h1 className="text-xl font-heading font-bold text-gray-900" data-testid="garena-accounts-title">Garena Accounts</h1>
              <p className="text-sm text-gray-600">{accounts.length} accounts</p>
            </div>
          </div>
          <Button onClick={() => setShowCreate(true)} className="bg-primary hover:bg-primary-hover text-white" data-testid="create-garena-account-button">
            <Plus className="w-4 h-4 mr-2" />
            Add Account
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {accounts.map((account) => (
          <div key={account.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6" data-testid={`garena-account-${account.id}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <Shield className="w-5 h-5 text-primary" />
                  <h3 className="text-lg font-bold text-gray-900">{account.name}</h3>
                  {account.active ? (
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">Active</span>
                  ) : (
                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm">Disabled</span>
                  )}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Email:</span>
                    <span className="text-gray-900 font-medium">{account.email}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Password:</span>
                    <span className="text-gray-900 font-mono">***hidden***</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">PIN:</span>
                    <span className="text-gray-900 font-mono">***hidden***</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-600">Last Used:</span>
                    <span className="text-gray-900">{formatDate(account.last_used)}</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => openEdit(account)} size="sm" variant="outline" data-testid={`edit-garena-${account.id}`}>
                  <Edit className="w-4 h-4" />
                </Button>
                <Button onClick={() => handleDelete(account.id)} size="sm" variant="destructive" data-testid={`delete-garena-${account.id}`}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Add Garena Account</h2>
            <div className="space-y-4">
              <div>
                <Label>Account Name *</Label>
                <Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} placeholder="e.g., Primary Account" data-testid="garena-name-input" />
              </div>
              <div>
                <Label>Email *</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} placeholder="garena@example.com" data-testid="garena-email-input" />
              </div>
              <div>
                <Label>Password *</Label>
                <Input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} placeholder="Enter password" data-testid="garena-password-input" />
              </div>
              <div>
                <Label>Security PIN *</Label>
                <Input type="password" value={formData.pin} onChange={(e) => setFormData({...formData, pin: e.target.value})} placeholder="6-digit PIN" data-testid="garena-pin-input" />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreate} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-create-garena">Create</Button>
                <Button onClick={() => { setShowCreate(false); resetForm(); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editAccount && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Edit Garena Account</h2>
            <div className="space-y-4">
              <div>
                <Label>Account Name</Label>
                <Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
              </div>
              <div>
                <Label>Email</Label>
                <Input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
              </div>
              <div>
                <Label>Update Password (leave empty to keep current)</Label>
                <Input type="password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} placeholder="New password" data-testid="edit-garena-password" />
              </div>
              <div>
                <Label>Update PIN (leave empty to keep current)</Label>
                <Input type="password" value={formData.pin} onChange={(e) => setFormData({...formData, pin: e.target.value})} placeholder="New PIN" data-testid="edit-garena-pin" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={formData.active} onChange={(e) => setFormData({...formData, active: e.target.checked})} data-testid="edit-garena-active" />
                <Label>Active</Label>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleUpdate} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-edit-garena">Update</Button>
                <Button onClick={() => { setEditAccount(null); resetForm(); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminGarenaAccounts;