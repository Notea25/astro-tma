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
import { PosterBackdrop } from './parts/PosterBackdrop';
import { ZODIAC_LABEL } from './constants';
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
    variant = 'editorial',
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
  const isPoster = variant === 'zodiac-poster';

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

  const subject = data.name ? ` для ${data.name}` : '';
  const dateReadable = formatBirthDate(data.birthDate);
  const ariaLabel = `Натальная карта${subject}: рождение ${dateReadable} в ${data.birthTime}, ${data.birthLocation.city}, ${data.birthLocation.country}.`;
  const ariaDesc = `Солнце в знаке ${ZODIAC_LABEL[data.sun.sign]}, асцендент в знаке ${ZODIAC_LABEL[data.ascendant.sign]}, середина неба в знаке ${ZODIAC_LABEL[data.midheaven.sign]}.`;
  const viewBox = isPoster ? '0 0 1000 1000' : '0 0 1000 1400';
  const aspectRatio = isPoster ? '1 / 1' : '1000 / 1400';

  return (
    <svg
      ref={svgRef}
      className={clsx(styles.root, isPoster && styles.posterRoot, className)}
      data-theme={theme}
      data-variant={variant}
      role="img"
      aria-labelledby={titleId}
      aria-describedby={descId}
      viewBox={viewBox}
      width={size}
      style={{ maxWidth: '100%', height: 'auto', aspectRatio }}
    >
      <title id={titleId}>{ariaLabel}</title>
      <desc id={descId}>{ariaDesc}</desc>

      {isPoster ? (
        <PosterBackdrop />
      ) : (
        <rect width={1000} height={1400} fill="var(--natal-bg)" />
      )}

      {!isPoster && showDecorative && <TopFrame />}

      {!isPoster && (
        <Header
          title={title}
          birthDate={data.birthDate}
          birthTime={data.birthTime}
          birthLocation={data.birthLocation}
        />
      )}

      {!isPoster && <CornerMetadata sun={data.sun} ascendant={data.ascendant} />}

      {!isPoster && effectiveSideFigures && <SideFigure sign={data.sun.sign}       side="left"  />}
      {!isPoster && effectiveSideFigures && <SideFigure sign={data.ascendant.sign} side="right" />}

      <g transform={isPoster ? 'translate(0 -320)' : undefined}>
        <ChartWheel
          data={data}
          variant={variant}
          onPlanetClick={onPlanetClick}
          onHouseClick={onHouseClick}
        />
      </g>

      {!isPoster && showDecorative && <BottomFrame />}
    </svg>
  );
}
