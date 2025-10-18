import React, { useState, useEffect } from 'react';
import { Award, Star } from 'lucide-react';
import { progressAPI } from '../utils/api';
import { ProgressResponse, BATCH_COLORS } from '../types/progress';

interface BatchWidgetProps {
  compact?: boolean;
}

const BatchWidget: React.FC<BatchWidgetProps> = ({ compact = false }) => {
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [animatingStars, setAnimatingStars] = useState<number[]>([]);

  useEffect(() => {
    fetchProgress();
  }, []);

  const fetchProgress = async () => {
    try {
      const response = await progressAPI.getProgress();
      const newProgress = response.data as ProgressResponse;
      
      // Trigger star animation if stars changed
      if (newProgress.stars_changed && newProgress.batch.current_star > 0) {
        const newStar = newProgress.batch.current_star - 1;
        setAnimatingStars([newStar]);
        setTimeout(() => setAnimatingStars([]), 1000);
      }
      
      // Trigger batch upgrade animation
      if (newProgress.batch_upgraded) {
        // Could add confetti or special animation here
        console.log('🎉 Batch upgraded to:', newProgress.batch.current_batch);
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
      <div className="animate-pulse">
        <div className="h-24 bg-gradient-to-r from-blue-100 to-teal-100 rounded-xl"></div>
      </div>
    );
  }

  if (!progress) {
    return null;
  }

  const { batch } = progress;
  const batchColor = BATCH_COLORS[batch.current_batch] || BATCH_COLORS.Bronze;
  // Compute progress percent toward the next star as: current / (current + remaining)
  const xpTarget = (batch.xp_points || 0) + (batch.xp_to_next_star || 0);
  const xpPercent = xpTarget > 0 ? Math.min(((batch.xp_points || 0) / xpTarget) * 100, 100) : 0;

  // Calculate stars (filled based on current_star)
  const stars = Array.from({ length: batch.stars_per_batch }, (_, i) => ({
    filled: i < batch.current_star,
    animating: animatingStars.includes(i),
  }));

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-blue-50 to-teal-50 rounded-lg">
        <div 
          className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
          style={{ backgroundColor: `${batchColor.primary}20` }}
        >
          {batchColor.icon}
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-900">{batch.current_batch}</p>
          <div className="flex gap-1">
            {stars.map((star, i) => (
              <Star
                key={i}
                size={12}
                className={`${star.filled ? 'text-yellow-400' : 'text-gray-300'} transition-all`}
                fill={star.filled ? 'currentColor' : 'none'}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="p-6 rounded-2xl shadow-lg bg-gradient-to-br transition-all duration-300 hover:shadow-xl"
      style={{
        background: `linear-gradient(135deg, ${batchColor.primary}15, ${batchColor.secondary}30)`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div 
            className="w-14 h-14 rounded-full flex items-center justify-center text-3xl shadow-md"
            style={{ backgroundColor: `${batchColor.primary}30` }}
          >
            {batchColor.icon}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">{batch.current_batch} Batch</h3>
            <p className="text-xs text-gray-600">Progress to mastery</p>
          </div>
        </div>
        <Award size={24} style={{ color: batchColor.primary }} />
      </div>

      {/* Stars Display */}
      <div className="flex items-center justify-center gap-3 mb-4">
        {stars.map((star, i) => (
          <div
            key={i}
            className={`
              transition-all duration-500
              ${star.animating ? 'animate-bounce scale-125' : ''}
            `}
          >
            <Star
              size={32}
              className={`
                ${star.filled ? 'text-yellow-400' : 'text-gray-300'}
                transition-all duration-300
              `}
              fill={star.filled ? 'currentColor' : 'none'}
              strokeWidth={2}
            />
          </div>
        ))}
      </div>

      {/* XP Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-700 font-medium">XP to next star</span>
          <span className="text-gray-900 font-bold">
            {batch.xp_points.toFixed(1)} / {(batch.xp_points + batch.xp_to_next_star).toFixed(1)}
          </span>
        </div>
        <div className="w-full h-2 bg-white/50 rounded-full overflow-hidden">
          <div 
            className="h-full transition-all duration-500 ease-out rounded-full"
            style={{ 
              width: `${xpPercent}%`,
              background: `linear-gradient(90deg, ${batchColor.primary}, ${batchColor.secondary})`
            }}
          />
        </div>
      </div>

      {/* Next Batch Info */}
      {batch.current_star === batch.stars_per_batch && batch.next_batch && (
        <div className="mt-4 p-3 bg-white/80 rounded-lg text-center">
          <p className="text-xs text-gray-600">
            🎉 All stars earned! Keep earning XP to advance to <strong>{batch.next_batch}</strong>
          </p>
        </div>
      )}

      {/* Tooltip */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-blue-900 text-center">
          💡 Earn XP by completing tests. Each star represents your progress toward the next batch level!
        </p>
      </div>
    </div>
  );
};

export default BatchWidget;
