import React from 'react';
import { useAuth } from '../utils/AuthContext';
import { Calendar, LogOut } from 'lucide-react';
import BatchWidget from './BatchWidget';

interface UserProfilePopupProps {
  onClose: () => void;
}

const UserProfilePopup: React.FC<UserProfilePopupProps> = ({ onClose }) => {
  const { user, logout } = useAuth();
  const { updateProfile } = useAuth();

  const handleLogout = () => {
    onClose();
    logout();
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0).toUpperCase())
      .join('')
      .substring(0, 2);
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40" onClick={handleOverlayClick}>
      <div className="w-full max-w-sm bg-white rounded-lg p-4 shadow-lg mx-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center text-2xl font-bold text-gray-800">
            {user?.name ? getInitials(user.name) : 'U'}
          </div>
          <div className="flex-1 text-left">
            <h3 className="text-lg font-semibold text-gray-900">{user?.name || 'User'}</h3>
            <p className="text-sm text-gray-500">{user?.email || 'No email'}</p>
          </div>
        </div>

        {/* Batch Widget - XP & Stars Progress */}
        <div className="mt-4">
          <BatchWidget />
        </div>

        <div className="mt-4 p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-3">
            <Calendar className="h-5 w-5 text-gray-600" />
            <div>
              <div className="text-xs text-gray-500">Member since</div>
              <div className="text-sm text-gray-700">
                {user?.created_at
                  ? new Date(user.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long'
                  })
                  : 'Recently'
                }
              </div>
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xs text-gray-500">Preferred language</div>
            <div className="text-sm text-gray-700">{user?.preferred_language ? (user.preferred_language === 'tanglish' ? 'Tanglish' : 'English') : 'Tanglish'}</div>
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <button
            className="flex-1 bg-white border border-gray-200 text-gray-700 py-2 rounded-lg"
            onClick={() => {
              // open a simple edit modal/flow: use browser prompt for minimal change
              const choice = window.prompt('Preferred language (tanglish / english):', user?.preferred_language || 'tanglish');
              if (choice && (choice === 'tanglish' || choice === 'english')) {
                updateProfile && updateProfile({ preferred_language: choice });
              } else if (choice) {
                alert('Invalid choice. Use "tanglish" or "english"');
              }
            }}
          >
            Edit Profile
          </button>

          <button
            className="flex-1 bg-red-600 text-white py-2 rounded-lg inline-flex items-center justify-center gap-2"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserProfilePopup;