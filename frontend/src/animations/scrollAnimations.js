import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function initScrollAnimations(rootElement) {
  const ctx = gsap.context(() => {
    const sectionFadeElements = gsap.utils.toArray("[data-section-fade]");
    const fadeUpElements = gsap.utils.toArray("[data-animate='fade-up']");
    const popUpElements = gsap.utils.toArray("[data-animate='pop-up']");
    const slideRightElements = gsap.utils.toArray("[data-animate='slide-right']");
    const staggerGroups = gsap.utils.toArray("[data-stagger]");
    const buildReplayTrigger = (trigger, start) => ({
      trigger,
      start,
      once: false,
      toggleActions: "restart none restart reset",
    });

    sectionFadeElements.forEach((element) => {
      gsap.fromTo(
        element,
        { opacity: 0.24 },
        {
          opacity: 1,
          duration: 0.9,
          ease: "power2.out",
          scrollTrigger: buildReplayTrigger(element, "top 88%"),
        }
      );
    });

    fadeUpElements.forEach((element) => {
      gsap.fromTo(
        element,
        { y: 36, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.75,
          ease: "power3.out",
          scrollTrigger: buildReplayTrigger(element, "top 84%"),
        }
      );
    });

    popUpElements.forEach((element) => {
      gsap.fromTo(
        element,
        {
          y: 88,
          scale: 0.78,
          opacity: 0,
          transformOrigin: "50% 50%",
          force3D: true,
        },
        {
          y: 0,
          scale: 1,
          opacity: 1,
          duration: 1.02,
          ease: "back.out(1.28)",
          scrollTrigger: buildReplayTrigger(element, "top 88%"),
        }
      );
    });

    slideRightElements.forEach((element) => {
      gsap.fromTo(
        element,
        { x: 56, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.85,
          ease: "power3.out",
          scrollTrigger: buildReplayTrigger(element, "top 82%"),
        }
      );
    });

    staggerGroups.forEach((group) => {
      const items = group.querySelectorAll("[data-stagger-item]");
      if (!items.length) {
        return;
      }

      gsap.fromTo(
        items,
        { y: 28, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.58,
          stagger: 0.12,
          ease: "power3.out",
          scrollTrigger: buildReplayTrigger(group, "top 84%"),
        }
      );
    });
  }, rootElement);

  return () => {
    ctx.revert();
  };
}