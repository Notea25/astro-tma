import { lazy, Suspense, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import { BottomNav } from "@/components/ui/BottomNav";
import { usersApi } from "@/services/api";
import { useAppStore } from "@/stores/app";
import { useStartParam, useTelegramReady } from "@/hooks/useTelegram";
import { LoadingScreenFull } from "@/components/screens/LoadingScreen";

const loadOnboarding = () =>
  import("@/components/screens/Onboarding").then((m) => ({
    default: m.Onboarding,
  }));
const loadHome = () =>
  import("@/components/screens/Home").then((m) => ({ default: m.Home }));
const loadDiscover = () =>
  import("@/components/screens/Discover").then((m) => ({
    default: m.Discover,
  }));
const loadTarot = () =>
  import("@/components/screens/Tarot").then((m) => ({ default: m.Tarot }));
const loadCompatibility = () =>
  import("@/components/screens/Compatibility").then((m) => ({
    default: m.Compatibility,
  }));
const loadMoon = () =>
  import("@/components/screens/Moon").then((m) => ({ default: m.Moon }));
const loadNatal = () =>
  import("@/components/screens/Natal").then((m) => ({ default: m.Natal }));
const loadMac = () =>
  import("@/components/screens/Mac").then((m) => ({ default: m.Mac }));
const loadProfile = () =>
  import("@/components/screens/Profile").then((m) => ({ default: m.Profile }));
const loadTransits = () =>
  import("@/components/screens/Transits").then((m) => ({
    default: m.Transits,
  }));
const loadSynastry = () =>
  import("@/components/screens/Synastry").then((m) => ({
    default: m.Synastry,
  }));
const loadSynastryInvite = () =>
  import("@/components/screens/SynastryInvite").then((m) => ({
    default: m.SynastryInvite,
  }));
const loadGlossary = () =>
  import("@/components/screens/Glossary").then((m) => ({
    default: m.Glossary,
  }));
const loadGlossaryTerm = () =>
  import("@/components/screens/GlossaryTerm").then((m) => ({
    default: m.GlossaryTerm,
  }));
const loadNews = () =>
  import("@/components/screens/News").then((m) => ({
    default: m.News,
  }));
const loadNewsDetail = () =>
  import("@/components/screens/NewsDetail").then((m) => ({
    default: m.NewsDetail,
  }));

const Onboarding = lazy(loadOnboarding);
const Home = lazy(loadHome);
const Discover = lazy(loadDiscover);
const Tarot = lazy(loadTarot);
const Compatibility = lazy(loadCompatibility);
const Moon = lazy(loadMoon);
const Natal = lazy(loadNatal);
const Mac = lazy(loadMac);
const Profile = lazy(loadProfile);
const Transits = lazy(loadTransits);
const Synastry = lazy(loadSynastry);
const SynastryInvite = lazy(loadSynastryInvite);
const Glossary = lazy(loadGlossary);
const GlossaryTerm = lazy(loadGlossaryTerm);
const News = lazy(loadNews);
const NewsDetail = lazy(loadNewsDetail);

const SCREEN_PRELOADERS = [
  loadHome,
  loadDiscover,
  loadTarot,
  loadCompatibility,
  loadMoon,
  loadNatal,
  loadMac,
  loadProfile,
  loadTransits,
  loadSynastry,
  loadSynastryInvite,
  loadGlossary,
  loadGlossaryTerm,
  loadNews,
  loadNewsDetail,
];

const ONBOARDING_PRELOADERS = [loadHome, loadSynastryInvite];

function SplashScreen() {
  return (
    <motion.div
      style={{ position: "fixed", inset: 0, zIndex: 999 }}
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.6, ease: "easeInOut" }}
    >
      <LoadingScreenFull />
    </motion.div>
  );
}

