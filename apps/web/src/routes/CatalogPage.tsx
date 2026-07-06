import { useQuery } from "@tanstack/react-query";
import { useOrgFetch } from "@/lib/useApi";
import type { CatalogReport } from "@/lib/types";

export function CatalogPage() {
  const orgFetch = useOrgFetch();
  const reportsQuery = useQuery({
    queryKey: ["catalog", "reports"],
    queryFn: () => orgFetch<CatalogReport[]>("/catalog/reports"),
  });

  if (reportsQuery.isLoading) return <div className="state-message">Loading catalog…</div>;
  if (reportsQuery.isError) {
    return <div className="state-message">Couldn't load the catalog. Is the API running?</div>;
  }

  const reports = reportsQuery.data!;

  return (
    <div className="cat2-shell">
      <div className="cat2-main">
        {reports.length === 0 && (
          <div className="state-message">
            No reports registered yet for this organization.
          </div>
        )}
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>
    </div>
  );
}

const STRIPE_CLASS: Record<CatalogReport["current_status"], string> = {
  go: "go",
  warn: "warn",
  stop: "stop",
};

function ReportCard({ report }: { report: CatalogReport }) {
  return (
    <div className="rc2" style={{ display: "flex", marginBottom: 10, borderRadius: 8 }}>
      <div className={`rc2-stripe ${STRIPE_CLASS[report.current_status]}`} />
      <div className="rc2-body">
        <div className="rc2-top">
          <div className="rc2-name">
            {report.icon} {report.name}
          </div>
          <div className="rc2-right">
            <span className="rc2-dq-label">{report.current_status.toUpperCase()}</span>
          </div>
        </div>
        <div className="rc2-meta">
          <span>{report.domain_name}</span>
          <span>{report.owner_team}</span>
          <span>{report.refresh_schedule}</span>
          {report.last_run_at && (
            <span>Last run {new Date(report.last_run_at).toLocaleString()}</span>
          )}
        </div>
      </div>
    </div>
  );
}
