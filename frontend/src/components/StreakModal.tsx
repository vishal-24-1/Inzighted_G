import React from 'react';
import { X, Trophy, TrendingUp } from 'lucide-react';
import { ProgressResponse, MILESTONE_BADGES } from '../types/progress';

interface StreakModalProps {
  progress: ProgressResponse;
  onClose: () => void;
  onRefresh: () => void;
}

const StreakModal: React.FC<StreakModalProps> = ({ progress, onClose, onRefresh }) => {
  const { streak } = progress;
  const progressPercent = (streak.current / streak.next_milestone) * 100;
  const hasNewMilestone = progress.newly_earned_milestone;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div 
        className="relative bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button (top-right) - match UserProfilePopup style */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute top-3 right-3 inline-flex items-center justify-center w-8 h-8 rounded-full text-gray-600 hover:bg-gray-100"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center">
              <TrendingUp size={24} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Your Streak</h2>
              <p className="text-sm text-gray-500">Keep learning daily!</p>
            </div>
          </div>
        </div>

        {/* Current Streak Display */}
        <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-6 mb-6 text-center">
          <div className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-red-500 mb-2">
            {streak.current}
          </div>
          <p className="text-gray-600 font-medium">Day Streak 🔥</p>
          {streak.last_test_date && (
            <p className="text-xs text-gray-500 mt-2">
              Last test: {new Date(streak.last_test_date).toLocaleDateString()}
            </p>
          )}
        </div>

        {/* New Milestone Animation */}
        {hasNewMilestone && (
          <div className="mb-6 p-4 bg-yellow-50 border-2 border-yellow-300 rounded-xl animate-bounce">
            <div className="flex items-center gap-3">
              <Trophy size={32} className="text-yellow-600" />
              <div>
                <p className="font-bold text-yellow-900">New Milestone Unlocked!</p>
                <p className="text-sm text-yellow-700">{hasNewMilestone}</p>
              </div>
            </div>
          </div>
        )}

        {/* Progress to Next Milestone */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Next: {streak.next_milestone_name}
            </span>
            <span className="text-sm text-gray-500">
              {streak.current} / {streak.next_milestone}
            </span>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-orange-400 to-red-500 transition-all duration-500 ease-out"
              style={{ width: `${Math.min(progressPercent, 100)}%` }}
            />
          </div>
        </div>

        {/* Earned Milestones */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Trophy size={16} />
            Earned Milestone Badges
          </h3>
          {streak.earned_milestones.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">
              Complete 7 consecutive days to earn your first badge! 🎯
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {streak.earned_milestones.map((milestone) => {
                const badge = MILESTONE_BADGES[milestone];
                if (!badge) return null;
                
                return (
                  <div
                    key={milestone}
                    className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
                    style={{ 
                      borderColor: badge.color,
                      backgroundColor: `${badge.color}10`
                    }}
                  >
                    <span className="text-2xl">{badge.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">
                        {badge.name}
                      </p>
                      <p className="text-xs text-gray-500">{milestone}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-xs text-blue-900 text-center">
            💡 <strong>Pro Tip:</strong> Complete one test per day to maintain your streak. 
            Earned badges stay with you forever, even if your streak resets!
          </p>
        </div>
      </div>
    </div>
  );
};

export default StreakModal;
