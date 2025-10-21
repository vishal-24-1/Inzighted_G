import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowLeft, X, CheckCircle } from 'lucide-react';

interface AppTourProps {
  onComplete: () => void;
  onSkip: () => void;
  run: boolean;
}

type TourStep = {
  target: string;
  title?: string;
  content: string;
};

const AppTour: React.FC<AppTourProps> = ({ onComplete, onSkip, run }) => {
  const [index, setIndex] = useState<number>(0);
  const [visible, setVisible] = useState<boolean>(run);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  const steps: TourStep[] = [
    {
      target: 'body',
      title: 'Welcome Aboard! 👋',
      content: "Let's take a quick tour of InzightEd G! We'll show you the main features to help you get started.",
    },
    {
      target: '[aria-label="Open profile"]',
      title: 'Your Profile',
      content: 'Access your profile here to view your stats, change settings, and manage your account.',
    },
    {
      target: '.streak-widget, [data-tour="streak"]',
      title: 'Daily Streak 🔥',
      content: 'Track your learning streak! Keep coming back daily to maintain your streak and earn rewards.',
    },
    {
      target: '[aria-label="Open Library"]',
      title: 'Document Library 📚',
      content: 'Your document library is here. Access all your uploaded materials and start tutoring sessions anytime.',
    },
    {
      target: '[aria-label="Boost Me"]',
      title: 'Boost Me 🚀',
      content: 'Get personalized insights about your learning style and performance. This feature helps you understand yourself better!',
    },
    {
      target: '[placeholder*="Drop your notes"]',
      title: 'Start Learning ✍️',
      content: 'Start a new tutoring session by dropping your notes or documents here. Our AI tutor will help you learn!',
    },
    {
      target: '[data-tour="mobile-dock"], .mobile-dock',
      title: 'Quick Navigation 🧭',
      content: 'Navigate easily between Home, Chat, and your Profile using this dock. Everything you need is just a tap away!',
    },
  ];

  useEffect(() => {
    setVisible(run);
    setIndex(0);
  }, [run]);

  useEffect(() => {
    if (!visible) return;
    // Scroll target into view
    const step = steps[index];
    if (!step) return;
    const el = document.querySelector(step.target) as HTMLElement | null;
    if (el) {
      try {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } catch (e) {
        // ignore
      }
    }
  }, [index, visible]);

  const close = (complete = false) => {
    setVisible(false);
    if (complete) onComplete(); else onSkip();
  };

  const next = () => {
    if (index >= steps.length - 1) {
      close(true);
    } else {
      setIndex(i => i + 1);
    }
  };

  const back = () => setIndex(i => Math.max(0, i - 1));

  if (!visible) return null;

  const step = steps[index];
  const targetEl = step.target === 'body' ? null : document.querySelector(step.target) as HTMLElement | null;
  const rect = targetEl ? targetEl.getBoundingClientRect() : null;

  // Compute tooltip position (place above the element if there's room, otherwise below)
  const tooltipStyle: React.CSSProperties = {};
  const TOOLTIP_MAX_WIDTH = 360;
  const VIEWPORT_PADDING = 12;

  if (rect) {
    const viewportHeight = window.innerHeight;
    const spaceAbove = rect.top;
    const spaceBelow = viewportHeight - (rect.top + rect.height);

    // Preferred placement: above if spaceAbove > 160 else below
    const placeAbove = spaceAbove > 160 || spaceAbove > spaceBelow;

    // Horizontal center over element, but keep inside viewport
    let left = rect.left + rect.width / 2 - TOOLTIP_MAX_WIDTH / 2 + window.scrollX;
    left = Math.max(VIEWPORT_PADDING + window.scrollX, Math.min(left, window.scrollX + window.innerWidth - TOOLTIP_MAX_WIDTH - VIEWPORT_PADDING));

    if (placeAbove) {
      // Place tooltip above the element with a small margin so it doesn't cover the highlight
      tooltipStyle.left = left;
      tooltipStyle.top = rect.top + window.scrollY - 18 - 160; // conservative offset
    } else {
      // Place below the element
      tooltipStyle.left = left;
      tooltipStyle.top = rect.top + window.scrollY + rect.height + 18; // small gap below
    }

    // Ensure top isn't negative
    if (typeof tooltipStyle.top === 'number') {
      tooltipStyle.top = Math.max(8 + window.scrollY, tooltipStyle.top as number);
    }

    tooltipStyle.width = TOOLTIP_MAX_WIDTH;
  } else {
    // center
    tooltipStyle.left = '50%';
    tooltipStyle.transform = 'translateX(-50%)';
    tooltipStyle.top = '20%';
    tooltipStyle.width = TOOLTIP_MAX_WIDTH;
  }

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {/* dark overlay */}
      <div className="absolute inset-0 bg-black/60" style={{ pointerEvents: 'auto' }} onClick={() => close(false)} />

      {/* highlight box */}
      {rect && (
        <div
          aria-hidden
          style={{
            position: 'absolute',
            left: rect.left + window.scrollX - 8,
            top: rect.top + window.scrollY - 8,
            width: rect.width + 16,
            height: rect.height + 16,
            borderRadius: 12,
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.6), 0 8px 24px rgba(0,0,0,0.4)',
            pointerEvents: 'none',
            transition: 'all 300ms ease',
            zIndex: 10001,
            border: '2px solid rgba(255,255,255,0.9)'
          }}
        />
      )}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        style={{
          position: 'absolute',
          zIndex: 10002,
          maxWidth: 360,
          ...tooltipStyle,
          pointerEvents: 'auto'
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22 }}
          className="bg-white rounded-2xl p-5 shadow-lg border border-gray-100"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              {step.title && <h3 className="text-lg font-bold text-gray-900">{step.title}</h3>}
              <div className="mt-2 text-sm text-gray-700">{step.content}</div>
            </div>
            <button onClick={() => close(false)} aria-label="Skip tour" className="text-gray-500 hover:text-gray-700 ml-2"><X size={18} /></button>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-2">
              <button onClick={back} disabled={index === 0} className={`px-3 py-2 rounded-lg ${index === 0 ? 'bg-gray-100 text-gray-400' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
                <ArrowLeft size={14} /> <span className="hidden sm:inline">Back</span>
              </button>
            </div>

            <div className="flex gap-2">
              <div className="text-xs text-gray-500 mr-2">Step {index + 1} of {steps.length}</div>
              <button onClick={next} className={`px-4 py-2 rounded-lg font-semibold text-white ${index === steps.length - 1 ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}`}>
                <span className="mr-2">{index === steps.length - 1 ? 'Get Started' : 'Next'}</span>
                {index === steps.length - 1 ? <CheckCircle size={16} /> : <ArrowRight size={16} />}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default AppTour;
