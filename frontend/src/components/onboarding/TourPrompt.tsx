import React from 'react';
import { motion } from 'framer-motion';
import { Compass, Sparkles } from 'lucide-react';

interface TourPromptProps {
  onStartTour: () => void;
  onSkip: () => void;
}

/**
 * TourPrompt - Blur overlay with floating "Start Tour" button
 * Shows after user closes the welcome screen
 */
const TourPrompt: React.FC<TourPromptProps> = ({ onStartTour, onSkip }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-40 flex items-center justify-center"
      style={{ backdropFilter: 'blur(8px)' }}
    >
      {/* Semi-transparent overlay */}
      <div className="absolute inset-0 bg-black/30" />

      {/* Floating Tour Button */}
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{
          type: "spring",
          stiffness: 260,
          damping: 20,
          delay: 0.1
        }}
        className="relative z-10 text-center"
      >
        {/* Animated glow effect */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full blur-xl"
        />

        {/* Main button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={onStartTour}
          className="relative bg-gradient-to-r from-blue-600 to-purple-600 text-white px-12 py-6 rounded-full font-bold text-xl shadow-2xl flex items-center gap-3 group"
        >
          <Compass size={32} className="group-hover:rotate-180 transition-transform duration-700" />
          <span>Start Tour</span>
          <Sparkles size={24} className="animate-pulse" />
        </motion.button>

        {/* Skip text below */}
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          onClick={onSkip}
          className="mt-6 text-white/90 hover:text-white text-sm font-medium underline underline-offset-4"
        >
          Skip tour and explore on my own
        </motion.button>

        {/* Helper text */}
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-4 text-white/70 text-sm max-w-xs mx-auto"
        >
          Let us show you around! Takes less than 2 minutes ⏱️
        </motion.p>
      </motion.div>
    </motion.div>
  );
};

export default TourPrompt;
