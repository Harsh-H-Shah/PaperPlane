'use client';

import { useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// Register plugin once
if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

/**
 * Custom hook to initialize GSAP ScrollTrigger animations.
 * Targets elements with `data-gsap` attribute inside a scrollable container.
 *
 * Supported `data-gsap` values:
 * - "fade-up"       → fade in + slide up
 * - "fade-down"     → fade in + slide down
 * - "fade-left"     → fade in + slide from left
 * - "fade-right"    → fade in + slide from right
 * - "scale-in"      → fade in + scale from 0.85
 * - "stagger"       → parent: children animate in sequence
 */
export function useGsapScroll(scrollerSelector?: string) {
  useEffect(() => {
    // Small delay to ensure DOM is ready after React hydration
    const timeout = setTimeout(() => {
      const scroller = scrollerSelector
        ? document.querySelector(scrollerSelector)
        : undefined;

      // Individual element animations
      const elements = document.querySelectorAll('[data-gsap]');
      const animations: gsap.core.Tween[] = [];

      elements.forEach((el) => {
        const type = el.getAttribute('data-gsap');
        const delay = parseFloat(el.getAttribute('data-gsap-delay') || '0');

        const baseConfig: gsap.TweenVars = {
          duration: 0.8,
          ease: 'power3.out',
          delay,
          scrollTrigger: {
            trigger: el,
            start: 'top 90%',
            end: 'bottom 10%',
            toggleActions: 'play none none none',
            ...(scroller ? { scroller } : {}),
          },
        };

        let fromConfig: gsap.TweenVars = {};

        switch (type) {
          case 'fade-up':
            fromConfig = { opacity: 0, y: 40 };
            break;
          case 'fade-down':
            fromConfig = { opacity: 0, y: -40 };
            break;
          case 'fade-left':
            fromConfig = { opacity: 0, x: -60 };
            break;
          case 'fade-right':
            fromConfig = { opacity: 0, x: 60 };
            break;
          case 'scale-in':
            fromConfig = { opacity: 0, scale: 0.85 };
            break;
          case 'fade-in':
            fromConfig = { opacity: 0 };
            break;
          default:
            fromConfig = { opacity: 0, y: 30 };
        }

        const tween = gsap.from(el, { ...fromConfig, ...baseConfig });
        animations.push(tween);
      });

      // Stagger groups: parent has data-gsap="stagger", children get animated
      const staggerParents = document.querySelectorAll('[data-gsap="stagger"]');
      staggerParents.forEach((parent) => {
        const children = parent.children;
        if (children.length === 0) return;

        const tween = gsap.from(Array.from(children), {
          opacity: 0,
          y: 30,
          duration: 0.6,
          stagger: 0.1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: parent,
            start: 'top 85%',
            toggleActions: 'play none none none',
            ...(scroller ? { scroller } : {}),
          },
        });
        animations.push(tween);
      });
    }, 100);

    return () => {
      clearTimeout(timeout);
      ScrollTrigger.getAll().forEach((st) => st.kill());
    };
  }, [scrollerSelector]);
}

/**
 * Hook for parallax background effect.
 * Moves background layers at different speeds relative to scroll.
 */
export function useParallax() {
  useEffect(() => {
    const timeout = setTimeout(() => {
      const layers = document.querySelectorAll('[data-parallax]');

      layers.forEach((layer) => {
        const speed = parseFloat(layer.getAttribute('data-parallax-speed') || '0.5');

        gsap.to(layer, {
          yPercent: speed * 20,
          ease: 'none',
          scrollTrigger: {
            trigger: document.body,
            start: 'top top',
            end: 'bottom bottom',
            scrub: 1,
          },
        });
      });
    }, 200);

    return () => {
      clearTimeout(timeout);
      ScrollTrigger.getAll().forEach((st) => st.kill());
    };
  }, []);
}
