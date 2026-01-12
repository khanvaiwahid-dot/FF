import { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import '@/index.css';

import Login from './pages/Login';
import Signup from './pages/Signup';
import AdminLogin from './pages/AdminLogin';
import TopUp from './pages/TopUp';
import PaymentMethod from './pages/PaymentMethod';
import PaymentDetails from './pages/PaymentDetails';
import OrderStatus from './pages/OrderStatus';
import Wallet from './pages/Wallet';
import WalletAddFunds from './pages/WalletAddFunds';
import WalletPaymentDetails from './pages/WalletPaymentDetails';
import AdminDashboard from './pages/AdminDashboard';
import AdminOrders from './pages/AdminOrders';
import AdminReview from './pages/AdminReview';
import AdminPayments from './pages/AdminPayments';
import AdminProducts from './pages/admin/AdminProducts';
import AdminGarenaAccounts from './pages/admin/AdminGarenaAccounts';
import AdminUsers from './pages/admin/AdminUsers';
import AdminSMSInbox from './pages/admin/AdminSMSInbox';
import AdminAuditLogs from './pages/admin/AdminAuditLogs';
import UserOrders from './pages/UserOrders';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userType = localStorage.getItem('userType');
    const username = localStorage.getItem('username');
    const walletBalance = localStorage.getItem('walletBalance');

    if (token && userType && username) {
      setUser({ token, userType, username, walletBalance: parseFloat(walletBalance) || 0 });
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    setLoading(false);
  }, []);

  const login = (token, userType, username, walletBalance = 0) => {
    localStorage.setItem('token', token);
    localStorage.setItem('userType', userType);
    localStorage.setItem('username', username);
    localStorage.setItem('walletBalance', walletBalance.toString());
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser({ token, userType, username, walletBalance });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userType');
    localStorage.removeItem('username');
    localStorage.removeItem('walletBalance');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  const updateWalletBalance = (balance) => {
    localStorage.setItem('walletBalance', balance.toString());
    setUser(prev => ({ ...prev, walletBalance: balance }));
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, updateWalletBalance, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { user, loading } = useAuth();

  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center"><div className="text-primary">Loading...</div></div>;

  if (!user) return <Navigate to="/login" />;
  if (adminOnly && user.userType !== 'admin') return <Navigate to="/" />;
  if (!adminOnly && user.userType === 'admin') return <Navigate to="/admin/dashboard" />;

  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/" element={<ProtectedRoute><TopUp /></ProtectedRoute>} />
          <Route path="/payment/:orderId" element={<ProtectedRoute><PaymentMethod /></ProtectedRoute>} />
          <Route path="/payment-details/:orderId" element={<ProtectedRoute><PaymentDetails /></ProtectedRoute>} />
          <Route path="/order/:orderId" element={<ProtectedRoute><OrderStatus /></ProtectedRoute>} />
          <Route path="/wallet" element={<ProtectedRoute><Wallet /></ProtectedRoute>} />
          <Route path="/orders" element={<ProtectedRoute><UserOrders /></ProtectedRoute>} />
          <Route path="/wallet/add-funds" element={<ProtectedRoute><WalletAddFunds /></ProtectedRoute>} />
          <Route path="/wallet/payment-details" element={<ProtectedRoute><WalletPaymentDetails /></ProtectedRoute>} />
          <Route path="/admin/dashboard" element={<ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>} />
          <Route path="/admin/products" element={<ProtectedRoute adminOnly><AdminProducts /></ProtectedRoute>} />
          <Route path="/admin/garena-accounts" element={<ProtectedRoute adminOnly><AdminGarenaAccounts /></ProtectedRoute>} />
          <Route path="/admin/users" element={<ProtectedRoute adminOnly><AdminUsers /></ProtectedRoute>} />
          <Route path="/admin/sms-inbox" element={<ProtectedRoute adminOnly><AdminSMSInbox /></ProtectedRoute>} />
          <Route path="/admin/orders" element={<ProtectedRoute adminOnly><AdminOrders /></ProtectedRoute>} />
          <Route path="/admin/review" element={<ProtectedRoute adminOnly><AdminReview /></ProtectedRoute>} />
          <Route path="/admin/payments" element={<ProtectedRoute adminOnly><AdminPayments /></ProtectedRoute>} />
        </Routes>
        <Toaster position="top-center" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
export { API };