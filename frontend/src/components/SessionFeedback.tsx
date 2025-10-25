import React, { useState, useEffect } from 'react';
import { feedbackAPI } from '../utils/api';
import { Sparkles, ArrowRight, X } from 'lucide-react';

interface SessionFeedbackProps {
  sessionId: string;
  onComplete: () => void;
  onSkip?: () => void;
}

const SessionFeedback: React.FC<SessionFeedbackProps> = ({ sessionId, onComplete, onSkip }) => {
  const [rating, setRating] = useState<number>(7);
  const [liked, setLiked] = useState<string>('');
  const [improve, setImprove] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [bounceRating, setBounceRating] = useState(false);

  // Get emoji and text based on rating
  const getRatingDisplay = (value: number): { emoji: string; text: string; color: string } => {
    if (value <= 3) {
      return { emoji: '😭', text: 'Ouch!', color: '#dc3545' };
    } else if (value <= 6) {
      return { emoji: '😐', text: 'Could be better', color: '#ffc107' };
    } else if (value <= 8) {
      return { emoji: '🙂', text: 'Nice!', color: '#28a745' };
    } else {
      return { emoji: '🤩', text: 'Legendary!', color: '#007bff' };
    }
  };

  const ratingDisplay = getRatingDisplay(rating);

  // Handle rating change with animation
  const handleRatingChange = (value: number) => {
    setRating(value);
    setBounceRating(true);
    
    // Show confetti for legendary ratings
    if (value >= 9) {
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 2000);
    }
    
    setTimeout(() => setBounceRating(false), 300);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setIsSubmitting(true);

    try {
      await feedbackAPI.submitFeedback(sessionId, {
        rating,
        liked: liked.trim(),
        improve: improve.trim(),
        // If improve is empty, mark as skipped so backend validation passes
        skipped: !improve.trim(),
      });
      
      onComplete();
    } catch (error: any) {
      console.error('Failed to submit feedback:', error);
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = async () => {
    setIsSubmitting(true);

    try {
      await feedbackAPI.submitFeedback(sessionId, {
        skipped: true,
      });
      
      if (onSkip) {
        onSkip();
      } else {
        onComplete();
      }
    } catch (error: any) {
      console.error('Failed to skip feedback:', error);
      // Still proceed even if skip fails
      if (onSkip) {
        onSkip();
      } else {
        onComplete();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      {/* Confetti effect */}
      {showConfetti && (
        <div className="fixed inset-0 pointer-events-none z-50">
          {[...Array(30)].map((_, i) => (
            <div
              key={i}
              className="absolute animate-confetti"
              style={{
                left: `${Math.random() * 100}%`,
                top: '-10%',
                animationDelay: `${Math.random() * 0.5}s`,
                fontSize: `${Math.random() * 20 + 10}px`,
              }}
            >
              🎉
            </div>
          ))}
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-6 rounded-t-2xl">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Sparkles size={24} />
              Quick Feedback
            </h2>
            <button
              onClick={handleSkip}
              className="text-white/80 hover:text-white transition-colors"
              disabled={isSubmitting}
              aria-label="Skip feedback"
            >
              <X size={24} />
            </button>
          </div>
          <p className="text-blue-100 text-sm">
            Help us make your learning experience better!
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Rating Slider with Gamification */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              On a scale of 0 to 10, how likely are you to recommend this to a friend?
            </label>
            
            {/* Emoji Display with Animation */}
            <div className="flex justify-center mb-4">
              <div
                className={`text-6xl transition-transform duration-300 ${
                  bounceRating ? 'scale-125' : 'scale-100'
                }`}
              >
                {ratingDisplay.emoji}
              </div>
            </div>

            {/* Rating Text */}
            <div
              className="text-center font-bold text-lg mb-4 transition-colors duration-300"
              style={{ color: ratingDisplay.color }}
            >
              {ratingDisplay.text}
            </div>

            {/* Slider */}
            <div className="relative">
              <input
                type="range"
                min="0"
                max="10"
                value={rating}
                onChange={(e) => handleRatingChange(parseInt(e.target.value))}
                className="w-full h-3 bg-gray-200 rounded-full appearance-none cursor-pointer slider"
                style={{
                  background: `linear-gradient(to right, ${ratingDisplay.color} 0%, ${ratingDisplay.color} ${rating * 10}%, #e5e7eb ${rating * 10}%, #e5e7eb 100%)`,
                }}
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>0</span>
                <span className="font-bold text-base">{rating}</span>
                <span>10</span>
              </div>
            </div>
          </div>

          {/* What They Liked - Optional */}
          <div>
            <label htmlFor="liked" className="block text-sm font-semibold text-gray-700 mb-2">
              What's one thing you liked? <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <input
              id="liked"
              type="text"
              value={liked}
              onChange={(e) => setLiked(e.target.value)}
              placeholder="e.g., The questions were challenging..."
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors"
              maxLength={200}
            />
          </div>

          {/* What to Improve - Optional */}
          <div>
            <label htmlFor="improve" className="block text-sm font-semibold text-gray-700 mb-2">
              What's one thing we should improve? <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <textarea
              id="improve"
              value={improve}
              onChange={(e) => setImprove(e.target.value)}
              placeholder="e.g., More hints would be helpful..."
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors resize-none"
              rows={3}
              maxLength={500}
            />
            <div className="text-xs text-gray-400 mt-1 text-right">
              {improve.length}/500
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleSkip}
              disabled={isSubmitting}
              className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  Submit
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      <style>{`
        @keyframes confetti {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(360deg);
            opacity: 0;
          }
        }

        .animate-confetti {
          animation: confetti 2s ease-out forwards;
        }

        /* Custom slider styling */
        input[type='range']::-webkit-slider-thumb {
          appearance: none;
          width: 24px;
          height: 24px;
          background: white;
          border: 3px solid ${ratingDisplay.color};
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
          transition: transform 0.2s;
        }

        input[type='range']::-webkit-slider-thumb:hover {
          transform: scale(1.2);
        }

        input[type='range']::-moz-range-thumb {
          width: 24px;
          height: 24px;
          background: white;
          border: 3px solid ${ratingDisplay.color};
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
          transition: transform 0.2s;
        }

        input[type='range']::-moz-range-thumb:hover {
          transform: scale(1.2);
        }
      `}</style>
    </div>
  );
};

export default SessionFeedback;
