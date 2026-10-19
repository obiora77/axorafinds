import type { App } from 'vue'
import { MotionPlugin } from '@vueuse/motion'
import gsap from 'gsap'

/*
 * Motion rules for the whole app:
 *  - VueUse Motion (v-motion): hero entrance, scroll reveals, button hover.
 *  - Vue <Transition>/<TransitionGroup>: route changes and the property grid.
 *  - GSAP: listing-card stagger, the inspection/account modal, the success states.
 * Durations stay between 150 and 250ms, ease-out, and everything is skipped when the
 * visitor prefers reduced motion.
 */

const DURATION_MS = 200
const EASE = 'easeOut'

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

/** Hero entrance. Use as: v-motion v-bind="heroIn(120)" */
export function heroIn(delayMs = 0) {
  if (prefersReducedMotion()) return { initial: { opacity: 1, y: 0 }, enter: { opacity: 1, y: 0 } }
  return {
    initial: { opacity: 0, y: 18 },
    enter: { opacity: 1, y: 0, transition: { duration: DURATION_MS, delay: delayMs, ease: EASE } },
  }
}

/** Scroll reveal, plays once. Use as: v-motion v-bind="reveal()" */
export function reveal(delayMs = 0) {
  if (prefersReducedMotion()) return { initial: { opacity: 1, y: 0 }, visibleOnce: { opacity: 1, y: 0 } }
  return {
    initial: { opacity: 0, y: 14 },
    visibleOnce: { opacity: 1, y: 0, transition: { duration: DURATION_MS, delay: delayMs, ease: EASE } },
  }
}

/** Button hover and press. Use as: v-motion v-bind="buttonMotion()" */
export function buttonMotion() {
  if (prefersReducedMotion()) return { initial: { scale: 1 }, enter: { scale: 1 } }
  const transition = { duration: 150, ease: EASE }
  return {
    initial: { scale: 1 },
    enter: { scale: 1 },
    hovered: { scale: 1.03, transition },
    tapped: { scale: 0.97, transition },
  }
}

/** GSAP enter hooks for <TransitionGroup :css="false"> on the listing grid (staggered by data-index). */
export const gridStagger = {
  onBeforeEnter(el: Element): void {
    if (!prefersReducedMotion()) gsap.set(el, { opacity: 0, y: 14 })
  },
  onEnter(el: Element, done: () => void): void {
    if (prefersReducedMotion()) {
      done()
      return
    }
    const index = Number((el as HTMLElement).dataset.index ?? 0)
    gsap.to(el, {
      opacity: 1,
      y: 0,
      duration: 0.22,
      delay: Math.min(index, 8) * 0.04,
      ease: 'power2.out',
      clearProps: 'opacity,transform',
      onComplete: done,
    })
  },
}

export default {
  install(app: App): void {
    app.use(MotionPlugin)
  },
}
