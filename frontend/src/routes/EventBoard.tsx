import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { EventBoardContent } from "@/components/events/EventBoardContent";

export function EventBoard() {
  return (
    <AppShell>
      <PageHeader
        title="Operational Events"
        subtitle="Abnormality events awaiting context assembly"
      />
      <EventBoardContent />
    </AppShell>
  );
}
