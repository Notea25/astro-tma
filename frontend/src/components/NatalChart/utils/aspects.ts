import type { AspectType } from '../types';

export interface AspectStyle {
  stroke: string;      // CSS custom-property reference
  dasharray?: string;  // SVG stroke-dasharray, when applicable
  opacity: number;
}

export function getAspectStyle(type: AspectType): AspectStyle {
  switch (type) {
    case 'conjunction': return { stroke: 'var(--natal-accent)',    opacity: 0.8 };
    case 'opposition':  return { stroke: 'var(--natal-primary)',   opacity: 0.8 };
    case 'trine':       return { stroke: 'var(--natal-accent)',    opacity: 0.8 };
    case 'square':      return { stroke: 'var(--natal-secondary)', opacity: 0.8 };
    case 'sextile':     return { stroke: 'var(--natal-dim)',       opacity: 0.5, dasharray: '3 4' };
  }
}
