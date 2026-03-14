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
      className="relative min-h-screen flex items-center justify-center overflow-hidden pt-10 sm:pt-16 md:pt-24 pb-16 md:pb-24"
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

      <div className="relative w-full max-w-4xl mx-auto text-center px-6">
        {/* badge */}
        <motion.div {...fadeUp(0)} className="mb-4">
          <span className="inline-flex items-center gap-2.5 px-6 py-2.5 rounded-full text-xs sm:text-sm font-semibold tracking-[0.14em] uppercase bg-[#c9a84c]/[0.08] text-[#c9a84c] border border-[#c9a84c]/15">
            <span className="w-1.5 h-1.5 rounded-full bg-[#c9a84c] animate-pulse" />
            AI-Powered Exhibit Monitoring
          </span>
        </motion.div>

        {/* title */}
        <motion.h1
          {...fadeUp(0.15)}
          className="text-4xl sm:text-6xl lg:text-[4.8rem] font-extrabold text-white leading-[1.1] tracking-tight"
        >
          <span className="block">Protecting Heritage</span>
          <span className="block mt-2 text-3xl sm:text-5xl lg:text-[4.3rem] leading-[1.1]">with{" "}
            <span className="bg-gradient-to-r from-[#c9a84c] via-[#e8c547] to-[#d4a843] bg-clip-text text-transparent">
              Artificial Intelligence
            </span>
          </span>
        </motion.h1>

        {/* subtitle */}
        <div className="mt-6 mb-8 sm:mb-12 flex justify-center">
          <motion.p
            {...fadeUp(0.3)}
            className="w-full max-w-[680px] text-base sm:text-lg lg:text-[1.16rem] text-[#8a8480] leading-[1.7] px-4"
          >
            Advanced computer vision monitors museum exhibits 24/7, detecting
            damage, misplacement, and structural deterioration before it&#39;s too
            late.
          </motion.p>
        </div>

        <motion.div {...fadeUp(0.45)} className="flex justify-center">
          <button
            type="button"
            onClick={handleStartSystem}
            disabled={starting}
            className="inline-flex items-center justify-center min-w-[180px] px-8 py-3.5 rounded-full bg-gradient-to-r from-[#c9a84c] to-[#e8c547] text-[#0a0a0f] font-bold text-sm tracking-wide shadow-lg shadow-[#c9a84c]/20 hover:shadow-xl hover:shadow-[#c9a84c]/30 hover:-translate-y-0.5 transition-all duration-300"
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
        className="absolute bottom-10 left-1/2 -translate-x-1/2"
      >
        <div className="w-7 h-11 rounded-full border-2 border-white/15 flex justify-center pt-2.5">
          <motion.div
            animate={{ y: [0, 9, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className="w-1.5 h-1.5 rounded-full bg-[#c9a84c]"
          />
        </div>
      </motion.div>
    </section>
  );
}
