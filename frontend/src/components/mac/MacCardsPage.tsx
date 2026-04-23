import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import styles from './MacCardsPage.module.css';
import { MacCardBack } from './MacCardBack';
import { MAC_DECK, CATEGORY_INFO, CARD_W, CARD_H } from './macData';
import type { MacCard, MacCategory } from './macData';
import { useHaptic, useTelegramBackButton } from '@/hooks/useTelegram';

type Phase = 'idle' | 'shuffle' | 'fan' | 'drawn' | 'revealed';

type Filter = MacCategory | 'all';

type FanCard = { id: number; card: MacCard; gone: boolean };

type FlyingCard = {
  card: MacCard;
  startX: number;
  startY: number;
  dx: number;
  dy: number;
  startRot: number;
};

// ─── static star field ────────────────────────────────────────────────────────

const STARS = Array.from({ length: 70 }, (_, i) => ({
  id: i,
  x: (i * 73 + 11) % 100,
  y: (i * 47 + 7) % 100,
  size: 0.6 + (i % 5) * 0.35,
  delay: (i * 0.37) % 4,
  dur: 2 + (i % 6) * 0.5,
  op: 0.15 + (i % 4) * 0.08,
}));

const FILTERS: { id: Filter; name: string; symbol: string; accent: string }[] = [
  { id: 'all',            name: 'Все',             symbol: '✵', accent: '#c9a84c' },
  { id: 'inner_world',    name: CATEGORY_INFO.inner_world.name,    symbol: CATEGORY_INFO.inner_world.symbol,    accent: CATEGORY_INFO.inner_world.accent },
  { id: 'relationships',  name: CATEGORY_INFO.relationships.name,  symbol: CATEGORY_INFO.relationships.symbol,  accent: CATEGORY_INFO.relationships.accent },
  { id: 'path',           name: CATEGORY_INFO.path.name,           symbol: CATEGORY_INFO.path.symbol,           accent: CATEGORY_INFO.path.accent },
  { id: 'fears',          name: CATEGORY_INFO.fears.name,          symbol: CATEGORY_INFO.fears.symbol,          accent: CATEGORY_INFO.fears.accent },
  { id: 'resources',      name: CATEGORY_INFO.resources.name,      symbol: CATEGORY_INFO.resources.symbol,      accent: CATEGORY_INFO.resources.accent },
  { id: 'transformation', name: CATEGORY_INFO.transformation.name, symbol: CATEGORY_INFO.transformation.symbol, accent: CATEGORY_INFO.transformation.accent },
];

// ─── fan card size (smaller than main card) ──────────────────────────────────

const FAN_CARD_W = 140;
const FAN_CARD_H = 216;

// ─── card front ────────────────────────────────────────────────────────────

function CardFront({ card }: { card: MacCard }) {
  const info = CATEGORY_INFO[card.category];
  const [imgFailed, setImgFailed] = useState(false);
  const imageUrl = `/mac/card-${card.number}.png`;
  return (
    <div
      className={styles.frontWrap}
      style={{
        '--accent': info.accent,
        '--front-from': info.bgFrom,
        '--front-to': info.bgTo,
      } as React.CSSProperties}
    >
      <div className={styles.frontBorder} />
      <div className={styles.frontMeta}>
        <span className={styles.frontNumeral}>№ {card.number}</span>
        <span className={styles.frontCategory}>{info.name.toUpperCase()}</span>
      </div>
      {imgFailed ? (
        <div className={styles.frontSymbol}>{info.symbol}</div>
      ) : (
        <div className={styles.frontImageWrap}>
          <img
            className={styles.frontImage}
            src={imageUrl}
            alt={card.name}
            onError={() => setImgFailed(true)}
            loading="lazy"
            draggable={false}
          />
          <div className={styles.frontImageGlow} />
        </div>
      )}
      <div className={styles.frontName}>{card.name}</div>
      <div className={styles.frontDivider}>
        <span className={styles.frontDividerDot} />
      </div>
      <div className={styles.frontTagline}>
        <span className={styles.frontTaglineLabel}>Аффирмация</span>
        {card.affirmation}
      </div>
    </div>
  );
}

