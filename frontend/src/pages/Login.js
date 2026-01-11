import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Gem } from 'lucide-react';

const Login = () => {
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
      const response = await axios.post(`${API}/auth/login`, formData);
      const { token, user_type, username, wallet_balance } = response.data;
      login(token, user_type, username, wallet_balance);
      toast.success(`Welcome back, ${username}!`);
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4" 
         style={{backgroundImage: 'url(https://images.unsplash.com/photo-1674453736349-029f0ffc863a?crop=entropy&cs=srgb&fm=jpg&q=85)', backgroundSize: 'cover', backgroundPosition: 'center'}}>
      <div className="absolute inset-0 bg-background/90 backdrop-blur-sm"></div>
      
      <div className="relative w-full max-w-md">
        <div className="bg-card/60 backdrop-blur-xl border border-white/5 rounded-2xl p-8 shadow-2xl">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <Gem className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl font-heading font-bold text-white" data-testid="login-title">Welcome Back</h1>
            <p className="text-gray-400 mt-2">Sign in to continue</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
            <div className="space-y-2">
              <Label htmlFor="identifier" className="text-gray-300">Username / Email / Phone</Label>
              <Input
                id="identifier"
                data-testid="login-identifier-input"
                type="text"
                placeholder="Enter your username, email or phone"
                value={formData.identifier}
                onChange={(e) => setFormData({ ...formData, identifier: e.target.value })}
                className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-300">Password</Label>
              <Input
                id="password"
                data-testid="login-password-input"
                type="password"
                placeholder="Enter your password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="bg-white/5 border-white/10 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12 text-white"
                required
              />
            </div>

            <Button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full bg-primary text-black font-bold h-12 rounded-full hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 text-center space-y-3">
            <p className="text-gray-400 text-sm">
              Don't have an account?{' '}
              <Link to="/signup" className="text-primary hover:underline" data-testid="signup-link">
                Sign up
              </Link>
            </p>
            <p className="text-gray-500 text-xs">
              <Link to="/admin/login" className="hover:text-primary transition-colors" data-testid="admin-login-link">
                Admin Login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;