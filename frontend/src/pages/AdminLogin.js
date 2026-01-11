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
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-8 shadow-2xl">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-secondary/10 rounded-full flex items-center justify-center mb-4">
              <Shield className="w-8 h-8 text-secondary" />
            </div>
            <h1 className="text-3xl font-heading font-bold text-white" data-testid="admin-login-title">Admin Access</h1>
            <p className="text-gray-400 mt-2">Secure admin portal</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="admin-login-form">
            <div className="space-y-2">
              <Label htmlFor="identifier" className="text-gray-300">Admin Username</Label>
              <Input
                id="identifier"
                data-testid="admin-login-username-input"
                type="text"
                placeholder="Enter admin username"
                value={formData.identifier}
                onChange={(e) => setFormData({ ...formData, identifier: e.target.value })}
                className="bg-white/5 border-white/10 focus:border-secondary focus:ring-1 focus:ring-secondary rounded-xl h-12 text-white"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-300">Admin Password</Label>
              <Input
                id="password"
                data-testid="admin-login-password-input"
                type="password"
                placeholder="Enter admin password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="bg-white/5 border-white/10 focus:border-secondary focus:ring-1 focus:ring-secondary rounded-xl h-12 text-white"
                required
              />
            </div>

            <Button
              type="submit"
              data-testid="admin-login-submit-button"
              disabled={loading}
              className="w-full bg-secondary text-white font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(176,38,255,0.4)] transition-all"
            >
              {loading ? 'Signing in...' : 'Sign In as Admin'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => navigate('/login')}
              className="text-gray-500 text-xs hover:text-gray-400 transition-colors"
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