import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { useOrgFetch, useOrgMutate } from "@/lib/useApi";
import { ApiError } from "@/lib/api";
import {
  CONNECTION_KIND_FIELDS,
  CONNECTION_KIND_LABELS,
  type Connection,
  type ConnectionKind,
  type ConnectionTestResult,
} from "@/lib/types";

const STATUS_LABEL: Record<Connection["status"], string> = {
  pending: "Not tested yet",
  connected: "Connected",
  error: "Error",
};

export function SettingsPage() {
  const { me, currentOrgId } = useAuth();
  const orgFetch = useOrgFetch();
  const orgMutate = useOrgMutate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const role = me?.memberships.find((m) => m.org_id === currentOrgId)?.role;
  const canManage = role === "org_admin" || role === "engineer";

  const connectionsQuery = useQuery({
    queryKey: ["connections"],
    queryFn: () => orgFetch<Connection[]>("/connections"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => orgMutate(`/connections/${id}`, "DELETE"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => orgMutate<ConnectionTestResult>(`/connections/${id}/test`, "POST"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });

  return (
    <div className="db-wrap">
      <div className="card" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 2 }}>Data source connections</div>
          <div style={{ fontSize: 12.5, color: "var(--fog3)" }}>
            Connect Meridian to your OpenMetadata instance, Greenplum warehouse, or a local
            directory of ETL CSV exports.
          </div>
        </div>
        {canManage && (
          <button className="btn btn-p" style={{ marginLeft: "auto" }} onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "+ Add Connection"}
          </button>
        )}
      </div>

      {showForm && canManage && (
        <ConnectionForm
          onDone={() => {
            setShowForm(false);
            queryClient.invalidateQueries({ queryKey: ["connections"] });
          }}
        />
      )}

      {connectionsQuery.isLoading && <div className="state-message">Loading connections…</div>}
      {connectionsQuery.isError && (
        <div className="state-message">Couldn't load connections. Is the API running?</div>
      )}

      {connectionsQuery.data?.length === 0 && (
        <div className="state-message">No connections configured yet.</div>
      )}

      {connectionsQuery.data?.map((conn) => (
        <div key={conn.id} className="card" style={{ marginBottom: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 600 }}>{conn.name}</div>
              <div style={{ fontSize: 12, color: "var(--fog3)" }}>
                {CONNECTION_KIND_LABELS[conn.kind]}
              </div>
            </div>
            <StatusBadge status={conn.status} />
            {canManage && (
              <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                <button
                  className="btn btn-s"
                  disabled={testMutation.isPending}
                  onClick={() => testMutation.mutate(conn.id)}
                >
                  Test
                </button>
                <button
                  className="btn btn-s"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(conn.id)}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
          {conn.status === "error" && conn.last_checked_error && (
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--md-error)" }}>
              {conn.last_checked_error}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: Connection["status"] }) {
  const colorVar =
    status === "connected" ? "var(--go)" : status === "error" ? "var(--stop)" : "var(--fog3)";
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 600,
        color: colorVar,
        border: `1px solid ${colorVar}`,
        borderRadius: 20,
        padding: "2px 10px",
      }}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

function ConnectionForm({ onDone }: { onDone: () => void }) {
  const orgMutate = useOrgMutate();
  const [kind, setKind] = useState<ConnectionKind>("greenplum");
  const [name, setName] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      orgMutate("/connections", "POST", {
        kind,
        name,
        config: CONFIG_TO_TYPED(kind, values),
      }),
    onSuccess: onDone,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed to create connection"),
  });

  const fields = CONNECTION_KIND_FIELDS[kind];

  return (
    <div className="card">
      <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label style={{ fontSize: 11.5, color: "var(--fog3)" }}>Connection type</label>
          <select
            className="inp"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as ConnectionKind);
              setValues({});
            }}
          >
            {(Object.keys(CONNECTION_KIND_FIELDS) as ConnectionKind[]).map((k) => (
              <option key={k} value={k}>
                {CONNECTION_KIND_LABELS[k]}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label style={{ fontSize: 11.5, color: "var(--fog3)" }}>Name</label>
          <input
            className="inp"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Production Greenplum"
          />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>
        {fields.map((field) => (
          <div key={field.key}>
            <label style={{ fontSize: 11.5, color: "var(--fog3)" }}>{field.label}</label>
            <input
              className="inp"
              type={field.type}
              placeholder={field.placeholder}
              value={values[field.key] ?? field.defaultValue ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
            />
          </div>
        ))}
      </div>

      {error && <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--md-error)" }}>{error}</div>}

      <div style={{ marginTop: 14 }}>
        <button
          className="btn btn-p"
          disabled={!name || createMutation.isPending}
          onClick={() => {
            setError(null);
            createMutation.mutate();
          }}
        >
          Save connection
        </button>
      </div>
    </div>
  );
}

function CONFIG_TO_TYPED(kind: ConnectionKind, values: Record<string, string>): Record<string, unknown> {
  const fields = CONNECTION_KIND_FIELDS[kind];
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.key] ?? field.defaultValue ?? "";
    result[field.key] = field.type === "number" ? Number(raw) : raw;
  }
  return result;
}
