import { MessageSquare, Send, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { EvidenceChip } from "@/components/dossier/EvidenceChip";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { chatDossierRaw, type ChatResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  citations?: string[];
  refused?: boolean;
  grounding?: "evidenced" | "hypothesis";
};

const histories = new Map<number, ChatMessage[]>();

function getHistory(dossierId: number): ChatMessage[] {
  if (!histories.has(dossierId)) histories.set(dossierId, []);
  return histories.get(dossierId)!;
}

/**
 * FR-9 — contextual chat drawer. Unlocked when dossier status is complete.
 * History is client-held per dossier (in-memory).
 */
export function ChatDrawer({
  dossierId,
  open,
  onClose,
}: {
  dossierId: number;
  open: boolean;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => getHistory(dossierId));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages(getHistory(dossierId));
  }, [dossierId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || loading) return;
    setError(null);
    const userMsg: ChatMessage = { role: "user", text: q };
    const next = [...messages, userMsg];
    setMessages(next);
    histories.set(dossierId, next);
    setInput("");
    setLoading(true);
    try {
      const history = next.slice(0, -1).slice(-6).map((m) => ({ role: m.role, text: m.text }));
      const resp = await chatDossierRaw(dossierId, q, history);
      if (resp.status === 429) {
        setError("Rate limit reached — try again in a moment.");
        return;
      }
      if (!resp.ok) {
        setError("Reasoning service unavailable.");
        return;
      }
      const data = (await resp.json()) as ChatResponse;
      const assistant: ChatMessage = {
        role: "assistant",
        text: data.answer,
        citations: data.citations,
        refused: data.refused,
        grounding: data.grounding ?? undefined,
      };
      const updated = [...next, assistant];
      setMessages(updated);
      histories.set(dossierId, updated);
    } catch {
      setError("Reasoning service unavailable.");
    } finally {
      setLoading(false);
    }
  }, [dossierId, input, loading, messages]);

  if (!open) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-background shadow-2xl">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <MessageSquare className="size-4 text-primary" />
          Dossier chat
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-muted-foreground hover:bg-muted"
          aria-label="Close chat"
        >
          <X className="size-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <p className="mb-4 text-xs text-muted-foreground">
          Answers come only from this dossier&apos;s assembled plant records. Open an event on
          another asset for its context.
        </p>
        <div className="flex flex-col gap-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={cn(
                "rounded-lg px-3 py-2 text-sm",
                m.role === "user"
                  ? "ml-8 bg-primary/15 text-foreground"
                  : m.refused
                    ? "mr-4 border border-border/60 bg-muted/30 text-muted-foreground italic"
                    : m.grounding === "hypothesis"
                      ? "mr-4 border border-dashed border-muted-foreground/40 bg-card/40"
                      : "mr-4 border border-border bg-card/60",
              )}
            >
              {m.grounding === "hypothesis" && (
                <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Hypothesis
                </span>
              )}
              <p>{m.text}</p>
              {m.citations && m.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {m.citations.map((id) => (
                    <EvidenceChip key={id} citation={id} />
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="mr-4 rounded-lg border border-border bg-card/40 px-3 py-2 text-sm text-muted-foreground">
              Reviewing plant records…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {error && (
        <p className="px-4 pb-2 text-xs text-muted-foreground">{error}</p>
      )}

      <form
        className="flex gap-2 border-t border-border p-4"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={error ? "Reasoning unavailable" : "Ask about this event…"}
          disabled={loading || Boolean(error)}
          className="flex-1"
        />
        <Button type="submit" size="icon" disabled={loading || !input.trim() || Boolean(error)}>
          <Send className="size-4" />
        </Button>
      </form>
    </div>
  );
}
