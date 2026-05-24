import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { motion } from "framer-motion";
import {
  SPREAD_CONFIG,
  CARD_W,
  CARD_H,
  type SpreadKey,
} from "@/data/spread-config";

interface Props {
  spreadKey: SpreadKey;
  onStart: () => void;
}

const SCALE_BY_KEY: Record<SpreadKey, number> = {
  three_card: 0.9,
  celtic_cross: 1.08,
  week: 1.14,
  relationship: 1.0,
};

function ThreeCardIntro({ onStart }: { onStart: () => void }) {
  const config = SPREAD_CONFIG.three_card;
  const positions = config.sections[0]?.positions ?? [];

  return (
    <motion.div
      className="spread-intro-v2 spread-intro-v2--showcase spread-intro-v2--three_card spread-intro-v2--three-ref"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h1 className="spread-intro-v2__title spread-intro-v2__title--three">
        {config.title}
      </h1>

      <div className="spread-intro-v2__three-preview">
        {positions.map((pos) => (
          <div key={pos.num} className="spread-intro-v2__back-card">
            <div className="spread-intro-v2__back-badge">{pos.num}</div>
          </div>
        ))}
      </div>

      <div className="spread-intro-v2__frame spread-intro-v2__frame--three">
        <p
          className="spread-intro-v2__story"
          dangerouslySetInnerHTML={{ __html: config.intro }}
        />
      </div>

      <motion.button
        className="btn-primary spread-intro-v2__start-btn"
        onClick={onStart}
        whileTap={{ scale: 0.96 }}
      >
        Перейти к раскладу
      </motion.button>
    </motion.div>
  );
}

export function SpreadIntro({ spreadKey, onStart }: Props) {
  const [titleScale, setTitleScale] = useState(1);
  const titleWrapRef = useRef<HTMLHeadingElement>(null);
  const titleMeasureRef = useRef<HTMLSpanElement>(null);

  const config = SPREAD_CONFIG[spreadKey];
  const { layout, title } = config;
  const scale = SCALE_BY_KEY[spreadKey] ?? 1.0;
  const previewW = layout.w * scale;
  const previewH = layout.h * scale;
  const cardW = CARD_W * scale;
  const cardH = CARD_H * scale;
  const titleStyle = {
    "--spread-title-scale": titleScale,
  } as CSSProperties;

  useLayoutEffect(() => {
    const titleWrap = titleWrapRef.current;
    const titleMeasure = titleMeasureRef.current;
    if (!titleWrap || !titleMeasure) return;

    let frame = 0;
    const updateScale = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const availableWidth = titleWrap.clientWidth;
        const naturalWidth = titleMeasure.scrollWidth;
        const nextScale =
          availableWidth > 0 && naturalWidth > 0
            ? Math.min(1, availableWidth / naturalWidth)
            : 1;

        setTitleScale((current) =>
          Math.abs(current - nextScale) > 0.005 ? nextScale : current,
        );
      });
    };

    updateScale();
    window.addEventListener("resize", updateScale);

    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(updateScale)
        : null;
    resizeObserver?.observe(titleWrap);
    resizeObserver?.observe(titleMeasure);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", updateScale);
      resizeObserver?.disconnect();
    };
  }, [title]);

  if (spreadKey === "three_card") {
    return <ThreeCardIntro onStart={onStart} />;
  }

  return (
    <motion.div
      className={`spread-intro-v2 spread-intro-v2--showcase spread-intro-v2--${spreadKey}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h1
        ref={titleWrapRef}
        className="spread-intro-v2__title"
        style={titleStyle}
      >
        <span className="spread-intro-v2__title-text">{title}</span>
        <span
          ref={titleMeasureRef}
          className="spread-intro-v2__title-measure"
          aria-hidden="true"
        >
          {title}
        </span>
      </h1>

      <div className="spread-intro-v2__preview spread-intro-v2__preview--ornament">
        <div
          className="spread-intro-v2__preview-stage"
          style={{ width: previewW, height: previewH }}
        >
          {layout.slots.map((slot, idx) => (
            <div
              key={idx}
              className="spread-intro-v2__back-card spread-intro-v2__back-card--positioned"
              style={{
                left: slot.x * scale,
                top: slot.y * scale,
                width: cardW,
                height: cardH,
                ...(slot.rotate
                  ? { transform: `rotate(${slot.rotate}deg)` }
                  : {}),
              }}
            >
              <div className="spread-intro-v2__back-badge">{idx + 1}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="spread-intro-v2__frame">
        <p
          className="spread-intro-v2__story"
          dangerouslySetInnerHTML={{ __html: config.intro }}
        />
      </div>

      <motion.button
        className="btn-primary spread-intro-v2__start-btn"
        onClick={onStart}
        whileTap={{ scale: 0.96 }}
      >
        Перейти к раскладу
      </motion.button>
    </motion.div>
  );
}
