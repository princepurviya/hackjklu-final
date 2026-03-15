import { useRef, useState } from "react";
import { motion } from "framer-motion";
import ContactModal from "./ContactModal.jsx";

const features = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    title: "Deep Learning Models",
    description:
      "YOLO, Faster R-CNN, and SSD models trained on real-world damage datasets for high-accuracy detection.",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    title: "Real-Time Processing",
    description:
      "Process images instantly and receive bounding-box annotations with class labels and confidence scores.",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    title: "Heritage Protection",
    description:
      "Early detection of cracks, potholes, and structural damage helps preserve cultural and historical sites.",
  },
];

export default function FeaturesSection() {
  const ref = useRef(null);
  const [showContact, setShowContact] = useState(false);

  return (
    <section
      id="features"
      ref={ref}
      data-section-fade
      className="relative w-full py-24 sm:py-32 lg:py-36"
      style={{ background: "linear-gradient(145deg, #0e0e16 0%, #0a0d1f 40%, #0c1218 70%, #0e0e16 100%)" }}
    >

      <div className="relative layout-container tech-section" style={{ background: "transparent" }}>
        {/* header */}
        <div
          data-animate="fade-up"
          className="tech-header"
        >
          <span className="tech-kicker">
            Technology
          </span>

          <h2 className="tech-title">
            Built with Cutting-Edge{" "}
            <span className="bg-gradient-to-r from-[#c9a84c] to-[#e8c547] bg-clip-text text-transparent">
              Technology
            </span>
          </h2>

          <div className="tech-subtitle-wrap">
            <p className="tech-subtitle">
              Powered by state-of-the-art deep learning architectures trained on
              diverse real-world datasets.
            </p>
          </div>
        </div>

        {/* feature cards */}
        <div
          data-stagger
          className="tech-grid"
        >
          {features.map((feat) => (
            <div
              key={feat.title}
              data-stagger-item
              className="tech-card"
            >
              <div className="tech-card-icon">
                {feat.icon}
              </div>
              <h3 className="tech-card-title">
                {feat.title}
              </h3>
              <p className="tech-card-description">
                {feat.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* footer */}
      <footer className="footer-shell">
        <div className="footer-backdrop" />
        <div className="footer-watermark" aria-hidden="true">
          <p>AI-Monitoring</p>
        </div>

        <div className="footer-container">
          <div className="footer-inner">
            <div className="footer-grid">
              <div className="footer-brand">
                <div className="footer-logo-wrap">
                  <svg className="footer-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M4 7.5L12 3l8 4.5v9L12 21l-8-4.5v-9z" />
                    <path d="M8.5 10.5h7M10.5 13.5h3" strokeLinecap="round" />
                  </svg>
                </div>

                <p className="footer-description">
                  Elegant monitoring for galleries and museums, with a footer treatment that stays minimal while feeling more premium.
                </p>

                <div className="footer-socials">
                {[
                  ["Instagram", "M7 2h10a5 5 0 015 5v10a5 5 0 01-5 5H7a5 5 0 01-5-5V7a5 5 0 015-5zm5 5.5A5.5 5.5 0 1112 18.5 5.5 5.5 0 0112 7.5zm6.25-.95a1.25 1.25 0 11-1.25-1.25 1.25 1.25 0 011.25 1.25z"],
                  ["LinkedIn", "M6.5 8.5h-3v9h3v-9zm-1.5-1.7a1.7 1.7 0 100-3.4 1.7 1.7 0 000 3.4zM10 8.5h2.85v1.23h.04c.4-.75 1.37-1.53 2.82-1.53 3.02 0 3.58 1.98 3.58 4.56v4.74h-3v-4.2c0-1-.02-2.28-1.39-2.28-1.39 0-1.6 1.08-1.6 2.2v4.28h-3v-9z"],
                  ["Discord", "M8.4 5.8a9.7 9.7 0 017.2 0l.35.85c1.7.12 2.95.78 3.83 1.63 0 0-.32 4.46-2.9 7.1-.72.75-1.85 1.5-3.52 1.95l-.47-.95c.78-.23 1.43-.54 1.97-.9-.23.16-1.53.92-2.9.92-1.37 0-2.67-.76-2.9-.92.54.36 1.2.67 1.97.9l-.47.95c-1.67-.45-2.8-1.2-3.52-1.95-2.58-2.64-2.9-7.1-2.9-7.1.88-.85 2.13-1.5 3.83-1.63l.41-.85zm1.63 7.67c.72 0 1.3-.66 1.3-1.48 0-.82-.58-1.48-1.3-1.48-.72 0-1.3.66-1.3 1.48 0 .82.58 1.48 1.3 1.48zm3.94 0c.72 0 1.3-.66 1.3-1.48 0-.82-.58-1.48-1.3-1.48-.72 0-1.3.66-1.3 1.48 0 .82.58 1.48 1.3 1.48z"],
                  ["YouTube", "M23 12s0-3.2-.4-4.7a2.8 2.8 0 00-2-2C19 5 12 5 12 5s-7 0-8.6.3a2.8 2.8 0 00-2 2C1 8.8 1 12 1 12s0 3.2.4 4.7a2.8 2.8 0 002 2C5 19 12 19 12 19s7 0 8.6-.3a2.8 2.8 0 002-2c.4-1.5.4-4.7.4-4.7zM10 15.5v-7l6 3.5-6 3.5z"],
                  ["X", "M4 3h4.2l3.26 4.7L15.8 3H20l-6.43 7.2L20.7 21h-4.2l-3.72-5.32L8.2 21H4l6.9-7.72L4 3z"],
                ].map(([label, path]) => (
                  <a
                    key={label}
                    href="#"
                    aria-label={label}
                    className="footer-social-link"
                  >
                    <svg viewBox="0 0 24 24" className="footer-social-icon" fill="currentColor">
                      <path d={path} />
                    </svg>
                  </a>
                ))}
              </div>
              </div>

              <div className="footer-group">
                <h4 className="footer-heading">ABOUT</h4>
                <ul className="footer-list">
                  <li><a href="#" className="footer-link">About Us</a></li>
                  <li><a href="#" className="footer-link">Support</a></li>
                  <li><a href="#" className="footer-link">Terms and Condition</a></li>
                  <li><a href="#" className="footer-link">Privacy Policy</a></li>
                  <li><button type="button" onClick={() => setShowContact(true)} className="footer-link footer-button">Submit Projects</button></li>
                </ul>
              </div>

              <div className="footer-group">
                <h4 className="footer-heading">COMPANY</h4>
                <ul className="footer-list">
                  <li><a href="#" className="footer-link">Hire From Us</a></li>
                  <li><a href="#" className="footer-link">Discord</a></li>
                  <li><a href="#" className="footer-link">Pricing and Refund</a></li>
                  <li><a href="#" className="footer-link">Jobs</a></li>
                  <li><a href="#" className="footer-link">Feedback</a></li>
                </ul>
              </div>

              <div className="footer-group">
                <h4 className="footer-heading">CONTACT</h4>
                <ul className="footer-list footer-contact-list">
                  <li className="footer-text">Online: 11am - 8pm</li>
                  <li className="footer-text">+91 9993478545</li>
                  <li className="footer-text">Offline: 11am - 8pm</li>
                  <li className="footer-text">+91 9691778470</li>
                  <li className="footer-text">hello@museummonitor.ai</li>
                  <li className="footer-text">Indrapuri, Bhopal (MP)</li>
                </ul>
              </div>
            </div>

            <ContactModal isOpen={showContact} onClose={() => setShowContact(false)} />

            <div className="footer-bottom">
              <p>© 2026 AI-Powered Exhibit Monitoring System</p>
            </div>
          </div>
        </div>
      </footer>
    </section>
  );
}
