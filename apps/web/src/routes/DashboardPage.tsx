import { useQuery } from "@tanstack/react-query";
import { useOrgFetch } from "@/lib/useApi";
import type { DashboardContext, Incident, SLAStatus } from "@/lib/types";

export function DashboardPage() {
  const orgFetch = useOrgFetch();

  const contextQuery = useQuery({
    queryKey: ["dashboard", "context"],
    queryFn: () => orgFetch<DashboardContext>("/dashboard/context"),
  });
  const slaQuery = useQuery({
    queryKey: ["dashboard", "sla-status"],
    queryFn: () => orgFetch<SLAStatus>("/dashboard/sla-status"),
  });
  const incidentsQuery = useQuery({
    queryKey: ["dashboard", "incidents"],
    queryFn: () => orgFetch<Incident[]>("/dashboard/incidents"),
  });

  if (contextQuery.isLoading || slaQuery.isLoading || incidentsQuery.isLoading) {
    return <div className="state-message">Loading dashboard…</div>;
  }
  if (contextQuery.isError || slaQuery.isError || incidentsQuery.isError) {
    return <div className="state-message">Couldn't load dashboard data. Is the API running?</div>;
  }

  const ctx = contextQuery.data!;
  const sla = slaQuery.data!;
  const incidents = incidentsQuery.data!;

  return (
    <div className="db-wrap">
      <div className="db-ctx">
        <div className="db-ctx-item">
          <span className="db-ctx-label">Reports</span>
          <span className="db-ctx-val">{ctx.reports_count}</span>
        </div>
        <div className="db-ctx-item">
          <span className="db-ctx-label">Domains</span>
          <span className="db-ctx-val">{ctx.domains_count}</span>
        </div>
        <div className="db-ctx-spacer" />
        <div className="db-ctx-scan">
          {ctx.scan_time ? (
            <>
              Last scan {ctx.scan_time} · {ctx.scan_date}
              {ctx.next_scan_in ? ` · Next in ${ctx.next_scan_in}` : ""}
            </>
          ) : (
            "No scans yet"
          )}
        </div>
      </div>

      <div className="db-sla">
        <div className="db-sla-hdr">
          <span className="db-sla-hdr-title">SLA Status — {sla.layer} layer</span>
          {sla.as_of && <span style={{ marginLeft: "auto", color: "var(--fog4)" }}>{sla.as_of}</span>}
        </div>
        <div style={{ display: "flex" }}>
          <SlaCount label="Breach" sub="SLA violated" count={sla.breach} tone="error" />
          <SlaCount label="Warnings" sub="At risk" count={sla.warning} tone="warning" />
          <SlaCount label="Healthy" sub="All SLAs met" count={sla.healthy} tone="success" />
        </div>
      </div>

      <div className="db-grid">
        <div className="db-rca-section">
          <div
            style={{
              fontFamily: "var(--FM)",
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: ".12em",
              color: "var(--fog4)",
            }}
          >
            Active incidents — today
          </div>

          {incidents.length === 0 && (
            <div className="state-message">No active incidents. All pipelines healthy.</div>
          )}

          {incidents.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))}
        </div>
      </div>
    </div>
  );
}

function SlaCount({
  label,
  sub,
  count,
  tone,
}: {
  label: string;
  sub: string;
  count: number;
  tone: "error" | "warning" | "success";
}) {
  const colorVar = `var(--md-${tone === "success" ? "success" : tone === "warning" ? "warning" : "error"})`;
  const bgVar = tone === "warning" ? "var(--warn-bg)" : `var(--md-${tone}-cont)`;
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        padding: "14px 20px",
        borderRight: "1px solid var(--rule)",
        background: bgVar,
      }}
    >
      <span style={{ fontSize: 22, fontWeight: 300, color: colorVar, letterSpacing: "-.5px" }}>
        {count}
      </span>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, color: colorVar }}>{label}</div>
        <div style={{ fontSize: 11, color: colorVar, opacity: 0.7 }}>{sub}</div>
      </div>
    </div>
  );
}

function IncidentCard({ incident }: { incident: Incident }) {
  const layerOrder = ["source", "staging", "ods", "dm"];
  return (
    <div className={`inc-card ${incident.severity}`}>
      <div className="inc-stripe" />
      <div className="inc-hdr">
        <div className="inc-status-row">
          <span className="inc-status-badge">
            {incident.severity === "critical" ? "❌ Critical Incident" : "⚠ Warning"}
          </span>
          <span className="inc-sla-breach">
            {incident.reports_affected_count} reports affected
            {incident.availability_label ? ` · ${incident.availability_label}` : ""}
          </span>
          {incident.occurrence_label && (
            <span className="inc-pattern">⚡ {incident.occurrence_label}</span>
          )}
        </div>
        <div className="inc-ai-block">
          <div className="inc-ai-label">
            <span className="inc-ai-label-dot" />
            AI-generated
          </div>
          <div className="inc-ai-name">{incident.ai_name}</div>
          <div className="inc-ai-desc">
            {incident.ai_description}
            {incident.delay_label ? ` — ${incident.delay_label}` : ""}
          </div>
        </div>
        <div className="inc-where">
          <span className="inc-where-item">{incident.mart_name}</span>
          {layerOrder
            .filter((layer) => incident.layer_statuses[layer])
            .map((layer, idx) => (
              <span key={layer} style={{ display: "contents" }}>
                {idx > 0 && <span className="inc-where-sep">›</span>}
                <span className="inc-where-item">
                  {layer} {incident.layer_statuses[layer] === "ok" ? "✓" : "✕"}
                </span>
              </span>
            ))}
        </div>
      </div>
      {incident.est_recovery_time && (
        <div className="inc-footer">
          <span className="inc-eta">Est. recovery: {incident.est_recovery_time}</span>
        </div>
      )}
    </div>
  );
}
