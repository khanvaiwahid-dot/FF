import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth, API } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Package, Plus, Edit, Trash2, ArrowLeft } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const AdminProducts = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editProduct, setEditProduct] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    type: 'diamond',
    amount: '',
    price: '',
    active: true
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/admin/packages`);
      setProducts(response.data);
    } catch (error) {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.amount || !formData.price) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      await axios.post(`${API}/admin/packages`, {
        name: formData.name,
        type: formData.type,
        amount: parseInt(formData.amount),
        price: parseFloat(formData.price),
        active: formData.active
      });
      toast.success('Product created');
      setShowCreate(false);
      resetForm();
      fetchProducts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create product');
    }
  };

  const handleUpdate = async () => {
    try {
      await axios.put(`${API}/admin/packages/${editProduct.id}`, {
        name: formData.name || undefined,
        type: formData.type || undefined,
        amount: formData.amount ? parseInt(formData.amount) : undefined,
        price: formData.price ? parseFloat(formData.price) : undefined,
        active: formData.active
      });
      toast.success('Product updated');
      setEditProduct(null);
      resetForm();
      fetchProducts();
    } catch (error) {
      toast.error('Failed to update product');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this product?')) return;
    try {
      await axios.delete(`${API}/admin/packages/${id}`);
      toast.success('Product deleted');
      fetchProducts();
    } catch (error) {
      toast.error('Failed to delete product');
    }
  };

  const openEdit = (product) => {
    setEditProduct(product);
    setFormData({
      name: product.name,
      type: product.type,
      amount: product.amount.toString(),
      price: product.price.toString(),
      active: product.active
    });
  };

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'diamond',
      amount: '',
      price: '',
      active: true
    });
  };

  const getTypeLabel = (type) => {
    const labels = {
      diamond: 'Diamond',
      membership: 'Membership',
      evo_access: 'Evo Access'
    };
    return labels[type] || type;
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
              <h1 className="text-xl font-heading font-bold text-gray-900" data-testid="admin-products-title">Products Management</h1>
              <p className="text-sm text-gray-600">{products.length} products</p>
            </div>
          </div>
          <Button onClick={() => setShowCreate(true)} className="bg-primary hover:bg-primary-hover text-white" data-testid="create-product-button">
            <Plus className="w-4 h-4 mr-2" />
            Create Product
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Product</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Price</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-700 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-50" data-testid={`product-row-${product.id}`}>
                    <td className="px-6 py-4">
                      <div className="font-semibold text-gray-900">{product.name}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">{getTypeLabel(product.type)}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-900">{product.amount}</td>
                    <td className="px-6 py-4">
                      <span className="font-bold text-primary">₹{product.price}</span>
                    </td>
                    <td className="px-6 py-4">
                      {product.active ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">Active</span>
                      ) : (
                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm">Disabled</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <Button onClick={() => openEdit(product)} size="sm" variant="outline" data-testid={`edit-product-${product.id}`}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button onClick={() => handleDelete(product.id)} size="sm" variant="destructive" data-testid={`delete-product-${product.id}`}>
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
            <h2 className="text-xl font-bold mb-4">Create Product</h2>
            <div className="space-y-4">
              <div>
                <Label>Product Name *</Label>
                <Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} placeholder="e.g., 115 Diamonds" data-testid="product-name-input" />
              </div>
              <div>
                <Label>Type *</Label>
                <select value={formData.type} onChange={(e) => setFormData({...formData, type: e.target.value})} className="w-full border border-gray-300 rounded-md p-2">
                  <option value="diamond">Diamond</option>
                  <option value="membership">Membership</option>
                  <option value="evo_access">Evo Access</option>
                </select>
              </div>
              <div>
                <Label>Amount (Diamonds or Days) *</Label>
                <Input type="number" value={formData.amount} onChange={(e) => setFormData({...formData, amount: e.target.value})} placeholder="e.g., 115" data-testid="product-amount-input" />
              </div>
              <div>
                <Label>Price (₹) *</Label>
                <Input type="number" step="0.01" value={formData.price} onChange={(e) => setFormData({...formData, price: e.target.value})} placeholder="e.g., 4.50" data-testid="product-price-input" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={formData.active} onChange={(e) => setFormData({...formData, active: e.target.checked})} />
                <Label>Active</Label>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreate} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-create-product">Create</Button>
                <Button onClick={() => { setShowCreate(false); resetForm(); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Edit Product</h2>
            <div className="space-y-4">
              <div>
                <Label>Product Name</Label>
                <Input value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
              </div>
              <div>
                <Label>Type</Label>
                <select value={formData.type} onChange={(e) => setFormData({...formData, type: e.target.value})} className="w-full border border-gray-300 rounded-md p-2">
                  <option value="diamond">Diamond</option>
                  <option value="membership">Membership</option>
                  <option value="evo_access">Evo Access</option>
                </select>
              </div>
              <div>
                <Label>Amount</Label>
                <Input type="number" value={formData.amount} onChange={(e) => setFormData({...formData, amount: e.target.value})} />
              </div>
              <div>
                <Label>Price (₹)</Label>
                <Input type="number" step="0.01" value={formData.price} onChange={(e) => setFormData({...formData, price: e.target.value})} data-testid="edit-product-price" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={formData.active} onChange={(e) => setFormData({...formData, active: e.target.checked})} data-testid="edit-product-active" />
                <Label>Active</Label>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleUpdate} className="flex-1 bg-primary hover:bg-primary-hover text-white" data-testid="submit-edit-product">Update</Button>
                <Button onClick={() => { setEditProduct(null); resetForm(); }} variant="outline" className="flex-1">Cancel</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminProducts;