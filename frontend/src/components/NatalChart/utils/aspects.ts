import type { AspectType } from "../types";

export interface AspectStyle {
  stroke: string; // CSS custom-property reference
  dasharray?: string; // SVG stroke-dasharray, when applicable
  opacity: number;
}

export function getAspectStyle(type: AspectType): AspectStyle {
  // Каждый тип аспекта — отдельный цвет (раньше conjunction и trine оба были на
  // --natal-accent → неразличимы). Цвета согласованы с PDF (ASPECT_COLORS в
  // natal_pdf_html.py): соединение — золото, трин — зелёный, секстиль — лайм,
  // квадрат — синий, оппозиция — красный.
  switch (type) {
    case "conjunction":
      return { stroke: "var(--natal-accent)", opacity: 0.85 };
    case "trine":
      return { stroke: "#1fa37c", opacity: 0.85 };
    case "sextile":
      return { stroke: "#96d957", opacity: 0.6, dasharray: "3 4" };
    case "square":
      return { stroke: "#398ada", opacity: 0.85 };
    case "opposition":
      return { stroke: "#ff585f", opacity: 0.85 };
  }
}