// ─── component ────────────────────────────────────────────────────────────

export function MacCardsPage({ onBack }: { onBack: () => void }) {
  const { impact } = useHaptic();
  const [filter, setFilter] = useState<Filter>('all');
  const [phase, setPhase] = useState<Phase>('idle');
  const [card, setCard] = useState<MacCard | null>(null);
  const [fanCards, setFanCards] = useState<FanCard[]>([]);
  const [flyingCard, setFlyingCard] = useState<FlyingCard | null>(null);
  const [justLanded, setJustLanded] = useState(false);
  const [viewW, setViewW] = useState(() => typeof window !== 'undefined' ? window.innerWidth : 1200);

  const dropTargetRef = useRef<HTMLDivElement>(null);
  const fanCardRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  useTelegramBackButton(onBack, true);

  const filterInfo = useMemo(() => FILTERS.find(f => f.id === filter)!, [filter]);
  const cardInfo = card ? CATEGORY_INFO[card.category] : null;

  useEffect(() => {
    const h = () => setViewW(window.innerWidth);
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, []);

  // ── fan parameters (responsive) ──────────────────────────────────────────

  const fanCount = Math.min(11, Math.max(5, Math.floor(viewW / 150)));
  const spreadDeg = Math.min(90, Math.max(45, viewW * 0.045 + 10));

  // ── filter select ────────────────────────────────────────────────────────

  const handleSelectFilter = useCallback((id: Filter) => {
    if (phase !== 'idle') return;
    setFilter(id);
  }, [phase]);

  // ── shuffle → show fan ───────────────────────────────────────────────────

  const handleShuffleAndDraw = useCallback(() => {
    if (phase !== 'idle') return;
    impact('medium');
    setPhase('shuffle');
    setTimeout(() => {
      const pool = filter === 'all' ? MAC_DECK : MAC_DECK.filter(c => c.category === filter);
      const withoutLast = card ? pool.filter(c => c.number !== card.number) : pool;
      const shuffled = [...withoutLast].sort(() => Math.random() - 0.5);
      const picks = shuffled.slice(0, Math.min(fanCount, shuffled.length));
      setFanCards(picks.map((c, i) => ({ id: i, card: c, gone: false })));
      setPhase('fan');
    }, 2000);
  }, [phase, filter, fanCount, card, impact]);

  // ── fan card click → fly to center ───────────────────────────────────────

  const handleFanCardClick = useCallback((fanId: number, pickedCard: MacCard) => {
    if (flyingCard !== null) return;

    const cardEl = fanCardRefs.current.get(fanId);
    const targetEl = dropTargetRef.current;
    if (!cardEl || !targetEl) return;
    impact('medium');

    const cardRect = cardEl.getBoundingClientRect();
    const targetRect = targetEl.getBoundingClientRect();

    // centre of drop area, offset so card centre lands there
    const targetX = targetRect.left + targetRect.width / 2 - CARD_W / 2;
    const targetY = targetRect.top + targetRect.height / 2 - CARD_H / 2;

    // remember fan-angle of this card to start the flight from that rotation
    const activeFan = fanCards.filter(fc => !fc.gone);
    const N = activeFan.length;
    const idx = activeFan.findIndex(fc => fc.id === fanId);
    const t = N === 1 ? 0.5 : idx / (N - 1);
    const startRot = spreadDeg * (t - 0.5);

    setFanCards(prev => prev.map(fc => fc.id === fanId ? { ...fc, gone: true } : fc));
    setFlyingCard({
      card: pickedCard,
      startX: cardRect.left,
      startY: cardRect.top,
      dx: targetX - cardRect.left,
      dy: targetY - cardRect.top,
      startRot,
    });
  }, [flyingCard, fanCards, spreadDeg, impact]);

  // ── fly animation ends → card lands ──────────────────────────────────────

  const handleFlyEnd = useCallback(() => {
    if (!flyingCard) return;
    const landed = flyingCard.card;
    setCard(landed);
    setPhase('drawn');
    setFlyingCard(null);
    setFanCards([]);
    setJustLanded(true);
    setTimeout(() => setJustLanded(false), 500);
  }, [flyingCard]);

  // ── reveal (flip) ────────────────────────────────────────────────────────

  const handleReveal = useCallback(() => {
    if (phase !== 'drawn') return;
    impact('success' as any);
    setPhase('revealed');
  }, [phase, impact]);

  // ── draw another → back to idle, keep card for exclusion ─────────────────

  const handleDrawAgain = useCallback(() => {
    setPhase('idle');
  }, []);

  // ── reset ────────────────────────────────────────────────────────────────

  const handleReset = useCallback(() => {
    setPhase('idle');
    setCard(null);
    setFanCards([]);
    setFlyingCard(null);
    setJustLanded(false);
  }, []);

  // ── prompt ───────────────────────────────────────────────────────────────

  const prompt = (() => {
    if (phase === 'idle') return card
      ? 'Нажмите на колоду — вытяните новую карту'
      : 'Задайте вопрос и нажмите на колоду';
    if (phase === 'shuffle') return 'Карты перемешиваются…';
    if (phase === 'fan') return flyingCard ? '' : 'Выберите карту, которую чувствуете';
    if (phase === 'drawn') return 'Нажмите на карту, чтобы открыть';
    return '';
  })();

  const showDeck = phase === 'idle' || phase === 'shuffle';
  const showCard = phase === 'drawn' || phase === 'revealed';
  const showFan = phase === 'fan';
  const activeFan = fanCards.filter(fc => !fc.gone);
  const N = activeFan.length;

  return (
    <div className={styles.page}>
      {/* Stars */}
      {STARS.map(s => (
        <div key={s.id} className={styles.star} style={{
          left: `${s.x}%`, top: `${s.y}%`,
          width: s.size, height: s.size, opacity: s.op,
          '--dur': `${s.dur}s`, '--delay': `${s.delay}s`, '--base-op': s.op,
        } as React.CSSProperties} />
      ))}

      {/* Header */}
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={onBack}>← Назад</button>
        <h1 className={styles.title}>
          ЗЕРКАЛО&nbsp;ДУШИ
          <span className={styles.titleSub}>метафорические карты</span>
        </h1>
        <button className={styles.resetBtn} onClick={handleReset}>Сначала</button>
      </header>

      {/* Category selector — only while idle and no card shown */}
      {phase === 'idle' && !card && (
        <div className={styles.categorySelector}>
          {FILTERS.map(f => (
            <button
              key={f.id}
              className={`${styles.categoryTab} ${filter === f.id ? styles.categoryTabActive : ''}`}
              style={{ '--tab-accent': f.accent } as React.CSSProperties}
              onClick={() => handleSelectFilter(f.id)}
            >
              <span className={styles.categorySym}>{f.symbol}</span>
              {f.name}
            </button>
          ))}
        </div>
      )}

      {/* Prompt */}
      <p className={styles.prompt}>{prompt}</p>

      {/* Stage */}
      <div className={styles.stage}>
        <div className={styles.drawnCardArea} ref={dropTargetRef}>
          {showCard && card && (
            <div
              className={styles.cardPerspective}
              onClick={phase === 'drawn' ? handleReveal : undefined}
              style={phase === 'revealed' ? { cursor: 'default' } : undefined}
            >
              <div
                className={`${styles.cardInner} ${phase === 'revealed' ? styles.revealed : ''} ${justLanded ? styles.cardJustLanded : ''}`}
              >
                <div className={`${styles.cardBackFace} ${phase === 'drawn' ? styles.cardWaiting : ''}`}>
                  <MacCardBack width={CARD_W} height={CARD_H} />
                </div>
                <div className={styles.cardFrontFace}>
                  <CardFront card={card} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Reading panel — appears after reveal */}
        {phase === 'revealed' && card && cardInfo && (
          <>
            <div
              className={styles.readingPanel}
              style={{ '--accent': cardInfo.accent } as React.CSSProperties}
            >
              <div className={styles.readingHeader}>
                <div className={styles.readingCategory}>{cardInfo.symbol} &nbsp; {cardInfo.name}</div>
                <h2 className={styles.readingName}>{card.name}</h2>
                <div className={styles.readingNumber}>Карта №{card.number} из {MAC_DECK.length}</div>
              </div>

              <div className={styles.readingDivider} />

              <p className={styles.readingDescription}>{card.description}</p>

              <p className={styles.readingSectionTitle}>✦ &nbsp; Вопросы для размышления &nbsp; ✦</p>

              <ul className={styles.readingQuestions}>
                {card.questions.map((q, i) => <li key={i}>{q}</li>)}
              </ul>

              <p className={styles.readingSectionTitle}>✦ &nbsp; Аффирмация &nbsp; ✦</p>

              <p className={styles.readingAffirmation}>«{card.affirmation}»</p>
            </div>

            <button className={styles.drawAgain} onClick={handleDrawAgain}>
              Вытянуть ещё карту
            </button>
          </>
        )}
      </div>

      {/* Flying card — in transit from fan to centre */}
      {flyingCard && (
        <div
          className={styles.flyingCard}
          style={{
            left: flyingCard.startX,
            top: flyingCard.startY,
            width: FAN_CARD_W,
            height: FAN_CARD_H,
            '--dx': `${flyingCard.dx + (CARD_W - FAN_CARD_W) / 2}px`,
            '--dy': `${flyingCard.dy + (CARD_H - FAN_CARD_H) / 2}px`,
            '--start-rot': `${flyingCard.startRot}deg`,
            '--scale-up': `${CARD_W / FAN_CARD_W}`,
          } as React.CSSProperties}
          onAnimationEnd={handleFlyEnd}
        >
          <MacCardBack width={FAN_CARD_W} height={FAN_CARD_H} />
        </div>
      )}

      {/* Fan — carpet of cards to pick from */}
      {showFan && N > 0 && (
        <div
          className={styles.fanContainer}
          style={{ transform: 'translateX(-50%)' }}
        >
          {activeFan.map((fc, i) => {
            const t = N === 1 ? 0.5 : i / (N - 1);
            const angleDeg = spreadDeg * (t - 0.5);
            const delay = i * 0.055;
            return (
              <div
                key={fc.id}
                className={styles.fanCardWrapper}
                style={{
                  '--angle': `${angleDeg}deg`,
                  '--appear-delay': `${delay}s`,
                  zIndex: i + 1,
                } as React.CSSProperties}
                ref={el => { if (el) fanCardRefs.current.set(fc.id, el); }}
                onClick={() => !flyingCard && handleFanCardClick(fc.id, fc.card)}
              >
                <div className={styles.fanCardInner}>
                  <MacCardBack width={FAN_CARD_W} height={FAN_CARD_H} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Deck — shown during idle and shuffle */}
      {showDeck && (
        <div className={styles.deckContainer}>
          <div
            className={`${styles.deck} ${phase === 'shuffle' ? styles.deckShuffling : ''} ${phase === 'idle' ? styles.deckCursorPointer : ''}`}
            onClick={phase === 'idle' ? handleShuffleAndDraw : undefined}
          >
            {[3, 2, 1, 0].map((idx) => (
              <div key={idx} className={styles.deckCardLayer} style={{
                zIndex: 4 - idx,
                left: idx * 2.5 - 5,
                top: idx * 2.5,
                width: 160,
                height: 246,
                opacity: 0.55 + idx * 0.12,
              }}>
                <MacCardBack width={160} height={246} />
              </div>
            ))}
            <div className={styles.deckCardLayer} style={{ zIndex: 10, left: 5, top: 10, width: 160, height: 246 }}>
              <MacCardBack width={160} height={246} />
            </div>
          </div>
          {phase === 'idle' && (
            <>
              <span className={styles.deckLabel}>{filterInfo.symbol} &nbsp; {filterInfo.name.toUpperCase()}</span>
              <span className={styles.deckHint}>нажмите, чтобы вытянуть</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
