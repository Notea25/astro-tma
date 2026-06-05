import { motion } from "framer-motion";
import type { Screen } from "@/stores/app";
import { useAppStore } from "@/stores/app";
import { useHaptic } from "@/hooks/useTelegram";

/**
 * Bottom navigation — 5 equal-width tabs (no FAB). SCREEN_TO_TAB
 * decides which tab is highlighted for any given screen, including
 * nested screens (tarot/moon/mac all live under Practices).
 */
const SCREEN_TO_TAB: Partial<Record<Screen, NavId>> = {
  home: "home",
  horoscopes: "horoscopes",
  discover: "discover",
  tarot: "discover",
  moon: "discover",
  mac: "discover",
  natal: "natal",
  transits: "discover",
  synastry: "discover",
  synastry_invite: "discover",
  glossary: "discover",
  glossary_term: "discover",
  news: "discover",
  news_detail: "discover",
  // Premium opens from Profile's status card; highlight Profile so the
  // user has a clear "back to profile" hint while it's open.
  premium: "profile",
  profile: "profile",
};

type NavId = "home" | "horoscopes" | "discover" | "natal" | "profile";

interface NavItem {
  id: NavId;
  screen: Screen;
  label: string;
  icon: JSX.Element;
}

const NAV_ITEMS: NavItem[] = [
  { id: "home",       screen: "home",       label: "Главная",   icon: <HomeIcon /> },
  { id: "horoscopes", screen: "horoscopes", label: "Гороскопы", icon: <HoroscopesIcon /> },
  { id: "discover",   screen: "discover",   label: "Практики",  icon: <DiscoverIcon /> },
  { id: "natal",      screen: "natal",      label: "Моя карта", icon: <NatalWheelIcon /> },
  { id: "profile",    screen: "profile",    label: "Профиль",   icon: <UserIcon /> },
];

export function BottomNav() {
  const { screen, setScreen } = useAppStore();
  const { selection } = useHaptic();
  const activeTab = SCREEN_TO_TAB[screen] ?? "home";

  const handleNav = (item: NavItem) => {
    if (item.screen === screen) return;
    selection();
    setScreen(item.screen);
  };

  return (
    <nav className="bottom-nav">
      {NAV_ITEMS.map((item) => {
        const active = activeTab === item.id;
        return (
          <button
            key={item.id}
            className={`nav-item ${active ? "active" : ""}`}
            onClick={() => handleNav(item)}
            aria-label={item.label}
            aria-current={active ? "page" : undefined}
          >
            {active && (
              <motion.div
                className="nav-indicator"
                layoutId="nav-indicator"
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
              />
            )}
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

/* ── Icons (24×24 line SVG, stroke from currentColor) ──────────────────── */

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 11l8-7 8 7" />
      <path d="M6 9.5V20h12V9.5" />
      <rect x="10" y="14.5" width="4" height="5.5" />
    </svg>
  );
}

function HoroscopesIcon() {
  // Crescent moon with a small four-point star — the planet/sparkle motif.
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19 14.5A8.5 8.5 0 0 1 9 5a8.5 8.5 0 1 0 10 9.5z" />
      <path
        d="M17 4l.7 1.8L19.5 6.5 17.7 7.2 17 9l-.7-1.8L14.5 6.5l1.8-.7z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
  );
}

function DiscoverIcon() {
  // Crystal-ball / discover motif — circle with base lines.
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="10" r="6.5" />
      <path d="M7.5 18.5h9" />
      <path d="M9 15.5l-1 3M15 15.5l1 3" />
      <path d="M9.5 8.5a3.5 3.5 0 0 1 3-2" opacity="0.7" />
    </svg>
  );
}

function NatalWheelIcon() {
  // Astrology wheel — outer circle, 8 ray ticks, center dot.
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <g strokeWidth="1.1">
        <line x1="12" y1="3" x2="12" y2="5" />
        <line x1="12" y1="19" x2="12" y2="21" />
        <line x1="3" y1="12" x2="5" y2="12" />
        <line x1="19" y1="12" x2="21" y2="12" />
        <line x1="5.6" y1="5.6" x2="7" y2="7" />
        <line x1="17" y1="17" x2="18.4" y2="18.4" />
        <line x1="18.4" y1="5.6" x2="17" y2="7" />
        <line x1="7" y1="17" x2="5.6" y2="18.4" />
      </g>
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="9.5" r="3" />
      <path d="M6.5 18a5.7 5.7 0 0 1 11 0" />
    </svg>
  );
}
