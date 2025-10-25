import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  ArrowRight,
  X,
  BookOpen,
  BarChart3,
  User,
  CheckCircle,
  Smartphone,
  Shield,
  Rocket
} from 'lucide-react';

interface WelcomeScreenProps {
  onClose: () => void;
}

type Step = 'welcome' | 'features' | 'ready';

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onClose }) => {
  const [currentStep, setCurrentStep] = useState<Step>('welcome');
  const [direction, setDirection] = useState(1);

  const steps: { key: Step; title: string; subtitle: string }[] = [
    { key: 'welcome', title: 'Welcome to InzightEd G!', subtitle: 'Your learning journey starts here' },
    { key: 'features', title: 'Smart Features', subtitle: 'Everything you need to succeed' },
    { key: 'ready', title: "You're All Set!", subtitle: 'Ready to begin learning?' },
  ];

  const navigateToStep = (step: Step, dir: number) => {
    setDirection(dir);
    setCurrentStep(step);
  };

  const nextStep = () => {
    const currentIndex = steps.findIndex(step => step.key === currentStep);
    if (currentIndex < steps.length - 1) {
      navigateToStep(steps[currentIndex + 1].key, 1);
    }
  };

  const prevStep = () => {
    const currentIndex = steps.findIndex(step => step.key === currentStep);
    if (currentIndex > 0) {
      navigateToStep(steps[currentIndex - 1].key, -1);
    }
  };

  const stepVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 300 : -300,
      opacity: 0,
      scale: 0.9
    }),
    center: {
      x: 0,
      opacity: 1,
      scale: 1
    },
    exit: (direction: number) => ({
      x: direction > 0 ? -300 : 300,
      opacity: 0,
      scale: 0.9
    })
  };

  const ProgressDots = () => (
    <div className="flex justify-center space-x-2 mb-8">
      {steps.map((step, index) => {
        const isActive = step.key === currentStep;
        const isCompleted = steps.findIndex(s => s.key === currentStep) > index;

        return (
          <motion.div
            key={step.key}
            className={`w-2 h-2 rounded-full ${isActive ? 'bg-blue-600' :
              isCompleted ? 'bg-green-500' : 'bg-gray-300'
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

  const StepContent = () => {
    switch (currentStep) {
      case 'welcome':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-8"
          >

            <div className="space-y-4">
              <motion.h2
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-3xl font-bold text-gray-900"
              >
                Welcome to Inzight<span className="bg-gradient-to-r from-blue-600 to-blue-400 bg-clip-text text-transparent">Ed</span>
              </motion.h2>

              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-gray-600 text-lg"
              >
                Thanks for choosing us! 🎉
              </motion.p>

              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="text-gray-700 leading-relaxed"
              >
                InzightEd helps you analyze your performance and grow smarter every day with personalized tutoring and intelligent insights.
              </motion.p>
            </div>
          </motion.div>
        );

      case 'features':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-8"
          >
            <div className="text-center space-y-2">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", delay: 0.1 }}
                className="flex justify-center"
              >
                <Rocket className="h-12 w-12 text-blue-600" />
              </motion.div>
              <h2 className="text-2xl font-bold text-gray-900">Smart Features</h2>
              <p className="text-gray-600">Everything you need to succeed</p>
            </div>

            <div className="space-y-4">
              {[
                {
                  icon: BookOpen,
                  title: 'AI-Powered Tutoring',
                  description: 'Personalized learning sessions that adapt to your pace',
                  color: 'text-blue-600'
                },
                {
                  icon: BarChart3,
                  title: 'Progress Analytics',
                  description: 'Track your growth with detailed insights and reports',
                  color: 'text-blue-500'
                },
                {
                  icon: User,
                  title: 'Personalized Learning',
                  description: 'Content tailored specifically to your learning style',
                  color: 'text-blue-400'
                },
                {
                  icon: Smartphone,
                  title: 'Mobile Optimized',
                  description: 'Learn anywhere, anytime on your mobile device',
                  color: 'text-blue-600'
                }
              ].map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + index * 0.1 }}
                  className="flex items-start space-x-4 p-4 bg-white/80 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100"
                >
                  <div className={`p-2 rounded-lg bg-gray-50 ${feature.color}`}>
                    <feature.icon size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">{feature.title}</h3>
                    <p className="text-sm text-gray-600">{feature.description}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        );

      case 'ready':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-8 text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{
                type: "spring",
                stiffness: 200,
                delay: 0.3
              }}
              className="flex justify-center"
            >
              <div className="relative mt-4">
                <CheckCircle className="h-20 w-20 text-green-500" />
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.8 }}
                  className="absolute -inset-4 bg-green-100 rounded-full -z-10"
                />
              </div>
            </motion.div>

            <div className="space-y-4">
              <motion.h2
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-3xl font-bold text-gray-900"
              >
                You're All Set!
              </motion.h2>

              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="text-gray-600 text-lg"
              >
                Ready to begin your learning journey?
              </motion.p>

              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="text-gray-700 leading-relaxed"
              >
                Start exploring personalized tutoring sessions and track your progress with intelligent insights.
              </motion.p>
            </div>
          </motion.div>
        );

      default:
        return null;
    }
  };

  const currentStepIndex = steps.findIndex(step => step.key === currentStep);
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4"
    >
      {/* Close button - only show on first step or ready step */}
      {(isFirstStep || isLastStep) && (
        <motion.button
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          onClick={onClose}
          className="absolute top-6 right-6 bg-white/90 hover:bg-white text-gray-700 hover:text-gray-900 rounded-full p-3 shadow-lg hover:shadow-xl transition-all hover:scale-110 z-10"
          aria-label="Close welcome screen"
        >
          <X size={24} />
        </motion.button>
      )}

      <div className="w-full max-w-md mx-auto">
        {/* Progress dots */}
        <ProgressDots />

        {/* Step content with slide animation */}
        <div className="relative h-[500px] overflow-hidden">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentStep}
              custom={direction}
              variants={stepVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                x: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 },
                scale: { duration: 0.2 }
              }}
              className="absolute inset-0"
            >
              <StepContent />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation buttons - fixed at bottom (safe-area aware & responsive) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          position: 'fixed',
          left: 0,
          right: 0,
          bottom: 'calc(1rem + env(safe-area-inset-bottom))',
          display: 'flex',
          justifyContent: 'center',
          pointerEvents: 'auto',
          zIndex: 60,
          paddingLeft: '1rem',
          paddingRight: '1rem'
        }}
      >
        <div className="w-full max-w-md flex flex-col sm:flex-row items-center sm:justify-between gap-3">
          {isLastStep ? (
            // Show primary "Start Learning Now" action when on last step
            <div className="w-full">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={onClose}
                className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-400 text-white px-6 py-3 rounded-2xl font-semibold shadow-lg hover:shadow-xl transition-shadow"
              >
                <span>Start Learning Now</span>
              </motion.button>
            </div>
          ) : (
            <>
              {/* Left group (Back + Skip) */}
              <div className="w-full sm:w-auto flex gap-3 justify-center sm:justify-start">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={prevStep}
                  className={`px-5 py-3 rounded-2xl font-medium transition-all ${isFirstStep ? 'invisible' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    } w-full sm:w-auto`}
                  disabled={isFirstStep}
                >
                  Back
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={onClose}
                  className="px-5 py-3 rounded-2xl font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all w-full sm:w-auto"
                >
                  Skip
                </motion.button>
              </div>

              {/* Primary action */}
              <div className="w-full sm:w-auto">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={nextStep}
                  className="w-full sm:w-auto flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-400 text-white px-6 py-3 rounded-2xl font-medium shadow-lg hover:shadow-xl transition-shadow"
                >
                  <span>Continue</span>
                  <ArrowRight size={18} />
                </motion.button>
              </div>
            </>
          )}
        </div>
      </motion.div>

      {/* Decorative elements */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.3 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute top-20 left-6 text-4xl"
        style={{ transform: 'rotate(-15deg)' }}
      >
        ✨
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.3 }}
        transition={{ delay: 1.6, duration: 1 }}
        className="absolute bottom-20 right-6 text-4xl"
        style={{ transform: 'rotate(15deg)' }}
      >
        🚀
      </motion.div>
    </motion.div>
  );
};

export default WelcomeScreen;