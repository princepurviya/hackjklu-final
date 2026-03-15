import { useState } from "react";
import { motion } from "framer-motion";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] } },
});

export default function HeroSection() {
  const [starting, setStarting] = useState(false);

  const handleStartSystem = () => {
    if (starting) return;
    setStarting(true);
    window.location.href = "http://localhost:8501";
    setTimeout(() => setStarting(false), 1000);
  };

  return (
    <section
      className="hero-shell"
      style={{ background: "linear-gradient(135deg, #0a0a0f 0%, #0d0b1e 40%, #091018 70%, #0a0a0f 100%)" }}
    >
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          zIndex: 0,
          filter: 'brightness(0.5)',
        }}
        onError={(e) => console.warn('Video background failed to load', e)}
      >
        <source src="/videos/background.mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "linear-gradient(135deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.5) 50%, rgba(0,0,0,0.75) 100%)",
        }}
      />

      <div className="hero-content-wrap">
        {/* badge */}
        <motion.div {...fadeUp(0)} className="hero-badge-wrap" data-animate="fade-up">
          <span className="hero-badge">
            <span className="hero-badge-dot" />
            AI-Powered Exhibit Monitoring
          </span>
        </motion.div>

        {/* title */}
        <motion.h1
          {...fadeUp(0.15)}
          className="hero-title"
          data-animate="fade-up"
        >
          <span className="block">AI-Powered Exhibit</span>
          <span className="hero-title-accent">Monitoring</span>
        </motion.h1>

        {/* subtitle */}
        <div className="hero-subtitle-wrap" data-animate="fade-up">
          <motion.p
            {...fadeUp(0.3)}
            className="hero-subtitle"
          >
            A comprehensive deep-learning solution designed specifically for the unique
            environment and challenges of preserving historical artifacts.
          </motion.p>
        </div>

        <motion.div {...fadeUp(0.45)} className="hero-cta-wrap" data-animate="fade-up">
          <button
            type="button"
            onClick={handleStartSystem}
            disabled={starting}
            className="hero-cta-button hover-scale-button"
          >
            {starting ? "Starting..." : "Start System"}
          </button>
        </motion.div>
      </div>

      {/* scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="hero-scroll-indicator"
      >
        <div className="hero-scroll-track">
          <motion.div
            animate={{ y: [0, 9, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className="hero-scroll-dot"
          />
        </div>
      </motion.div>
    </section>
  );
}
