import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield } from 'lucide-react';

const AdminLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    identifier: '',
    password: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/admin/login`, formData);
      const { token, user_type, username } = response.data;
      login(token, user_type, username);
      toast.success(`Welcome, Admin ${username}`);
      navigate('/admin/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Admin login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen garena-gradient-light flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-lg">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-secondary/10 rounded-full flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-secondary" />
            </div>
            <h1 className="text-3xl font-heading font-bold text-gray-900" data-testid="admin-login-title">Admin Access</h1>
            <p className="text-gray-600 mt-2">Secure admin portal</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="admin-login-form">
            <div className="space-y-2">
              <Label htmlFor="identifier" className="text-gray-700">Admin Username</Label>
              <Input
                id="identifier"
                data-testid="admin-login-username-input"
                type="text"
                placeholder="Enter admin username"
                value={formData.identifier}
                onChange={(e) => setFormData({ ...formData, identifier: e.target.value })}
                className="border-gray-300 focus:border-secondary focus:ring-1 focus:ring-secondary rounded-xl h-12"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-700">Admin Password</Label>
              <Input
                id="password"
                data-testid="admin-login-password-input"
                type="password"
                placeholder="Enter admin password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="border-gray-300 focus:border-secondary focus:ring-1 focus:ring-secondary rounded-xl h-12"
                required
              />
            </div>

            <Button
              type="submit"
              data-testid="admin-login-submit-button"
              disabled={loading}
              className="w-full bg-secondary hover:bg-secondary-hover text-white font-bold h-12 rounded-full transition-all"
            >
              {loading ? 'Signing in...' : 'Sign In as Admin'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => navigate('/login')}
              className="text-gray-500 text-xs hover:text-primary transition-colors"
              data-testid="user-login-link"
            >
              ← Back to User Login
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
