import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Gem } from 'lucide-react';

const Signup = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (!formData.email && !formData.phone) {
      toast.error('Please provide either email or phone number');
      return;
    }

    setLoading(true);

    try {
      const payload = {
        username: formData.username,
        password: formData.password,
        email: formData.email || null,
        phone: formData.phone || null
      };

      const response = await axios.post(`${API}/auth/signup`, payload);
      const { token, user_type, username, wallet_balance } = response.data;
      login(token, user_type, username, wallet_balance);
      toast.success(`Welcome, ${username}! Your account has been created.`);
      navigate('/');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen garena-gradient-light flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-lg">
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <Gem className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-3xl font-heading font-bold text-gray-900" data-testid="signup-title">Join DiamondStore</h1>
            <p className="text-gray-600 mt-2">Create your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" data-testid="signup-form">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-gray-700">Username *</Label>
              <Input
                id="username"
                data-testid="signup-username-input"
                type="text"
                placeholder="Choose a unique username"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
                required
              />
              <p className="text-xs text-gray-500">Username cannot be changed later</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-700">Email</Label>
              <Input
                id="email"
                data-testid="signup-email-input"
                type="email"
                placeholder="your@email.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone" className="text-gray-700">Phone</Label>
              <Input
                id="phone"
                data-testid="signup-phone-input"
                type="tel"
                placeholder="Your phone number"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-700">Password *</Label>
              <Input
                id="password"
                data-testid="signup-password-input"
                type="password"
                placeholder="Create a strong password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-gray-700">Confirm Password *</Label>
              <Input
                id="confirmPassword"
                data-testid="signup-confirm-password-input"
                type="password"
                placeholder="Re-enter your password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="border-gray-300 focus:border-primary focus:ring-1 focus:ring-primary rounded-xl h-12"
                required
              />
            </div>

            <Button
              type="submit"
              data-testid="signup-submit-button"
              disabled={loading}
              className="w-full bg-primary hover:bg-primary-hover text-white font-bold h-12 rounded-full transition-all"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline font-semibold" data-testid="login-link">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Signup;
