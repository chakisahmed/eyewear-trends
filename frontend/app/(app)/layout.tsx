import { Shell } from "@/components/shell/Shell";
import { api } from "@/lib/api";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  // The shell still renders if the API is down; the page itself shows the error card.
  const meta = await api.meta().catch(() => null);
  return <Shell lastUpdate={meta?.last_success?.finished_at ?? null}>{children}</Shell>;
}
