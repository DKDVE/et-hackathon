import { useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { DossierBreadcrumb } from "@/components/layout/DossierBreadcrumb";
import { DossierHero } from "@/components/dossier/DossierHero";
import {
  DossierChatDrawer,
  DossierMainColumn,
  DossierSidebar,
} from "@/components/dossier/DossierSections";

export function DossierView() {
  const { id } = useParams<{ id: string }>();
  const eventId = id ?? "—";

  return (
    <AppShell breadcrumb={<DossierBreadcrumb eventId={eventId} />}>
      <DossierHero symptom="Elevated vibration" />
      <div className="grid grid-cols-1 gap-10 pb-24 lg:grid-cols-12 md:pb-8">
        <DossierMainColumn />
        <DossierSidebar />
      </div>
      <DossierChatDrawer />
    </AppShell>
  );
}
