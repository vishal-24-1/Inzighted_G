import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  onProfileClick?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen = true, onClose, onProfileClick }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleNavigate = (path: string) => {
    onClose && onClose();
    navigate(path);
  };

  return (
    // Off-canvas sidebar
    <aside
      className={`fixed top-0 left-0 h-full w-72 max-w-full bg-white shadow-lg z-40 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      aria-hidden={!isOpen}
      aria-label="Sidebar navigation"
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div className="text-lg font-semibold">InzightEd</div>
          <button
            onClick={onClose}
            aria-label="Close sidebar"
            className="w-9 h-9 flex items-center justify-center rounded-full bg-white text-gray-600 border border-gray-100 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            ×
          </button>
        </div>

        

        <nav className="px-2 py-3 flex-1 overflow-y-auto">
          <ul className="space-y-1">
            <li>
              <button
                onClick={() => handleNavigate('/')}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 flex items-center gap-3 text-gray-800"
              >
                Home
              </button>
            </li>
            <li>
              <button
                onClick={() => handleNavigate('/tutoring')}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 flex items-center gap-3 text-gray-800"
              >
                Tutoring
              </button>
            </li>
            <li>
              <button
                onClick={() => handleNavigate('/boost')}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 flex items-center gap-3 text-gray-800"
              >
                Boost
              </button>
            </li>
            <li>
              <button
                onClick={() => document.getElementById('file-upload')?.click()}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 flex items-center gap-3 text-gray-800"
              >
                Upload Notes
              </button>
            </li>
            <li>
              <button
                onClick={() => {
                  onProfileClick && onProfileClick();
                  onClose && onClose();
                }}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 flex items-center gap-3 text-gray-800"
              >
                Profile
              </button>
            </li>
          </ul>
        </nav>

        <div className="px-4 py-4 border-t border-gray-100">
          <button
            onClick={() => {
              onProfileClick && onProfileClick();
              onClose && onClose();
            }}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50"
          >
            <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center text-sm font-medium text-gray-700">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 text-left">
              <div className="text-sm font-medium text-gray-900">{user?.name || 'User'}</div>
              <div className="text-xs text-gray-500">View profile</div>
            </div>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
