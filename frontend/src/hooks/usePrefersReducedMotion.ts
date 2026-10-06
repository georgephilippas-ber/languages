import { useReducedMotion } from 'motion/react'

export function useScrollBehavior(): ScrollBehavior {
  return useReducedMotion() ? 'auto' : 'smooth'
}
