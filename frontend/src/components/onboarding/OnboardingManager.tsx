import React, { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import WelcomeScreen from './WelcomeScreen';

type OnboardingStep = 'idle' | 'welcome' | 'completed';

interface OnboardingManagerProps {
  userId: string;
  onComplete: () => void;
  onWelcomeClose: () => void;
}

const ONBOARDING_STORAGE_KEY = 'inzighted_onboarding_completed';

/**
 * OnboardingManager - Shows welcome screen for first-time users
 * 
 * Flow:
 * 1. Check if user has completed onboarding (via localStorage)
 * 2. If not, show Welcome screen with close button
 * 3. User clicks close → Call onWelcomeClose (parent shows tour prompt)
 * 
 * Note: This component only handles the Welcome screen. The parent (Home.tsx)
 * manages the tour prompt and tour separately.
 */
const OnboardingManager: React.FC<OnboardingManagerProps> = ({ 
  userId, 
  onComplete, 
  onWelcomeClose
}) => {
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('idle');
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState(false);

  useEffect(() => {
    // Check if user has already completed onboarding
    const checkOnboardingStatus = () => {
      try {
        const completedData = localStorage.getItem(ONBOARDING_STORAGE_KEY);
        
        if (completedData) {
          const parsed = JSON.parse(completedData);
          // Check if this specific user has completed onboarding
          if (parsed[userId]) {
            setHasSeenOnboarding(true);
            setCurrentStep('completed');
            return;
          }
        }
        
        // First-time user - start onboarding
        setCurrentStep('welcome');
      } catch (error) {
        console.error('Error checking onboarding status:', error);
        // On error, show onboarding to be safe
        setCurrentStep('welcome');
      }
    };

    checkOnboardingStatus();
  }, [userId]);

  // Don't render anything if user has already seen onboarding
  if (hasSeenOnboarding || currentStep === 'completed' || currentStep === 'idle') {
    return null;
  }

  return (
    <AnimatePresence mode="wait">
      {currentStep === 'welcome' && (
        <WelcomeScreen
          key="welcome"
          onClose={onWelcomeClose}
        />
      )}
    </AnimatePresence>
  );
};

export default OnboardingManager;

/**
 * Utility function to manually reset onboarding for a user
 * (useful for testing or if user wants to see tour again)
 */
export const resetOnboarding = (userId: string) => {
  try {
    const existingData = localStorage.getItem(ONBOARDING_STORAGE_KEY);
    if (existingData) {
      const data = JSON.parse(existingData);
      delete data[userId];
      localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(data));
    }
  } catch (error) {
    console.error('Error resetting onboarding:', error);
  }
};

/**
 * Utility function to check if user has completed onboarding
 */
export const hasCompletedOnboarding = (userId: string): boolean => {
  try {
    const completedData = localStorage.getItem(ONBOARDING_STORAGE_KEY);
    if (completedData) {
      const parsed = JSON.parse(completedData);
      return !!parsed[userId];
    }
    return false;
  } catch (error) {
    console.error('Error checking onboarding status:', error);
    return false;
  }
};
