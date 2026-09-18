import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { PRIMARY_WORKSPACES } from "@/lib/workspaces";

export default function WorkspaceIndexPage({ workspaceId }) {
  const workspace = PRIMARY_WORKSPACES.find(({ id }) => id === workspaceId);
  if (!workspace) return null;
  const views = workspace.tabs.filter(({ to }) => to !== workspace.to);
  return <div className="space-y-4" data-testid={`workspace-index-${workspaceId}`}>
    <div className="border-b border-border pb-4"><h2 className="text-lg font-semibold">{workspace.label} workspace</h2><p className="mt-1 max-w-2xl text-sm text-muted-foreground">{workspace.summary}</p></div>
    <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 xl:grid-cols-3">
      {views.map(({ to, label }) => <Link key={to} to={to} className="group flex min-h-24 items-center justify-between gap-4 bg-card p-4 transition-colors hover:bg-secondary/60"><div><div className="text-sm font-semibold">{label}</div><div className="mt-1 font-mono text-[10px] text-muted-foreground">{to}</div></div><ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground"/></Link>)}
    </div>
  </div>;
}
