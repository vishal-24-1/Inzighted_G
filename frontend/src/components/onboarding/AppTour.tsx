import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, ArrowLeft, X, CheckCircle, Map, Home, User, BookOpen, Zap, MessageCircle, Target } from 'lucide-react';

interface AppTourProps {
  onComplete: () => void;
  onSkip: () => void;
  run: boolean;
}

type TourStep = {
  target: string;
  title: string;
  content: string;
  icon: React.ComponentType<any>;
  highlight?: 'primary' | 'secondary' | 'accent';
};

const AppTour: React.FC<AppTourProps> = ({ onComplete, onSkip, run }) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [visible, setVisible] = useState<boolean>(run);
  const [direction, setDirection] = useState<number>(1);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const steps: TourStep[] = [
    {
      target: '[aria-label="Open profile"], [data-tour="profile"]',
      title: 'Your Learning Profile',
      content: 'Track your progress, view achievements, and customize your learning preferences here.',
      icon: User,
      highlight: 'secondary'
    },
    {
      target: '.streak-widget, [data-tour="streak"]',
      title: 'Daily Streak',
      content: 'Build your learning habit! Maintain your streak for bonus rewards and track your consistency.',
      icon: Zap,
      highlight: 'accent'
    },
    {
      target: '[aria-label="Open Library"], [data-tour="library"]',
      title: 'Smart Library',
      content: 'Access all your documents and learning materials. Start AI-powered tutoring sessions instantly.',
      icon: BookOpen,
      highlight: 'primary'
    },
    {
      target: '[aria-label="Boost Me"], [data-tour="boost"]',
      title: 'Boost Me',
      content: 'Get personalized insights about your learning patterns and receive tailored improvement suggestions.',
      icon: Target,
      highlight: 'secondary'
    },
    {
      target: '[placeholder*="Drop your notes"], [data-tour="upload"]',
      title: 'Start Learning',
      content: 'Drag & drop your notes or documents here to begin an interactive AI tutoring session.',
      icon: MessageCircle,
      highlight: 'accent'
    },
    {
      target: '[data-tour="mobile-dock"], .mobile-dock',
      title: 'Quick Navigation',
      content: 'Switch between Home, Chat, and Profile with one tap. Everything you need is right here.',
      icon: Home,
      highlight: 'primary'
    },
  ];

  // Progress indicators
  const ProgressDots = () => (
    <div className="flex justify-center space-x-2 mb-6">
      {steps.map((_, index) => {
        const isActive = index === currentStep;
        const isCompleted = index < currentStep;

        return (
          <motion.div
            key={index}
            className={`w-2 h-2 rounded-full ${isActive
              ? 'bg-blue-600 scale-125'
              : isCompleted
                ? 'bg-green-500'
                : 'bg-gray-300'
              }`}
            initial={false}
            animate={{
              scale: isActive ? 1.2 : 1,
              width: isActive ? 16 : 8
            }}
            transition={{ duration: 0.3 }}
          />
        );
      })}
    </div>
  );

  const StepIcon = ({ step, isActive }: { step: TourStep; isActive: boolean }) => {
    const IconComponent = step.icon;
    // Use a softer, blue-forward palette consistent with WelcomeScreen/TourPrompt
    const highlightColors: Record<string, string> = {
      primary: 'from-blue-600 to-blue-400',
      secondary: 'from-green-500 to-teal-400',
      accent: 'from-indigo-500 to-blue-400'
    };

    return (
      <motion.div
        className={`p-2 rounded-xl bg-gradient-to-br ${highlightColors[step.highlight || 'primary']} shadow-md`}
        initial={false}
        animate={{
          scale: isActive ? 1.05 : 1,
          rotate: isActive ? [0, -4, 4, 0] : 0
        }}
        transition={{ duration: 0.4 }}
      >
        <IconComponent className="text-white" size={18} />
      </motion.div>
    );
  };

  useEffect(() => {
    setVisible(run);
    setCurrentStep(0);
  }, [run]);

  useEffect(() => {
    if (!visible) return;

    const step = steps[currentStep];
    if (!step) return;

    // Scroll target into view with smooth animation
    const targetEl = step.target === 'body'
      ? document.documentElement
      : document.querySelector(step.target);

    if (targetEl) {
      setTimeout(() => {
        targetEl.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'center'
        });
      }, 300);
    }
  }, [currentStep, visible]);

  const navigateStep = (newStep: number) => {
    const newDirection = newStep > currentStep ? 1 : -1;
    setDirection(newDirection);
    setCurrentStep(newStep);
  };

  const closeTour = (completed: boolean = false) => {
    setVisible(false);
    setTimeout(() => {
      if (completed) {
        onComplete();
      } else {
        onSkip();
      }
    }, 300);
  };

  const nextStep = () => {
    if (currentStep >= steps.length - 1) {
      closeTour(true);
    } else {
      navigateStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      navigateStep(currentStep - 1);
    }
  };

  if (!visible) return null;

  const currentStepData = steps[currentStep];
  const targetEl = currentStepData.target === 'body'
    ? null
    : document.querySelector(currentStepData.target) as HTMLElement | null;

  const rect = targetEl ? targetEl.getBoundingClientRect() : null;
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  // Mobile-optimized tooltip positioning
  const tooltipStyle: React.CSSProperties = {
    position: 'absolute',
    zIndex: 10002,
    pointerEvents: 'auto',
    width: 'calc(100vw - 120px)',
    maxWidth: 320,
    left: '50%',
    transform: 'translateX(-50%)',
  };

  // Position tooltip based on available space
  if (rect) {
    const viewportHeight = window.innerHeight;
    const spaceAbove = rect.top;
    const spaceBelow = viewportHeight - rect.bottom;

    // Prefer positioning above the element if there's enough space
    if (spaceAbove > 200) {
      tooltipStyle.top = `${Math.max(20, rect.top - 180)}px`;
    } else {
      tooltipStyle.top = `${Math.min(viewportHeight - 300, rect.bottom + 20)}px`;
    }
  } else {
    // Center for welcome step
    tooltipStyle.top = '20%';
  }

  const stepVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 50 : -50,
      opacity: 0,
      scale: 0.9
    }),
    center: {
      x: 0,
      opacity: 1,
      scale: 1
    },
    exit: (direction: number) => ({
      x: direction > 0 ? -50 : 50,
      opacity: 0,
      scale: 0.9
    })
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 pointer-events-none"
    >
      {/* Overlay: keep backdrop-blur but use a subtle, semi-transparent tint so the page remains visible */}
      <motion.div
        className="absolute inset-0 bg-transparent"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ pointerEvents: 'auto' }}
        onClick={() => closeTour(false)}
      />

      {/* Highlight overlay with pulsing animation */}
      {rect && (
        <motion.div
          aria-hidden
          className="absolute rounded-2xl border-2 border-white/80 shadow-2xl"
          style={{
            left: rect.left + window.scrollX - 12,
            top: rect.top + window.scrollY - 12,
            width: rect.width + 24,
            height: rect.height + 24,
            // reduced outer-shadow alpha so the "cutout" around the target is more transparent
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.25), 0 8px 32px rgba(0,0,0,0.15)',
            zIndex: 10001,
          }}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{
            scale: 1,
            opacity: 1,
            borderColor: ['rgba(255,255,255,0.8)', 'rgba(255,255,255,0.4)', 'rgba(255,255,255,0.8)']
          }}
          transition={{
            duration: 0.5,
            borderColor: {
              repeat: Infinity,
              duration: 2,
              ease: "easeInOut"
            }
          }}
        />
      )}

      {/* Tooltip Container */}
      <div
        ref={tooltipRef}
        style={tooltipStyle}
      >
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentStep}
            custom={direction}
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30
            }}
            className="bg-white rounded-2xl p-3 shadow-md border border-gray-100"
          >
            {/* Header with compact icon and title */}
            <div className="flex items-center space-x-3 mb-2">
              <StepIcon step={currentStepData} isActive={true} />
              <div>
                <h3 className="text-sm font-semibold text-gray-900">
                  {currentStepData.title}
                </h3>
              </div>
            </div>

            {/* Content (compact) */}
            <motion.p
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12 }}
              className="text-gray-700 text-xs leading-snug mb-3"
            >
              {currentStepData.content}
            </motion.p>

            {/* Navigation buttons (compact) - Back on left, Next on right */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={prevStep}
                  disabled={isFirstStep}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-sm transition-all ${isFirstStep
                    ? 'text-gray-400 bg-gray-100'
                    : 'text-gray-700 bg-gray-100 hover:bg-gray-200'
                    }`}
                >
                  <ArrowLeft size={14} />
                  <span>Back</span>
                </motion.button>
              </div>

              <div className="flex items-center">
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={nextStep}
                  className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-blue-400 to-blue-600 shadow-sm"
                >
                  <span>{isLastStep ? 'Get Started' : 'Next'}</span>
                  {isLastStep ? (
                    <CheckCircle size={14} />
                  ) : (
                    <ArrowRight size={14} />
                  )}
                </motion.button>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default AppTour;