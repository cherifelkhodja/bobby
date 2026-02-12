import { useNavigate } from 'react-router-dom';
import { LogOut, User, Sun, Moon, Monitor, ChevronDown } from 'lucide-react';
import { Menu, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useTheme } from '../../hooks/useTheme';
import { Button } from '../ui/Button';

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
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-40">
      <div className="px-8 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-bold text-primary-600 dark:text-primary-400">
            Bobby
          </h1>
        </div>

        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleTheme}
            leftIcon={getThemeIcon()}
            title={`Thème: ${getThemeLabel()}`}
          >
            {getThemeLabel()}
          </Button>

          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              <User className="h-4 w-4" />
              <span>{user?.full_name}</span>
              <ChevronDown className="h-3 w-3" />
            </Menu.Button>

            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black/5 dark:ring-gray-700 focus:outline-none py-1">
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={() => navigate('/profile')}
                      className={`${
                        active ? 'bg-gray-50 dark:bg-gray-700' : ''
                      } flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300`}
                    >
                      <User className="h-4 w-4 mr-3" />
                      Mon profil
                    </button>
                  )}
                </Menu.Item>
                <div className="border-t border-gray-100 dark:border-gray-700 my-1" />
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={handleLogout}
                      className={`${
                        active ? 'bg-gray-50 dark:bg-gray-700' : ''
                      } flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400`}
                    >
                      <LogOut className="h-4 w-4 mr-3" />
                      Déconnexion
                    </button>
                  )}
                </Menu.Item>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  );
}
