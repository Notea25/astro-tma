import { NatalChart } from "@/components/NatalChart";
import type { NatalChartData } from "@/components/NatalChart";
import styles from "./NatalBirthCard.module.css";

interface NatalBirthCardProps {
  chartData: NatalChartData;
  userName?: string | null;
  ascendantLabel?: string | null;
  birthDate?: string | null;
  birthTime?: string | null;
  birthTimeKnown: boolean;
  birthCity?: string | null;
  birthLat?: number | null;
  birthLng?: number | null;
  birthTz?: string | null;
}

const DATE_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  timeZone: "UTC",
  year: "numeric",
});

function formatBirthDate(value?: string | null): string {
  if (!value) return "Дата рождения не указана";

  const [datePart] = value.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  if (!year || !month || !day) return value;

  return DATE_FORMATTER.format(new Date(Date.UTC(year, month - 1, day)));
}

function formatBirthDateTime(
  birthDate?: string | null,
  birthTime?: string | null,
  birthTimeKnown?: boolean,
): string {
  const dateText = formatBirthDate(birthDate);
  return birthTimeKnown && birthTime ? `${dateText} · ${birthTime}` : dateText;
}

function formatCoordinate(
  value: number,
  positiveLabel: "N" | "E",
  negativeLabel: "S" | "W",
): string {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positiveLabel : negativeLabel}`;
}

export function NatalBirthCard({
  chartData,
  userName,
  ascendantLabel,
  birthDate,
  birthTime,
  birthTimeKnown,
  birthCity,
  birthLat,
  birthLng,
  birthTz,
}: NatalBirthCardProps) {
  const displayName = userName?.trim() || "Ваше имя";
  const hasAscendant = Boolean(ascendantLabel && ascendantLabel !== "—");
  const ascendantText = hasAscendant
    ? `${ascendantLabel} восходящий`
    : "Асцендент не рассчитан";
  const birthDateTime = formatBirthDateTime(
    birthDate,
    birthTime,
    birthTimeKnown,
  );
  const cityText = birthCity?.trim() || "Город не указан";
  const coordinateText =
    birthLat != null && birthLng != null
      ? `${formatCoordinate(birthLat, "N", "S")} · ${formatCoordinate(
          birthLng,
          "E",
          "W",
        )}`
      : null;
  const metaText = [coordinateText, birthTz?.trim()].filter(Boolean).join(" · ");
  const namedChartData = { ...chartData, name: displayName };

  return (
    <section className={styles.card} aria-label="Карточка натальной карты">
      <span className={styles.cornerTopLeft} aria-hidden="true">
        ✦
      </span>
      <span className={styles.cornerTopRight} aria-hidden="true">
        ✦
      </span>
      <span className={styles.cornerBottomLeft} aria-hidden="true">
        ✦
      </span>
      <span className={styles.cornerBottomRight} aria-hidden="true">
        ✦
      </span>

      <div className={styles.header}>
        <div className={styles.headerStars} aria-hidden="true">
          ✦ ✦ ✦
        </div>
        <div className={styles.kicker}>НАТАЛЬНАЯ КАРТА</div>
      </div>

      <div className={styles.chartFrame}>
        <NatalChart
          data={namedChartData}
          theme="onyx-gold"
          variant="reference-wheel"
          size={520}
          className={styles.chart}
        />
      </div>

      <div className={styles.ascendant}>
        <span aria-hidden="true">✦</span>
        <span>{ascendantText}</span>
        <span aria-hidden="true">✦</span>
      </div>

      <h3 className={styles.name}>{displayName}</h3>
      <p className={styles.quote}>«Рождённый звёздами»</p>

      <div className={styles.divider} aria-hidden="true">
        <span />
        <b>✦</b>
        <span />
      </div>

      <div className={styles.birthInfo}>
        <div className={styles.birthDate}>{birthDateTime}</div>
        <div className={styles.city}>{cityText}</div>
        {metaText && <div className={styles.meta}>{metaText}</div>}
      </div>

      <footer className={styles.footer}>
        <div className={styles.brand}>ASTROGUIDE</div>
        <div className={styles.caption}>
          Ваша карта неба, рассказанная звёздами
        </div>
      </footer>
    </section>
  );
}
