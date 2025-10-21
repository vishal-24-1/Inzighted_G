import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, X } from 'lucide-react';
import logo from '../../logo.svg';

interface WelcomeScreenProps {
  onClose: () => void;
}

const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onClose }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4"
    >
      {/* Close button - top right */}
      <motion.button
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        onClick={onClose}
        className="absolute top-6 right-6 bg-white/90 hover:bg-white text-gray-700 hover:text-gray-900 rounded-full p-3 shadow-lg hover:shadow-xl transition-all hover:scale-110"
        aria-label="Close welcome screen"
      >
        <X size={24} />
      </motion.button>

      <div className="max-w-2xl mx-auto text-center">
        {/* Logo with bounce animation */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{
            type: "spring",
            stiffness: 260,
            damping: 20,
            delay: 0.1
          }}
          className="flex justify-center mb-8"
        >
          <div className="relative">
            <img src={logo} alt="InzightEd G" className="h-16 w-auto" />
            
            {/* Sparkle effect */}
            <motion.div
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6, duration: 0.3 }}
              className="absolute -top-2 -right-2"
            >
              <Sparkles className="text-yellow-500" size={24} />
            </motion.div>
          </div>
        </motion.div>

        {/* Welcome heading with slide up animation */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="text-4xl md:text-5xl font-bold text-gray-900 mb-4"
        >
          Welcome to <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">InzightEd G!</span>
        </motion.h1>

        {/* Thank you message */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6 }}
          className="text-lg text-gray-600 mb-3"
        >
          Thanks for choosing us! 🎉
        </motion.p>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.6 }}
          className="text-base md:text-lg text-gray-700 mb-12 max-w-xl mx-auto leading-relaxed"
        >
          InzightEd G helps you analyze your performance and grow smarter every day with personalized tutoring and intelligent insights.
        </motion.p>

        {/* Feature highlights with stagger animation */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12 max-w-3xl mx-auto"
        >
          {[
            { icon: '📚', title: 'Smart Tutoring', desc: 'AI-powered learning sessions' },
            { icon: '📊', title: 'Track Progress', desc: 'Monitor your growth' },
            { icon: '🎯', title: 'Personalized', desc: 'Tailored to your needs' }
          ].map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.8, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: 1 + index * 0.1, duration: 0.4 }}
              className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
            >
              <div className="text-3xl mb-3">{feature.icon}</div>
              <h3 className="font-semibold text-gray-900 mb-1">{feature.title}</h3>
              <p className="text-sm text-gray-600">{feature.desc}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* CTA Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.3, duration: 0.6 }}
          className="flex justify-center items-center"
        >
          <motion.p
            className="text-gray-500 text-sm"
          >
            Click the × button above to continue
          </motion.p>
        </motion.div>

        {/* Decorative elements */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.4 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="absolute top-20 left-10 text-6xl"
          style={{ transform: 'rotate(-15deg)' }}
        >
          ✨
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.4 }}
          transition={{ delay: 1.6, duration: 1 }}
          className="absolute bottom-20 right-10 text-6xl"
          style={{ transform: 'rotate(15deg)' }}
        >
          🚀
        </motion.div>
      </div>
    </motion.div>
  );
};

export default WelcomeScreen;