export default function App() {
  const screen = useAppStore((s) => s.screen);
  const navDirection = useAppStore((s) => s.navDirection);
  const setScreen = useAppStore((s) => s.setScreen);
  const onboardingComplete = useAppStore((s) => s.onboardingComplete);
  const setOnboardingComplete = useAppStore((s) => s.setOnboardingComplete);
  const setUser = useAppStore((s) => s.setUser);
  const pendingInviteToken = useAppStore((s) => s.pendingInviteToken);
  const setPendingInviteToken = useAppStore((s) => s.setPendingInviteToken);
  const [ready, setReady] = useState(false);
  const [synced, setSynced] = useState(false);
  useTelegramReady();
  const startParam = useStartParam();
  const [inviteHandled, setInviteHandled] = useState(false);

  const syncUser = useMutation({
    mutationFn: usersApi.upsertMe,
    onSuccess: (u) => {
      setUser(u);
      // If user has no gender/sign — they were deleted or never completed onboarding
      if (!u.gender && !u.sun_sign) {
        setOnboardingComplete(false);
      }
      setSynced(true);
    },
    onError: () => {
      setSynced(true);
    },
  });

  useEffect(() => {
    syncUser.mutate();
    const timer = setTimeout(() => setReady(true), 3500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!ready || !synced) return;
    const preloaders =
      onboardingComplete || screen !== "onboarding"
        ? SCREEN_PRELOADERS
        : ONBOARDING_PRELOADERS;
    const preload = () => {
      preloaders.forEach((load) => void load());
    };

    if ("requestIdleCallback" in window) {
      const id = window.requestIdleCallback(preload, { timeout: 2500 });
      return () => window.cancelIdleCallback(id);
    }

    const id = globalThis.setTimeout(preload, 300);
    return () => globalThis.clearTimeout(id);
  }, [ready, synced, onboardingComplete, screen]);

  // Capture syn_<token> from start_param into the persisted store as soon as
  // we see it — before splash, before onboarding gate. The token survives a
  // mid-onboarding reload that way.
  useEffect(() => {
    if (startParam?.startsWith("syn_")) {
      const token = startParam.slice(4);
      if (token && token !== pendingInviteToken) {
        setPendingInviteToken(token);
      }
    }
  }, [startParam, pendingInviteToken, setPendingInviteToken]);

  // After both splash timer and sync are done, route the onboarded user.
  // If they have a pending invite waiting, jump straight to the invite
  // landing page; otherwise the usual home screen.
  useEffect(() => {
    if (!ready || !synced || !onboardingComplete) return;
    if (screen !== "onboarding") return;
    setScreen(pendingInviteToken ? "synastry_invite" : "home");
  }, [ready, synced, onboardingComplete, screen, pendingInviteToken, setScreen]);

  // Already-onboarded user opening a fresh invite link: jump to the invite
  // page immediately. Non-onboarded users wait until onboarding finishes
  // (the effect above handles that branch).
  useEffect(() => {
    if (inviteHandled || !ready || !synced || !onboardingComplete) return;
    if (pendingInviteToken) {
      setScreen("synastry_invite");
      setInviteHandled(true);
    }
  }, [
    pendingInviteToken,
    ready,
    synced,
    onboardingComplete,
    inviteHandled,
    setScreen,
  ]);

  const showSplash = !ready || !synced;
  const showNav = !showSplash && screen !== "onboarding";

  if (showSplash) {
    return (
      <div className="app">
        <AnimatePresence mode="wait">
          <SplashScreen />
        </AnimatePresence>
      </div>
    );
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        <Suspense fallback={null}>
          <AnimatePresence mode="wait">
            <motion.div
              key={screen}
              className="screen-container"
              initial={{ opacity: 0, x: navDirection === "back" ? -20 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: navDirection === "back" ? 20 : -20 }}
              transition={{ duration: 0.22, ease: "easeInOut" }}
            >
              {screen === "onboarding" && <Onboarding />}
              {screen === "home" && <Home />}
              {screen === "discover" && <Discover />}
              {screen === "tarot" && <Tarot />}
              {screen === "compatibility" && <Compatibility />}
              {screen === "moon" && <Moon />}
              {screen === "natal" && <Natal />}
              {screen === "mac" && <Mac />}
              {screen === "profile" && <Profile />}
              {screen === "transits" && <Transits />}
              {screen === "synastry" && <Synastry />}
              {screen === "synastry_invite" && <SynastryInvite />}
              {screen === "glossary" && <Glossary />}
              {screen === "glossary_term" && <GlossaryTerm />}
              {screen === "news" && <News />}
              {screen === "news_detail" && <NewsDetail />}
            </motion.div>
          </AnimatePresence>
        </Suspense>

        {showNav && <BottomNav />}
      </div>
    </MotionConfig>
  );
}
