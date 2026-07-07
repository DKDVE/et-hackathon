import { useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { EventCard } from "./EventCard";
import { MOCK_EVENTS } from "@/lib/mock-events";
import { EventFiltersSidebar } from "./EventFiltersSidebar";

const filters = ["All", "Open", "Reviewed", "Closed"] as const;

export function EventBoardContent() {
  const [activeFilter, setActiveFilter] = useState<(typeof filters)[number]>("All");

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <EventFiltersSidebar />
      <div className="w-full min-w-0 flex-1">
        <div className="mb-8 flex flex-wrap items-center gap-3">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter(filter)}
              className={cn(
                "rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all",
                activeFilter === filter
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground",
              )}
            >
              {filter}
            </button>
          ))}
          <div className="ml-auto">
            <Button variant="outline" size="sm" className="gap-2" disabled>
              <Plus className="size-4" />
              Manual Log
            </Button>
          </div>
        </div>
        <div className="space-y-4">
          {MOCK_EVENTS.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </div>
    </div>
  );
}
