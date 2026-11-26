import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { apiGet, baseUrl } from "./api";
import "./styles.css";

const COLORS = ["#6e82ff", "#24b99a", "#f3a64a", "#ee6680", "#50afdb", "#a48bff"];
const NAV_ITEMS = ["Overview", "Tasks", "Analytics", "Monitoring"];

function Metric({ label, value, note, color = "blue" }) {
  return (
    <article className={`metric-card ${color}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}

function ChartCard({ title, subtitle, children, className = "" }) {
  return (
    <section className={`panel chart-panel ${className}`}>
      <div className="panel-heading"><div><h2>{title}</h2><p>{subtitle}</p></div></div>
      {children}
    </section>
  );
}

function EmptyState({ text }) {
  return <div className="empty-state">{text}</div>;
}

function App() {
  const [section, setSection] = useState("Overview");
  const [data, setData] = useState({ performance: null, comparison: null, resources: null, tasks: [] });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [performance, comparison, resources, tasks] = await Promise.all([
        apiGet("/api/analytics/performance"),
        apiGet("/api/analytics/comparison?tasks=60&seed=42"),
        apiGet("/api/monitoring/resources"),
        apiGet("/api/tasks?limit=25"),
      ]);
      setData({ performance, comparison, resources, tasks: tasks.items });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const summary = data.comparison?.comparison || [];
  const distribution = Object.entries(data.performance?.location_distribution || {}).map(
    ([name, value]) => ({ name: name[0].toUpperCase() + name.slice(1), value }),
  );
  const decisionDistribution = Object.entries(data.performance?.decision_distribution || {}).map(
    ([name, value]) => ({ name: name[0].toUpperCase() + name.slice(1), value }),
  );
  const chartSummary = summary.map((row) => ({
    ...row,
    policy: row.policy.replaceAll("_", " "),
  }));
  const services = data.resources ? [
    {
      name: "Mobile / API host",
      available: true,
      cpu: data.resources.mobile?.cpu_utilization,
      memory: data.resources.mobile?.memory_utilization,
      active: null,
      completed: null,
      failed: null,
      note: "Host running the FastAPI backend",
    },
    {
      name: "Edge server",
      available: data.resources.edge?.available,
      cpu: data.resources.edge?.cpu_utilization,
      memory: data.resources.edge?.memory_utilization,
      active: data.resources.edge?.active_tasks ?? 0,
      completed: data.resources.edge?.completed_tasks ?? 0,
      failed: data.resources.edge?.failed_tasks ?? 0,
      note: "Low-latency edge tier (port 8001)",
    },
    {
      name: "Cloud server",
      available: data.resources.cloud?.available,
      cpu: data.resources.cloud?.cpu_utilization,
      memory: data.resources.cloud?.memory_utilization,
      active: data.resources.cloud?.active_tasks ?? 0,
      completed: data.resources.cloud?.completed_tasks ?? 0,
      failed: data.resources.cloud?.failed_tasks ?? 0,
      note: "High-capacity cloud tier (port 8002)",
    },
  ] : [];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setSection("Overview")}>
          <span className="brand-mark">M</span><span>MEC<span className="brand-muted"> / INTELLIGENCE</span></span>
        </a>
        <div className="sidebar-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV_ITEMS.map((item, index) => (
            <button key={item} className={section === item ? "nav-item active" : "nav-item"}
              onClick={() => setSection(item)}>
              <span className="nav-icon">{["◫", "▤", "⌁", "◉"][index]}</span>{item}
              {item === "Overview" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-indicator"><i /> Backend connection</div>
          <span className="api-address">{baseUrl}</span>
          <a href={`${baseUrl}/docs`} target="_blank" rel="noreferrer">Open API documentation ↗</a>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div><span className="eyebrow">MOBILE EDGE COMPUTING</span>
            <h1>{section === "Overview" ? "Control Center" : section}</h1></div>
          <div className="topbar-actions">
            <span className="live-pill">
              <i /> {data.comparison?.dqn_model_loaded ? "DQN Online (Trained)" : "Greedy Fallback"}
            </span>
            <button className="refresh-button" onClick={refresh} disabled={loading}>
              {loading ? "Refreshing…" : "↻  Refresh"}
            </button>
          </div>
        </header>

        {error && <div className="error-banner" role="alert">
          <span><strong>Unable to load dashboard data</strong><br />{error}</span>
          <button onClick={refresh}>Retry</button>
        </div>}
        {!error && loading && <div className="loading-banner">Loading performance, task history, and server resources…</div>}

        {section === "Overview" && (
          <>
            <div className="section-title">
              <div>
                <h2>System overview</h2>
                <p>Live workload outcomes, DQN decisions, and reproducible policy comparisons.</p>
              </div>
              <span className="date-chip">Seeded benchmark · 60 scenarios</span>
            </div>
            <div className="metrics-grid" style={{ gridTemplateColumns: "repeat(5, minmax(0, 1fr))" }}>
              <Metric label="Total tasks" value={data.performance?.total ?? 0}
                note="All submitted tasks" />
              <Metric label="Completed tasks" value={data.performance?.completed ?? 0}
                note="Successfully executed" color="green" />
              <Metric label="Pending tasks" value={data.performance?.pending ?? 0}
                note="Created or processing" color="orange" />
              <Metric label="Failed tasks" value={data.performance?.failed ?? 0}
                note="Processing or connection errors" color="pink" />
              <Metric label="Average execution time"
                value={data.performance?.average_execution_seconds == null
                  ? "—" : `${data.performance.average_execution_seconds.toFixed(3)} s`}
                note="Measured on execution host" color="blue" />
            </div>

            <div className="chart-grid">
              <ChartCard title="Policy comparison (Latency)" subtitle="Mean simulated latency across all 6 policies">
                {summary.length ? <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartSummary} margin={{ top: 10, right: 12, left: 0, bottom: 36 }}>
                    <CartesianGrid strokeDasharray="3 5" stroke="#27334a" vertical={false} />
                    <XAxis dataKey="policy" angle={-24} textAnchor="end" interval={0}
                      tick={{ fill: "#94a2bc", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#94a2bc", fontSize: 11 }} axisLine={false}
                      tickLine={false} unit=" s" />
                    <Tooltip contentStyle={{ background: "#18243a", border: "1px solid #2e3c56",
                      borderRadius: 9, color: "#eff3ff" }} />
                    <Bar dataKey="average_latency_seconds" name="Mean latency (s)" radius={[5, 5, 0, 0]}>
                      {chartSummary.map((entry, index) => <Cell key={entry.policy} fill={COLORS[index % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer> : <EmptyState text="Run a comparison to populate the chart." />}
              </ChartCard>
              <ChartCard title="Execution location distribution" subtitle="Tasks completed across Local, Edge, and Cloud">
                {distribution.length ? <ResponsiveContainer width="100%" height={280}>
                  <PieChart><Pie data={distribution} dataKey="value" nameKey="name" innerRadius={66}
                    outerRadius={100} paddingAngle={5} stroke="none">
                    {distribution.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
                  </Pie><Tooltip contentStyle={{ background: "#18243a", border: "1px solid #2e3c56",
                    borderRadius: 9, color: "#eff3ff" }} /><Legend wrapperStyle={{ color: "#a4b0c6" }} />
                  </PieChart>
                </ResponsiveContainer> : <EmptyState text="Execute tasks to see location distribution." />}
              </ChartCard>
            </div>

            <div className="lower-grid">
              <ChartCard title="Recent tasks" subtitle="Latest tasks persisted in SQLite">
                {data.tasks.length ? <div className="task-table-wrap"><table>
                  <thead><tr><th>Task</th><th>Type</th><th>Location</th><th>Duration</th><th>Status</th></tr></thead>
                  <tbody>{data.tasks.slice(0, 6).map((task) => <tr key={task.id}>
                    <td><strong>{task.name}</strong><small>{task.id.slice(0, 8)}</small></td>
                    <td>{task.task_type}</td>
                    <td><span className={`location-token ${task.execution_location || "local"}`} style={{ padding: "2px 8px", fontSize: 10 }}>{task.execution_location || "—"}</span></td>
                    <td>{task.execution_seconds ? `${task.execution_seconds.toFixed(3)} s` : "—"}</td>
                    <td><span className={`status-badge ${task.status}`}>{task.status}</span></td>
                  </tr>)}</tbody></table></div> : <EmptyState text="No tasks have been recorded yet." />}
              </ChartCard>
              <ChartCard title="Server infrastructure status" subtitle="Resource utilization reported by each tier">
                <div className="server-list">{services.map((server) => <div className="server-row" key={server.name}>
                  <span className={`server-icon ${server.available ? "online" : "offline"}`}>◉</span>
                  <div className="server-details"><div className="server-name">
                    <strong>{server.name}</strong><span className={server.available ? "status-online" : "status-offline"}>
                      {server.available ? "ONLINE" : "OFFLINE"}</span></div>
                    <div className="meter-label"><span>CPU</span>
                      <span>{server.cpu == null ? "—" : `${(server.cpu * 100).toFixed(0)}%`}</span></div>
                    <div className="meter"><i style={{ width: `${Math.min(100, (server.cpu || 0) * 100)}%` }} /></div>
                    <small>{server.active != null ? `${server.active} active · ${server.completed} completed · ${server.failed} failed` : server.note}</small>
                  </div>
                </div>)}</div>
              </ChartCard>
            </div>
            <p className="footnote">Latency and energy in strategy comparison are simulation estimates; execution durations are wall-clock measurements.</p>
          </>
        )}

        {section === "Tasks" && <TaskPage tasks={data.tasks} onRefresh={refresh} />}
        {section === "Monitoring" && <MonitoringPage resources={data.resources} services={services} />}
        {section === "Analytics" && <AnalyticsPage
          chartSummary={chartSummary} summary={summary}
          distribution={data.performance?.location_distribution || {}}
          decisionDistribution={data.performance?.decision_distribution || {}} />}
      </main>
    </div>
  );
}

function TaskPage({ tasks, onRefresh }) {
  const [type, setType] = useState("compute");
  const [file, setFile] = useState(null);
  const [cycles, setCycles] = useState("0.05");
  const [task, setTask] = useState(null);
  const [decision, setDecision] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [inspectedTask, setInspectedTask] = useState(null);

  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError(""); setDecision(null); setResult(null);
    try {
      let created;
      if (type === "compute") {
        const response = await fetch(`${baseUrl}/api/tasks/create`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_type: type, name: "Dashboard compute task",
            input_size_mb: 0.1, cpu_cycles_giga: Number(cycles) }),
        });
        if (!response.ok) throw new Error(await response.text());
        created = await response.json();
      } else {
        if (!file) throw new Error("Choose an image or document file first.");
        const form = new FormData();
        form.append("file", file);
        form.append("task_type", type);
        form.append("cpu_cycles_giga", cycles);
        const response = await fetch(`${baseUrl}/api/tasks/upload`, { method: "POST", body: form });
        if (!response.ok) throw new Error(await response.text());
        created = await response.json();
      }
      setTask(created);
      const decisionResponse = await fetch(`${baseUrl}/api/offloading/decide`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: created.id }),
      });
      if (!decisionResponse.ok) throw new Error(await decisionResponse.text());
      setDecision(await decisionResponse.json());
      await onRefresh();
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  async function execute() {
    setBusy(true); setError("");
    try {
      const response = await fetch(`${baseUrl}/api/offloading/execute`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: task.id }),
      });
      if (!response.ok) throw new Error(await response.text());
      setResult(await response.json());
      await onRefresh();
    } catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  }

  return (
    <>
      <div className="section-title"><div><h2>Task processing</h2>
        <p>Create real compute, image, or document workloads, inspect the DQN decision, then execute.</p></div></div>
      <div className="task-layout">
        <form className="panel task-form" onSubmit={submit}>
          <h2>New task submission</h2>
          <label>Workload type<select value={type} onChange={(event) => setType(event.target.value)}>
            <option value="compute">Compute (Repeated SHA-256)</option>
            <option value="image">Image recognition (MobileNetV2)</option>
            <option value="document">Document extraction (PDF/DOCX/TXT)</option></select></label>
          {type !== "compute" && <label>Input file<input type="file"
            accept={type === "image" ? "image/png,image/jpeg,image/webp,image/bmp" : ".pdf,.docx,.txt"}
            onChange={(event) => setFile(event.target.files?.[0] || null)} required /></label>}
          <label>CPU workload (Giga-cycles)<input type="number" min="0.001" max="2" step="0.01"
            value={cycles} onChange={(event) => setCycles(event.target.value)} required /></label>
          <button className="primary-button" disabled={busy}>{busy ? "Processing…" : "Create & decide"}</button>
          {error && <p className="inline-error" role="alert">{error}</p>}
        </form>
        <div className="panel workflow-panel"><h2>DQN offloading decision & execution</h2>
          {!decision && <EmptyState text="Create a task to calculate its 7-feature state and obtain a DQN offloading decision." />}
          {decision && <div className="decision-details">
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className={`location-token ${decision.location}`}>{decision.location}</span>
              <span style={{ color: "#9daac0", fontSize: 12 }}>Action: <strong>{decision.action}</strong> ({decision.location})</span>
            </div>
            <p>Policy: <strong>{decision.policy.replaceAll("_", " ")}</strong></p>
            <div className="decision-metrics">
              <span>Estimated latency<strong>{decision.estimated_latency_ms.toFixed(1)} ms</strong></span>
              <span>Estimated energy<strong>{decision.estimated_energy_joules.toFixed(2)} J</strong></span>
              <span>Predicted reward<strong>{decision.reward.toFixed(3)}</strong></span>
            </div>
            <button className="primary-button" onClick={execute} disabled={busy || result != null}>
              {result ? "Task completed successfully" : busy ? "Executing workload…" : `Execute on ${decision.location.toUpperCase()}`}
            </button>
          </div>}
          {result && <div className="result-box">
            <strong>Measured execution: {result.execution_seconds.toFixed(3)} s (Network: {result.network_seconds?.toFixed(3) || "0.000"} s)</strong>
            <pre>{JSON.stringify(result.result, null, 2)}</pre>
          </div>}
        </div>
      </div>

      <div className="panel task-list-panel">
        <h2>Task execution history</h2>
        {tasks.length ? <div className="task-table-wrap"><table><thead><tr>
          <th>Task ID</th><th>Name</th><th>Type</th><th>Execution location</th><th>Execution time</th><th>Status</th><th>Action</th>
        </tr></thead><tbody>{tasks.map((item) => <tr key={item.id}>
          <td><code style={{ color: "#8292ff", fontSize: 11 }}>{item.id.slice(0, 8)}</code></td>
          <td><strong>{item.name}</strong></td>
          <td>{item.task_type}</td>
          <td><span className={`location-token ${item.execution_location || "local"}`} style={{ padding: "3px 9px", fontSize: 10 }}>{item.execution_location || "Not decided"}</span></td>
          <td>{item.execution_seconds != null ? `${item.execution_seconds.toFixed(3)} s` : "—"}</td>
          <td><span className={`status-badge ${item.status}`}>{item.status}</span></td>
          <td>
            <button style={{ background: "#212e44", border: "1px solid #32435e", color: "#ccd6e6", borderRadius: 5, padding: "4px 8px", fontSize: 10 }}
              onClick={() => setInspectedTask(item)}>
              View result
            </button>
          </td>
        </tr>)}</tbody></table></div> : <EmptyState text="Task history is empty." />}
      </div>

      {inspectedTask && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(6, 10, 18, 0.75)", display: "grid", placeItems: "center", zIndex: 10 }}>
          <div className="panel" style={{ width: "90%", maxWidth: 650, maxHeight: "85vh", overflow: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h2>Task details: {inspectedTask.name}</h2>
              <button style={{ background: "transparent", border: 0, color: "#9daac0", fontSize: 16 }} onClick={() => setInspectedTask(null)}>✕</button>
            </div>
            <p style={{ color: "#9daac0", fontSize: 12 }}>ID: <code>{inspectedTask.id}</code></p>
            <p style={{ color: "#9daac0", fontSize: 12 }}>Status: <span className={`status-badge ${inspectedTask.status}`}>{inspectedTask.status}</span> · Location: <strong>{inspectedTask.execution_location || "—"}</strong></p>
            <p style={{ color: "#9daac0", fontSize: 12 }}>Execution time: <strong>{inspectedTask.execution_seconds ? `${inspectedTask.execution_seconds.toFixed(4)} s` : "—"}</strong> · Network: <strong>{inspectedTask.network_seconds ? `${inspectedTask.network_seconds.toFixed(4)} s` : "—"}</strong></p>
            <h3>Execution result:</h3>
            <pre style={{ background: "#0a111a", padding: 12, borderRadius: 8, overflow: "auto", fontSize: 11, color: "#8be9fd" }}>
              {JSON.stringify(inspectedTask.result || { message: "No result payload recorded" }, null, 2)}
            </pre>
            {inspectedTask.server_metrics && (
              <>
                <h3>Server metrics:</h3>
                <pre style={{ background: "#0a111a", padding: 12, borderRadius: 8, overflow: "auto", fontSize: 11, color: "#50fa7b" }}>
                  {JSON.stringify(inspectedTask.server_metrics, null, 2)}
                </pre>
              </>
            )}
            <button className="primary-button" style={{ marginTop: 12 }} onClick={() => setInspectedTask(null)}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}

function MonitoringPage({ resources, services }) {
  return (
    <>
      <div className="section-title"><div><h2>Server monitoring</h2>
        <p>Availability, host metrics, and active processing tasks across execution tiers.</p></div></div>
      <div className="server-grid">{services.map((server) => <article className="panel server-card" key={server.name}>
        <div className="server-name"><h2>{server.name}</h2><span className={server.available ? "status-online" : "status-offline"}>
          {server.available ? "ONLINE" : "OFFLINE"}</span></div>
        <p>CPU utilization <strong>{server.cpu == null ? "Unavailable" : `${(server.cpu * 100).toFixed(1)}%`}</strong></p>
        <p>Memory utilization <strong>{server.memory == null ? "Unavailable" : `${(server.memory * 100).toFixed(1)}%`}</strong></p>
        <p>Active tasks <strong>{server.active != null ? server.active : "—"}</strong></p>
        <p>Completed tasks <strong>{server.completed != null ? server.completed : "—"}</strong></p>
        <p>Failed tasks <strong>{server.failed != null ? server.failed : "—"}</strong></p>
      </article>)}</div>
      <div className="panel network-panel"><h2>Network simulation model</h2>
        <p>Configured latency <strong>{resources?.network?.latency_ms ?? "—"} ms</strong></p>
        <p>Configured bandwidth <strong>{resources?.network?.bandwidth_mbps ?? "—"} Mbps</strong></p>
        <small>{resources?.network?.source || "Not available"}</small></div>
    </>
  );
}

function AnalyticsPage({ chartSummary, summary, distribution, decisionDistribution }) {
  const [metric, setMetric] = useState("average_latency_seconds");
  const choices = {
    average_latency_seconds: "Average latency (seconds)",
    average_energy_joules: "Estimated energy (joules)",
    success_rate: "Simulated success rate",
    average_reward: "Average policy reward",
  };
  return (
    <>
      <div className="section-title"><div><h2>Performance analytics</h2>
        <p>Reproducible baseline comparisons and real execution distributions.</p></div></div>
      <div className="chart-grid analytics-charts">
        <ChartCard title="Policy comparison benchmark" subtitle={choices[metric]}>
          <label style={{ display: "flex", gap: 8, alignItems: "center", color: "#94a2bc", fontSize: 11, marginBottom: 8 }}>
            Metric:
            <select value={metric} onChange={(event) => setMetric(event.target.value)}
              style={{ background: "#18243a", color: "#e8edf7", border: "1px solid #33425a", borderRadius: 6, padding: 6 }}>
              {Object.entries(choices).map(([key, title]) =>
                <option key={key} value={key}>{title}</option>)}
            </select>
          </label>
          {summary.length ? <ResponsiveContainer width="100%" height={340}>
            <BarChart data={chartSummary} margin={{ top: 10, right: 12, left: 0, bottom: 52 }}>
              <CartesianGrid strokeDasharray="3 5" stroke="#27334a" vertical={false} />
              <XAxis dataKey="policy" angle={-28} textAnchor="end" interval={0}
                tick={{ fill: "#94a2bc", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#94a2bc", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#18243a", border: "1px solid #2e3c56",
                borderRadius: 9, color: "#eff3ff" }} />
              <Bar dataKey={metric} name={choices[metric]} fill="#6e82ff" radius={[4, 4, 0, 0]}>
                {chartSummary.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer> : <EmptyState text="No benchmark data is available." />}
        </ChartCard>
        <ChartCard title="Real execution location distribution" subtitle="Completed tasks grouped by execution location">
          {Object.keys(distribution).length ? <ResponsiveContainer width="100%" height={340}>
            <PieChart><Pie data={Object.entries(distribution).map(([name, value]) => ({ name, value }))}
              dataKey="value" nameKey="name" innerRadius={70} outerRadius={115}>
              {Object.keys(distribution).map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
            </Pie><Tooltip /><Legend /></PieChart>
          </ResponsiveContainer> : <EmptyState text="Run tasks to populate execution distribution." />}
        </ChartCard>
      </div>

      <div className="panel" style={{ marginTop: 15 }}>
        <h2>Baseline summary table</h2>
        <div className="task-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Policy</th>
                <th>Mean latency (s)</th>
                <th>Estimated energy (J)</th>
                <th>Success rate</th>
                <th>Mean reward</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((row) => (
                <tr key={row.policy}>
                  <td><strong>{row.policy.replaceAll("_", " ").toUpperCase()}</strong></td>
                  <td>{row.average_latency_seconds.toFixed(4)} s</td>
                  <td>{row.average_energy_joules.toFixed(4)} J</td>
                  <td>{(row.success_rate * 100).toFixed(1)}%</td>
                  <td>{row.average_reward.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="footnote">Latency and energy metrics in policy comparison are simulated over shared seeded environments.</p>
    </>
  );
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
