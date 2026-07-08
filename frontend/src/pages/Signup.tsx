import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Video as VideoIcon, 
  Eye as EyeIcon, 
  EyeOff as EyeOffIcon, 
  AlertTriangle as AlertTriangleIcon 
} from 'lucide-react';
import { api } from '../api';

export function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);
    try {
      await api.signup({ email, password, full_name: fullName });
      navigate('/login', { state: { successMsg: 'Signup successful! Please log in.' } });
    } catch (e: any) {
      setErrorMsg(e.message || 'Signup failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card glass-panel">
        <div className="auth-header">
          <div style={{ display: 'inline-flex', padding: '0.75rem', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', marginBottom: '1rem', color: 'var(--accent-primary)' }}>
            <VideoIcon size={32} />
          </div>
          <h2>Create Account</h2>
          <p>Get started in just a few seconds</p>
        </div>

        {errorMsg && (
          <div className="error-box">
            <AlertTriangleIcon size={18} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSignupSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input 
              type="text" 
              className="form-input" 
              placeholder="John Doe" 
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required 
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              placeholder="email@domain.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Password</label>
            <div className="password-input-container">
              <input 
                type={showPassword ? "text" : "password"} 
                className="form-input" 
                placeholder="••••••••" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required 
              />
              <button 
                type="button" 
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="auth-toggle">
          <p>
            Already have an account?{' '}
            <Link to="/login">Log In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
export default Signup;
