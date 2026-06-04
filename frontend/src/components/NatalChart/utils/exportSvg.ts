/**
 * Serialize a live <NatalChart> SVG into a self-contained string for the PDF
 * backend. The live SVG relies on CSS custom properties (--natal-*) and CSS
 * module classes for colour, and references zodiac glyphs via external
 * <image href="/zodiac-glyphs/*.svg">. Neither survives a raw outerHTML, so we
 * resolve computed paint to inline attributes and inline the glyphs as data
 * URIs.
 */

const PAINT_PROPS = [
  "fill",
  "stroke",
  "stroke-width",
  "stroke-opacity",
  "fill-opacity",
  "opacity",
  "stroke-dasharray",
  "stroke-linecap",
  "stroke-linejoin",
  "color",
  "mix-blend-mode",
] as const;

const glyphCache = new Map<string, string>();

async function fetchGlyphDataUri(url: string): Promise<string | null> {
  const cached = glyphCache.get(url);
  if (cached !== undefined) return cached;
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const text = await res.text();
    const dataUri = `data:image/svg+xml;utf8,${encodeURIComponent(text)}`;
    glyphCache.set(url, dataUri);
    return dataUri;
  } catch {
    return null;
  }
}

/**
 * Walk the live element tree and the clone tree in lockstep, copying each
 * live node's *computed* paint onto the matching clone node as inline style.
 * This captures both CSS-variable values and CSS-class rules without shipping
 * any stylesheet.
 */
function inlineComputedPaint(liveEl: Element, cloneEl: Element): void {
  if (liveEl instanceof SVGElement || liveEl instanceof HTMLElement) {
    const computed = window.getComputedStyle(liveEl);
    const decls: string[] = [];
    for (const prop of PAINT_PROPS) {
      const value = computed.getPropertyValue(prop);
      if (value && value !== "normal" && value !== "auto") {
        decls.push(`${prop}:${value}`);
      }
    }
    if (decls.length) {
      const existing = cloneEl.getAttribute("style");
      cloneEl.setAttribute(
        "style",
        existing ? `${existing};${decls.join(";")}` : decls.join(";"),
      );
    }
    // Drop class refs — their rules are now inlined, and the backend has no CSS.
    cloneEl.removeAttribute("class");
  }

  const liveChildren = liveEl.children;
  const cloneChildren = cloneEl.children;
  for (let i = 0; i < liveChildren.length; i += 1) {
    const cloneChild = cloneChildren[i];
    if (cloneChild) inlineComputedPaint(liveChildren[i], cloneChild);
  }
}

const SVG_NS = "http://www.w3.org/2000/svg";
const XLINK_NS = "http://www.w3.org/1999/xlink";

/** Replace external glyph <image> hrefs with inline data URIs. */
async function inlineGlyphImages(clone: SVGSVGElement): Promise<void> {
  const images = Array.from(clone.querySelectorAll("image"));
  await Promise.all(
    images.map(async (img) => {
      const href =
        img.getAttribute("href") || img.getAttributeNS(XLINK_NS, "href");
      if (!href || href.startsWith("data:")) return;
      // Resolve relative to the document so fetch works regardless of base.
      const abs = new URL(href, window.location.origin).toString();
      const dataUri = await fetchGlyphDataUri(abs);
      if (!dataUri) return;
      img.setAttribute("href", dataUri);
      img.removeAttributeNS(XLINK_NS, "href");
    }),
  );
}

/**
 * Produce a fully self-contained SVG string (literal colours, inlined glyphs)
 * that the PDF backend can embed verbatim.
 */
export async function serializeWheelSvg(
  liveSvg: SVGSVGElement,
): Promise<string> {
  const clone = liveSvg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", SVG_NS);
  clone.setAttribute("xmlns:xlink", XLINK_NS);

  inlineComputedPaint(liveSvg, clone);
  await inlineGlyphImages(clone);

  // Strip interactivity / handlers that would not serialize meaningfully.
  clone
    .querySelectorAll("[data-part]")
    .forEach((el) => el.removeAttribute("data-part"));

  return new XMLSerializer().serializeToString(clone);
}
