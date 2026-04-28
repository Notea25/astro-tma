import { useCallback } from "react";
import { MacCardsPage } from "@/components/mac/MacCardsPage";
import { useAppStore } from "@/stores/app";

export function Mac() {
  const { setScreen } = useAppStore();
  const handleBack = useCallback(
    () => setScreen("discover", "back"),
    [setScreen],
  );

  return <MacCardsPage onBack={handleBack} />;
}
