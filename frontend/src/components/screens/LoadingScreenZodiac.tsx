import styles from './LoadingScreenZodiac.module.css';

export function LoadingScreenZodiac() {
  return (
    <div className={styles.screen}>
      {/* Фон со звёздами + туманности — растягивается на весь экран */}
      <img src="/zodiac/01-background-stars.svg" alt="" className={styles.bg} />

      {/* Стек колец — все слои одного размера, наложены друг на друга */}
      <div className={styles.wheel}>
        <img src="/zodiac/02-wheel-grid.svg"           alt="" className={styles.layer} />
        <img src="/zodiac/03-wheel-names.svg"          alt="" className={`${styles.layer} ${styles.spinCw70}`} />
        <img src="/zodiac/04-wheel-large-symbols.svg"  alt="" className={`${styles.layer} ${styles.spinCw70}`} />
        <img src="/zodiac/05-wheel-medium-symbols.svg" alt="" className={`${styles.layer} ${styles.spinCcw90}`} />
        <img src="/zodiac/06-wheel-small-symbols.svg"  alt="" className={`${styles.layer} ${styles.spinCw150}`} />
        <img src="/zodiac/07-center-sun.svg"           alt="" className={`${styles.layer} ${styles.pulseSun}`} />
      </div>

      {/* Подпись */}
      <div className={styles.footer}>
        <h1 className={styles.title}>ASTRO</h1>
        <div className={styles.dots} aria-hidden="true">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}
