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
    // Strip markdown bold/italic markers — backend prose mixes **жирный** with
    // plain text and our dropcap split breaks them mid-pair (see GlossaryTerm
    // body), leaving stray `*` / `**` in the rendered output. We don't render
    // <strong> from markdown anyway; the gold dropcap is enough emphasis.
    .replace(/\*+/g, "")
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

/**
 * Render markdown-ish glossary body into the editorial gx-article format.
 * The first non-heading paragraph gets a Playfair dropcap.
 */
function ArticleBody({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: JSX.Element[] = [];
  let listItems: string[] = [];
  let dropcapUsed = false;

  const flushList = () => {
    if (listItems.length === 0) return;
    const items = listItems;
    listItems = [];
    blocks.push(
      <ul key={`list-${blocks.length}`} className="gx-article__list">
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
      blocks.push(
        <h2 key={`h-${blocks.length}`} className="gx-article__h">
          {renderInlineMarkdown(formatMarkdownHeading(heading[2]))}
        </h2>,
      );
      return;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      listItems.push(bullet[1]);
      return;
    }

    flushList();
    const sanitized = sanitizeRussianText(line);
    if (!dropcapUsed && sanitized.length > 0) {
      dropcapUsed = true;
      const first = sanitized.charAt(0);
      const rest = sanitized.slice(1);
      blocks.push(
        <p key={`p-${blocks.length}`}>
          <span className="gx-article__dropcap">{first}</span>
          {renderInlineMarkdown(rest).map((node, i) =>
            typeof node === "string" ? node : <span key={i}>{node}</span>,
          )}
        </p>,
      );
      return;
    }
    blocks.push(
      <p key={`p-${blocks.length}`}>{renderInlineMarkdown(line)}</p>,
    );
  });

  flushList();

  return <div className="gx-article__body">{blocks}</div>;
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
            <article className="gx-article">
              <div className="gx-article__eyebrow">
                {CATEGORY_LABEL[data.category] ?? data.category}
              </div>
              <div className="gx-article__rule" />
              <ArticleBody text={data.full_ru} />
            </article>

            {data.related.length > 0 && (
              <>
                <div
                  className="gx-article__eyebrow"
                  style={{ margin: "24px 0 12px" }}
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
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
