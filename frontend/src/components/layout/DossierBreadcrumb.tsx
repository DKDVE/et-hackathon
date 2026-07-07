import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

type DossierBreadcrumbProps = {
  eventId: string;
};

export function DossierBreadcrumb({ eventId }: DossierBreadcrumbProps) {
  return (
    <div className="border-b border-border/50 bg-background">
      <div className="mx-auto max-w-[90rem] px-6 py-3">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
          <Link to="/events" className="hover:text-primary">
            Events
          </Link>
          <ChevronRight className="size-3.5" />
          <span className="text-foreground">Event #{eventId}</span>
        </div>
      </div>
    </div>
  );
}
