import { useEffect, useState } from "react";
import Lenis from "lenis";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import gsap from "gsap";
import { AnimatePresence, motion } from "framer-motion";
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import LandingScrollShowcase from "./components/LandingScrollShowcase";
import FeaturesSection from "./components/FeaturesSection";
import { api } from "./api/client.js";
import { initScrollAnimations } from "./animations/scrollAnimations.js";

gsap.registerPlugin(ScrollTrigger);

function App() {
  const [showEndPopup, setShowEndPopup] = useState(false);

  useEffect(() => {
    api.health().then((r) => console.log("Backend:", r.message)).catch(() => console.warn("Backend not reachable"));
  }, []);

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.1,
      smoothWheel: true,
      gestureOrientation: "vertical",
      touchMultiplier: 1.1,
      anchors: true,
    });

    let animationFrameId = 0;
    const teardownScrollAnimations = initScrollAnimations(document.body);

    const onLenisScroll = (event) => {
      const progress = event?.progress ?? 0;

      setShowEndPopup((current) => {
        const next = progress >= 0.985;
        return current === next ? current : next;
      });

      ScrollTrigger.update();
    };

    lenis.on("scroll", onLenisScroll);

    const updateScroll = (time) => {
      lenis.raf(time);
      animationFrameId = window.requestAnimationFrame(updateScroll);
    };

    animationFrameId = window.requestAnimationFrame(updateScroll);
    ScrollTrigger.refresh();

    return () => {
      window.cancelAnimationFrame(animationFrameId);
      lenis.off("scroll", onLenisScroll);
      teardownScrollAnimations();
      lenis.destroy();
    };
  }, []);

  return (
    <div>
      <Navbar />
      <div style={{ filter: "brightness(0.85)" }}>
        <HeroSection />
        <LandingScrollShowcase />
        <FeaturesSection />
      </div>

      <AnimatePresence>
        {showEndPopup && (
          <motion.div
            className="end-popup-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
          >
            <motion.div
              className="end-popup-card"
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            >
              <p className="end-popup-label">Journey Complete</p>
              <h3 className="end-popup-title">Start the monitoring system</h3>
              <p className="end-popup-text">You reached the end of the landing page. Launch the live dashboard now.</p>
              <button
                type="button"
                onClick={() => {
                  window.location.href = "http://localhost:8501";
                }}
                className="end-popup-button"
              >
                Start System
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
