import { Link, useNavigate } from 'react-router-dom';
import { 
  Video as VideoIcon, 
  User as UserIcon, 
  LogOut as LogOutIcon 
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { setToken } from '../api';

type NavbarProps = {
  user: any;
  setUser: (user: any) => void;
};

export default function Navbar({ user, setUser }: NavbarProps) {
  const navigate = useNavigate();

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    window.dispatchEvent(new Event('auth-status-change'));
    navigate('/login');
  };

  return (
    <header className="navbar">
      <Link to="/" className="logo-container" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <VideoIcon className="logo-icon" size={24} />
        <span>Video Summarizer</span>
      </Link>
      
      <div className="nav-user" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <ThemeToggle />
        {user && (
          <>
            <div className="user-badge" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <UserIcon size={14} />
              <span>{user.full_name}</span>
            </div>
            <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '0.45rem 0.85rem' }}>
              <LogOutIcon size={14} />
              <span>Logout</span>
            </button>
          </>
        )}
      </div>
    </header>
  );
}