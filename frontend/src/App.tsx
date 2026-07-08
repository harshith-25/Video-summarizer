import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AlertTriangle as AlertTriangleIcon, CheckCircle2 as CheckCircle2Icon } from 'lucide-react';
import { api, isLoggedIn } from './api';
import { Navbar } from './components/Navbar';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Dashboard } from './pages/Dashboard';
import { Tracker } from './pages/Tracker';
import { Details } from './pages/Details';

// Simple Route Guard
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!isLoggedIn()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}

export function App() {
  const [user, setUser] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Initialize theme on app load
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const handleAuthChange = () => {
      if (!isLoggedIn()) {
        setUser(null);
      }
    };
    window.addEventListener('auth-status-change', handleAuthChange);

    if (isLoggedIn()) {
      fetchUserProfile();
    }

    return () => {
      window.removeEventListener('auth-status-change', handleAuthChange);
    };
  }, []);

  const fetchUserProfile = async () => {
    try {
      const res = await api.getMe();
      if (res.user) {
        setUser(res.user);
      }
    } catch (e: any) {
      console.error('Failed to retrieve user profile', e);
      setUser(null);
    }
  };

  // Toast messages auto-clear timer
  useEffect(() => {
    if (errorMsg || successMsg) {
      const timer = setTimeout(() => {
        setErrorMsg(null);
        setSuccessMsg(null);
      }, 7000);
      return () => clearTimeout(timer);
    }
  }, [errorMsg, successMsg]);

  return (
    <Router>
      <div className="app-container">
        {/* Toast Alerts */}
        {errorMsg && (
          <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1000 }} className="error-box">
            <AlertTriangleIcon size={18} />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1000, background: 'hsla(150, 80%, 42%, 0.15)', border: '1px solid hsla(150, 80%, 42%, 0.3)', color: 'hsl(150, 95%, 70%)' }} className="error-box">
            <CheckCircle2Icon size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Global Navbar */}
        <Navbar user={user} setUser={setUser} />

        <main className="main-content">
          <Routes>
            <Route 
              path="/login" 
              element={isLoggedIn() ? <Navigate to="/" replace /> : <Login fetchUserProfile={fetchUserProfile} />} 
            />
            <Route 
              path="/signup" 
              element={isLoggedIn() ? <Navigate to="/" replace /> : <Signup />} 
            />
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <Dashboard setErrorMsg={setErrorMsg} setSuccessMsg={setSuccessMsg} />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/tracker/:jobId" 
              element={
                <ProtectedRoute>
                  <Tracker setErrorMsg={setErrorMsg} setSuccessMsg={setSuccessMsg} />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/summary/:videoId" 
              element={
                <ProtectedRoute>
                  <Details setErrorMsg={setErrorMsg} />
                </ProtectedRoute>
              } 
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      <style>{`
        .spin {
          animation: spin-anim 1.5s linear infinite;
        }
        @keyframes spin-anim {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </Router>
  );
}

export default App;