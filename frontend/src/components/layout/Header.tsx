import { useNavigate } from 'react-router-dom';
import { LogOut, Search, Sun, Moon, Monitor } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useTheme } from '../../hooks/useTheme';

function initialsOf(name?: string | null): string {
  if (!name) return '·';
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('') || '·'
  );
}

export function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getThemeIcon = () => {
    if (theme === 'light') return <Sun className="h-4 w-4" />;
    if (theme === 'dark') return <Moon className="h-4 w-4" />;
    return <Monitor className="h-4 w-4" />;
  };

  const getThemeLabel = () => {
    if (theme === 'light') return 'Clair';
    if (theme === 'dark') return 'Sombre';
    return 'Auto';
  };

  return (
    <header className="top">
      <h1 className="logo">Bobby</h1>
      <div className="flex items-center gap-3">
        <div className="srch hidden lg:flex">
          <Search className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">Rechercher (réf, consultant, société…)</span>
        </div>
        <button
          type="button"
          className="thm"
          onClick={toggleTheme}
          title={`Thème : ${getThemeLabel()}`}
          aria-label={`Basculer le thème (actuel : ${getThemeLabel()})`}
        >
          {getThemeIcon()}
        </button>
        <button
          type="button"
          className="av cursor-pointer"
          onClick={() => navigate('/profile')}
          title="Mon profil"
          aria-label="Mon profil"
        >
          {initialsOf(user?.full_name || `${user?.first_name ?? ''} ${user?.last_name ?? ''}`)}
        </button>
        <button
          type="button"
          className="thm"
          onClick={handleLogout}
          title="Déconnexion"
          aria-label="Déconnexion"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
