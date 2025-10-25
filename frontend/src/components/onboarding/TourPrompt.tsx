import React from 'react';
import { motion } from 'framer-motion';
import { Compass } from 'lucide-react';

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

      {/* Floating Tour Button (mobile-first, centered) */}
      <motion.div
        initial={{ scale: 0, rotate: -180 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{
          type: "spring",
          stiffness: 260,
          damping: 20,
          delay: 0.1
        }}
        className="relative z-10 flex flex-col items-center justify-center px-6 gap-4 text-center w-full"
      >
        {/* Static glow background (no pulsing) */}
        <div className="absolute inset-0 rounded-full blur-xl opacity-30 bg-gradient-to-r from-blue-500 to-blue-400" />

        {/* Main button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
          onClick={onStartTour}
          className="relative z-10 w-full max-w-xs mx-auto bg-gradient-to-r from-blue-600 to-blue-400 text-white px-8 py-4 rounded-full font-bold text-lg shadow-2xl flex items-center justify-center gap-3 group"
        >
          <Compass size={28} className="group-hover:rotate-180 transition-transform duration-700" />
          <span>Start Tour</span>
        </motion.button>

        {/* Prominent Skip action (mobile-first full width) */}
        <motion.button
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.12 }}
          onClick={onSkip}
          className="z-10 mt-2 w-full max-w-xs mx-auto bg-white/10 hover:bg-white/20 text-white font-semibold py-3 px-4 rounded-2xl text-center"
        >
          Skip tour and explore on my own
        </motion.button>

        {/* Helper text (smaller, centered) */}
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="z-10 mt-2 text-white/80 text-sm max-w-xs mx-auto"
        >
          Let us show you around! Takes less than 2 minutes ⏱️
        </motion.p>
      </motion.div>
    </motion.div>
  );
};

export default TourPrompt;
