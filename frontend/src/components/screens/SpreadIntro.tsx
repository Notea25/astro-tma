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
  celtic_cross: 0.44,
  week: 0.94,
  relationship: 0.44,
};

export function SpreadIntro({ spreadKey, onStart }: Props) {
  const config = SPREAD_CONFIG[spreadKey];
  const { layout, backVariant, previewSymbols, title } = config;
  const scale = SCALE_BY_KEY[spreadKey] ?? 0.55;

  const previewW = layout.w * scale;
  const previewH = layout.h * scale;
  const cardW = CARD_W * scale;
  const cardH = CARD_H * scale;
  const symbolFontSize = Math.round(cardH * 0.32);
  const firstPosition = config.sections[0]?.positions[0];

  return (
    <motion.div
      className={`spread-intro-v2 spread-intro-v2--showcase spread-intro-v2--${spreadKey}${
        spreadKey === "week" ? " spread-intro-v2--week-ritual" : ""
      }`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <h1 className="spread-intro-v2__title">{title}</h1>

      <div className="spread-intro-v2__preview">
        <div
          className="spread-intro-v2__preview-stage"
          style={{ width: previewW, height: previewH }}
        >
          {layout.slots.map((slot, idx) => {
            const symbol = previewSymbols?.[idx];
            return (
              <div
                key={idx}
                className={`spread-intro-v2__mini-card card-back-pattern--${backVariant}${
                  symbol ? " spread-intro-v2__mini-card--symbolic" : ""
                }`}
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
                {symbol && (
                  <span
                    className="spread-intro-v2__mini-symbol"
                    style={{ fontSize: symbolFontSize }}
                  >
                    {symbol}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {spreadKey === "week" ? (
        <div className="spread-intro-v2__frame spread-intro-v2__frame--week">
          <p
            className="spread-intro-v2__intro-text spread-intro-v2__intro-text--week"
            dangerouslySetInnerHTML={{ __html: config.intro }}
          />
          {firstPosition && (
            <>
              <div className="spread-intro-v2__divider" aria-hidden="true">
                <span />
              </div>
              <div className="spread-intro-v2__week-focus">
                <span className="spread-intro-v2__week-icon">
                  {previewSymbols?.[0] ?? "☽"}
                </span>
                <div>
                  <strong>{firstPosition.label}</strong>
                  <p>{firstPosition.description}</p>
                </div>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="spread-intro-v2__frame">
          <p
            className="spread-intro-v2__intro-text"
            dangerouslySetInnerHTML={{ __html: config.intro }}
          />

          {config.sections.map((section, si) => (
            <div key={si} className="spread-intro-v2__section">
              {section.title && (
                <h4 className="spread-intro-v2__section-title">
                  {section.title}
                </h4>
              )}
              <div className="spread-intro-v2__positions">
                {section.positions.map((pos) => (
                  <div key={pos.num} className="spread-intro-v2__pos">
                    <span className="spread-intro-v2__num">{pos.num}</span>
                    <div className="spread-intro-v2__pos-body">
                      <strong>{pos.label}</strong>
                      <p>{pos.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <motion.button
        className="btn-primary spread-intro-v2__start-btn"
        onClick={onStart}
        whileTap={{ scale: 0.96 }}
      >
        {spreadKey === "week" ? "ОТКРЫТЬ КАРТЫ ✦" : "Перейти к раскладу"}
      </motion.button>
    </motion.div>
  );
}
