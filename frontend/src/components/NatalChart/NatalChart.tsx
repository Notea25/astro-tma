import { useEffect, useId, useRef, useState } from 'react';
import clsx from 'clsx';
import type { NatalChartProps } from './types';
import styles from './NatalChart.module.css';
import { TopFrame } from './parts/TopFrame';
import { Header } from './parts/Header';
import { CornerMetadata } from './parts/CornerMetadata';
import { SideFigure } from './parts/SideFigure';
import { ChartWheel } from './parts/ChartWheel';
import { BottomFrame } from './parts/BottomFrame';
import { formatBirthDate } from './utils/formatting';

/** Below this rendered width, collapse to a wheel-only layout — side figures
 *  otherwise crowd the wheel and lose legibility. */
const COMPACT_WIDTH = 400;

/**
 * Natal chart SVG. viewBox is fixed at 1000×1400; `size` controls the
 * rendered width and the browser scales the rest to match.
 */
export function NatalChart(props: NatalChartProps) {
  const {
    data,
    theme = 'midnight-gold',
    size = 800,
    title = 'NATAL',
    showDecorative = true,
    showSideFigures = true,
    className,
    onPlanetClick,
    onHouseClick,
  } = props;

  const svgRef = useRef<SVGSVGElement | null>(null);
  const [compact, setCompact] = useState(false);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const el = svgRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      setCompact(w > 0 && w < COMPACT_WIDTH);
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const effectiveSideFigures = showSideFigures && !compact;

  const subject = data.name ? ` for ${data.name}` : '';
  const dateReadable = formatBirthDate(data.birthDate);
  const ariaLabel = `Natal chart${subject}, born ${dateReadable} at ${data.birthTime} in ${data.birthLocation.city}, ${data.birthLocation.country}.`;
  const ariaDesc = `Sun in ${data.sun.sign}, ascendant in ${data.ascendant.sign}, midheaven in ${data.midheaven.sign}.`;

  return (
    <svg
      ref={svgRef}
      className={clsx(styles.root, className)}
      data-theme={theme}
      role="img"
      aria-labelledby={titleId}
      aria-describedby={descId}
      viewBox="0 0 1000 1400"
      width={size}
      style={{ maxWidth: '100%', height: 'auto', aspectRatio: '1000 / 1400' }}
    >
      <title id={titleId}>{ariaLabel}</title>
      <desc id={descId}>{ariaDesc}</desc>

      <rect width={1000} height={1400} fill="var(--natal-bg)" />

      {showDecorative && <TopFrame />}

      <Header
        title={title}
        birthDate={data.birthDate}
        birthTime={data.birthTime}
        birthLocation={data.birthLocation}
      />

      <CornerMetadata sun={data.sun} ascendant={data.ascendant} />

      {effectiveSideFigures && <SideFigure sign={data.sun.sign}       side="left"  />}
      {effectiveSideFigures && <SideFigure sign={data.ascendant.sign} side="right" />}

      <ChartWheel
        data={data}
        onPlanetClick={onPlanetClick}
        onHouseClick={onHouseClick}
      />

      {showDecorative && <BottomFrame />}
    </svg>
  );
}
