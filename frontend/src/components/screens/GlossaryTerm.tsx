import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app";
import { glossaryApi } from "@/services/api";

const CATEGORY_LABEL: Record<string, string> = {
  planet: "Планета",
  sign: "Знак",
  house: "Дом",
  aspect: "Аспект",
  concept: "Понятие",
};

const ENGLISH_ASTRO_TERMS: Record<string, string> = {
  Aries: "Овен",
  Taurus: "Телец",
  Gemini: "Близнецы",
  Cancer: "Рак",
  Leo: "Лев",
  Virgo: "Дева",
  Libra: "Весы",
  Scorpio: "Скорпион",
  Sagittarius: "Стрелец",
  Capricorn: "Козерог",
  Aquarius: "Водолей",
  Pisces: "Рыбы",
  Sun: "Солнце",
  Moon: "Луна",
  Mercury: "Меркурий",
  Venus: "Венера",
  Mars: "Марс",
  Jupiter: "Юпитер",
  Saturn: "Сатурн",
  Uranus: "Уран",
  Neptune: "Нептун",
  Pluto: "Плутон",
  Ascendant: "Асцендент",
  Descendant: "Десцендент",
  Midheaven: "Середина неба",
  ASC: "Асцендент",
  DSC: "Десцендент",
  AC: "Асцендент",
  DC: "Десцендент",
  IC: "Нижняя точка неба",
  MC: "Середина неба",
};

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function sanitizeRussianText(text: string): string {
  let cleaned = text
    .replace(/\s*\((?=[^)]*[A-Za-z])[^)]*\)/g, "")
    .replace(/\s*\[(?=[^\]]*[A-Za-z])[^\]]*\]/g, "");

  Object.entries(ENGLISH_ASTRO_TERMS).forEach(([en, ru]) => {
    cleaned = cleaned.replace(new RegExp(`\\b${escapeRegExp(en)}\\b`, "gi"), ru);
  });

  const duplicateParenthetical = cleaned.match(/^(.+?)\s*\((.+)\)$/u);
  if (
    duplicateParenthetical &&
    duplicateParenthetical[1].trim().toLocaleLowerCase("ru-RU") ===
      duplicateParenthetical[2].trim().toLocaleLowerCase("ru-RU")
  ) {
    cleaned = duplicateParenthetical[1].trim();
  }

  return cleaned
    .replace(/\s+([.,;:!?])/g, "$1")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function renderInlineMarkdown(text: string): (string | JSX.Element)[] {
  const parts = sanitizeRussianText(text).split(/(\*\*[^*]+\*\*)/g);

  return parts
    .filter(Boolean)
    .map((part, index) => {
      const bold = part.match(/^\*\*([^*]+)\*\*$/);
      if (!bold) return part;

      return <strong key={index}>{bold[1]}</strong>;
    });
}

function formatMarkdownHeading(text: string): string {
  return sanitizeRussianText(text);
}

function MarkdownText({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: JSX.Element[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (listItems.length === 0) return;

    const items = listItems;
    listItems = [];
    blocks.push(
      <ul key={`list-${blocks.length}`} className="glossary-markdown__list">
        {items.map((item, index) => (
          <li key={index}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>,
    );
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();

    if (!line) {
      flushList();
      return;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushList();
      const level = heading[1].length;
      const Tag = level === 1 ? "h3" : "h4";
      blocks.push(
        <Tag
          key={`heading-${blocks.length}`}
          className={`glossary-markdown__heading glossary-markdown__heading--${level}`}
        >
          {renderInlineMarkdown(formatMarkdownHeading(heading[2]))}
        </Tag>,
      );
      return;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      listItems.push(bullet[1]);
      return;
    }

    flushList();
    blocks.push(
      <p key={`paragraph-${blocks.length}`} className="glossary-markdown__paragraph">
        {renderInlineMarkdown(line)}
      </p>,
    );
  });

  flushList();

  return <div className="glossary-markdown">{blocks}</div>;
}

export function GlossaryTerm() {
  const { setScreen, glossarySlug, setGlossarySlug } = useAppStore();

  const { data, isLoading, error } = useQuery({
    queryKey: ["glossary-term", glossarySlug],
    queryFn: () => glossaryApi.get(glossarySlug!),
    enabled: !!glossarySlug,
    staleTime: 1000 * 60 * 60,
  });

  const openRelated = (slug: string) => {
    setGlossarySlug(slug);
  };

  return (
    <div className="screen glossary-screen">
      <div className="screen-header screen-header--with-back">
        <button
          className="back-btn"
          onClick={() => setScreen("glossary", "back")}
          aria-label="Назад"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M13 4l-6 6 6 6" />
          </svg>
        </button>
        <h2 className="screen-title">
          {data?.title_ru ? sanitizeRussianText(data.title_ru) : "Термин"}
        </h2>
      </div>

      <div className="screen-content">
        {isLoading && (
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Загрузка...
          </p>
        )}
        {error && (
          <p style={{ color: "var(--text-dim)", textAlign: "center" }}>
            Термин не найден.
          </p>
        )}
        {data && (
          <>
            <div className="horoscope-card">
              <div
                className="horoscope-card__period"
                style={{ marginBottom: 8 }}
              >
                {CATEGORY_LABEL[data.category] ?? data.category}
              </div>
              <MarkdownText text={data.full_ru} />
            </div>

            {data.related.length > 0 && (
              <div className="horoscope-card">
                <div
                  className="horoscope-card__period"
                  style={{ marginBottom: 12 }}
                >
                  См. также
                </div>
                <div className="glossary-list">
                  {data.related.map((r) => (
                    <button
                      key={r.slug}
                      className="glossary-item"
                      onClick={() => openRelated(r.slug)}
                    >
                      <div className="glossary-item__title">
                        {sanitizeRussianText(r.title_ru)}
                      </div>
                      <div className="glossary-item__short">
                        {sanitizeRussianText(r.short_ru)}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
