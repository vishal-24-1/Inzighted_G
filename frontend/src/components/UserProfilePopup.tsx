import React, { useState } from 'react';
import { useAuth } from '../utils/AuthContext';
import { Calendar, LogOut, X, Edit2, Check } from 'lucide-react';
import BatchWidget from './BatchWidget';

interface UserProfilePopupProps {
  onClose: () => void;
}

const UserProfilePopup: React.FC<UserProfilePopupProps> = ({ onClose }) => {
  const { user, logout, updateProfile } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(user?.name || '');
  const [editLanguage, setEditLanguage] = useState(user?.preferred_language || 'tanglish');
  const [isSaving, setIsSaving] = useState(false);

  const handleLogout = () => {
    onClose();
    logout();
  };

  const handleEditProfile = () => {
    setEditName(user?.name || '');
    setEditLanguage(user?.preferred_language || 'tanglish');
    setIsEditing(true);
  };

  const handleSaveProfile = async () => {
    if (!editName.trim()) {
      alert('Name cannot be empty');
      return;
    }

    if (!updateProfile) {
      alert('Update function not available');
      return;
    }

    setIsSaving(true);
    try {
      await updateProfile({ name: editName.trim(), preferred_language: editLanguage });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
      alert('Failed to update profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditName(user?.name || '');
    setEditLanguage(user?.preferred_language || 'tanglish');
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
      <div className="relative w-full max-w-sm bg-white rounded-2xl p-4 shadow-lg mx-4">
        {/* Close button (top-right) */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close profile"
          className="absolute top-3 right-3 inline-flex items-center justify-center w-8 h-8 rounded-full text-gray-600 hover:bg-gray-100"
        >
          <X className="h-4 w-4" />
        </button>

        {!isEditing ? (
          <>
            {/* Profile View Mode */}
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
                className="flex-1 bg-white border border-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-50 transition-colors inline-flex items-center justify-center gap-2"
                onClick={handleEditProfile}
              >
                <Edit2 className="h-4 w-4" />
                Edit Profile
              </button>

              <button
                className="flex-1 bg-red-600 text-white py-2 rounded-lg inline-flex items-center justify-center gap-2 hover:bg-red-700 transition-colors"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Profile Edit Mode */}
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-gray-900">Edit Profile</h3>
              <p className="text-sm text-gray-500 mt-1">Update your name and language preference</p>
            </div>

            <div className="space-y-4">
              {/* Name Field */}
              <div>
                <label htmlFor="edit-name" className="block text-sm font-semibold text-gray-700 mb-2">
                  Name
                </label>
                <input
                  id="edit-name"
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Enter your name"
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors"
                  disabled={isSaving}
                />
              </div>

              {/* Language Preference Dropdown */}
              <div>
                <label htmlFor="edit-language" className="block text-sm font-semibold text-gray-700 mb-2">
                  Preferred Language
                </label>
                <select
                  id="edit-language"
                  value={editLanguage}
                  onChange={(e) => setEditLanguage(e.target.value)}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors bg-white"
                  disabled={isSaving}
                >
                  <option value="tanglish">Tanglish</option>
                  <option value="english">English</option>
                </select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-2">
              <button
                className="flex-1 bg-white border-2 border-gray-300 text-gray-700 py-3 rounded-xl font-semibold hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleCancelEdit}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white py-3 rounded-xl font-semibold hover:from-blue-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
                onClick={handleSaveProfile}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="h-5 w-5" />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default UserProfilePopup;