import React, { useState, useEffect } from 'react';
import { Flame } from 'lucide-react';
import { progressAPI } from '../utils/api';
import { ProgressResponse } from '../types/progress';
import StreakModal from './StreakModal';

const StreakWidget: React.FC = () => {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [pulseAnimation, setPulseAnimation] = useState(false);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const response = await progressAPI.getProgress();
      const newProgress = response.data as ProgressResponse;
      
      // Trigger pulse animation if there's a newly earned milestone
      if (newProgress.newly_earned_milestone) {
        setPulseAnimation(true);
        setTimeout(() => setPulseAnimation(false), 2000);
      }
      
      setProgress(newProgress);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch progress:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-orange-100 to-red-100 rounded-lg animate-pulse">
        <div className="w-5 h-5 bg-orange-300 rounded"></div>
        <div className="w-8 h-4 bg-orange-300 rounded"></div>
      </div>
    );
  }

  if (!progress) {
    return null;
  }

  const streakCount = progress.streak.current;
  const isActive = streakCount > 0;

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        className={`
          relative flex items-center gap-2 px-3 py-2 rounded-lg 
          bg-gradient-to-r from-orange-100 to-red-100 
          hover:from-orange-200 hover:to-red-200
          transition-all duration-300 shadow-sm hover:shadow-md
          ${pulseAnimation ? 'animate-pulse scale-105' : ''}
        `}
        title="Your learning streak"
        aria-label={`Current streak: ${streakCount} days`}
      >
        <Flame 
          size={20} 
          className={`${isActive ? 'text-orange-500' : 'text-gray-400'}`}
          fill={isActive ? 'currentColor' : 'none'}
        />
        <span className="text-lg font-bold text-gray-800">
          {streakCount}
        </span>
        
        {/* Pulsing indicator for active streak */}
        {isActive && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-orange-500 rounded-full animate-ping" />
        )}
      </button>

      {showModal && (
        <StreakModal
          progress={progress}
          onClose={() => setShowModal(false)}
          onRefresh={fetchProgress}
        />
      )}
    </>
  );
};

export default StreakWidget;
