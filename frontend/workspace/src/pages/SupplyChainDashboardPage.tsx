import { useMemo, useState } from "react";
import { CatalogSection } from "../components/CatalogSection";

type QueueMode = "priority" | "all" | "agents";

interface FindingCard {
  id: string;
  severity: "Critical" | "High" | "Medium";
  reachability: "Reachable" | "Needs Review" | "Unreachable";
  packageName: string;
  version: string;
  fixedVersion: string;
  repo: string;
  path: string;
  epss: string;
  blastRadius: string;
  owner: string;
  summary: string;
  agentHint: string;
  mode: QueueMode[];
}

const kpis = [
  {
    label: "Reachable criticals",
    value: "12",
    delta: "-4 this week",
    detail: "Hot-path vulnerabilities with confirmed code usage.",
  },
  {
    label: "Dependencies under review",
    value: "47",
    delta: "9 blocked by upgrades",
    detail: "Packages waiting on triage, ownership, or remediation planning.",
  },
  {
    label: "Agent remediation plans",
    value: "18",
    delta: "6 ready for PR",
    detail: "Plans already decomposed into upgrade, refactor, and verification steps.",
  },
  {
    label: "Mean time to contain",
    value: "2.8d",
    delta: "Down from 4.1d",
    detail: "Time from scan detection to an accepted fix or temporary control.",
  },
];

const findings: FindingCard[] = [
  {
    id: "SC-219",
    severity: "Critical",
    reachability: "Reachable",
    packageName: "axios",
    version: "0.27.2",
    fixedVersion: "1.8.8",
    repo: "student-portal-web",
    path: "auth callback -> request proxy -> axios redirect handler",
    epss: "74%",
    blastRadius: "19 services",
    owner: "Frontend Platform",
    summary:
      "User-controlled redirect input can reach the vulnerable request flow in the production login path.",
    agentHint: "Analyzer agent already mapped the call path and proposed a safe upgrade window.",
    mode: ["priority", "all", "agents"],
  },
  {
    id: "SC-184",
    severity: "High",
    reachability: "Reachable",
    packageName: "jinja2",
    version: "3.0.1",
    fixedVersion: "3.1.6",
    repo: "teaching-assistant-api",
    path: "report export -> template rendering -> user notes interpolation",
    epss: "41%",
    blastRadius: "4 internal apps",
    owner: "Teaching Services",
    summary:
      "Template rendering path is exposed through document export, making the finding high priority despite limited surface area.",
    agentHint: "Upgrade planner suggests a direct bump with two template compatibility checks.",
    mode: ["priority", "all", "agents"],
  },
  {
    id: "SC-151",
    severity: "High",
    reachability: "Needs Review",
    packageName: "lodash",
    version: "4.17.20",
    fixedVersion: "4.17.21",
    repo: "course-ops-console",
    path: "legacy admin utilities",
    epss: "18%",
    blastRadius: "1 console",
    owner: "Admin Experience",
    summary:
      "The vulnerable helper appears in an old utility bundle, but runtime usage still needs validation.",
    agentHint: "Trace agent can inspect whether the bundle is still shipped to production.",
    mode: ["priority", "all"],
  },
  {
    id: "SC-088",
    severity: "Medium",
    reachability: "Unreachable",
    packageName: "urllib3",
    version: "1.26.6",
    fixedVersion: "2.2.2",
    repo: "grading-worker",
    path: "transitive via requests",
    epss: "3%",
    blastRadius: "2 batch jobs",
    owner: "Infra Enablement",
    summary:
      "The package is present but the vulnerable code path has not been observed in the grading worker execution graph.",
    agentHint: "Keep in the batch plan rather than interrupting the active remediation queue.",
    mode: ["all"],
  },
];

const dependencyPressure = [
  {
    repo: "student-portal-web",
    riskScore: 91,
    direct: 84,
    transitive: 421,
    hotspots: ["axios", "postcss", "ws"],
  },
  {
    repo: "teaching-assistant-api",
    riskScore: 78,
    direct: 52,
    transitive: 188,
    hotspots: ["jinja2", "cryptography", "requests"],
  },
  {
    repo: "course-ops-console",
    riskScore: 62,
    direct: 47,
    transitive: 201,
    hotspots: ["lodash", "vite", "esbuild"],
  },
];

const ecosystems = [
  {
    name: "npm",
    openFindings: 26,
    reachable: 9,
    note: "Most exposure comes from browser-facing paths and auth-adjacent packages.",
  },
  {
    name: "PyPI",
    openFindings: 14,
    reachable: 3,
    note: "Document generation and worker images drive the current Python backlog.",
  },
  {
    name: "Maven",
    openFindings: 7,
    reachable: 0,
    note: "Low urgency for now, but the graph is deep and deserves dependency path monitoring.",
  },
];

const agentLanes = [
  {
    name: "Analyzer Agent",
    status: "Live now",
    mission: "Confirms exploitability, maps dependency paths, and explains why a finding matters.",
    queue: ["axios redirect path", "legacy lodash usage", "transitive package clustering"],
  },
  {
    name: "Upgrade Planner Agent",
    status: "6 plans ready",
    mission: "Chooses safe target versions, estimates breaking change risk, and bundles fixes.",
    queue: ["jinja2 3.1.6 upgrade", "requests + urllib3 alignment", "lockfile refresh batch"],
  },
  {
    name: "PR Coordinator Agent",
    status: "2 drafts open",
    mission: "Creates implementation notes, generates PR context, and hands work to owners.",
    queue: ["student-portal-web patch PR", "TA API rollout checklist", "verification script draft"],
  },
];

const timelineItems = [
  {
    time: "09:10",
    title: "Managed scan completed for student-portal-web",
    detail: "4 reachable findings, 1 malicious package review request, dependency tree refreshed.",
  },
  {
    time: "10:25",
    title: "Analyzer agent published upgrade notes",
    detail: "Auth redirect issue narrowed to one production route and one internal testing hook.",
  },
  {
    time: "11:40",
    title: "Upgrade planner opened remediation batch draft",
    detail: "Grouped jinja2 and requests updates into a low-conflict release lane for backend services.",
  },
  {
    time: "13:05",
    title: "PR coordinator requested owner confirmation",
    detail: "Frontend Platform and Teaching Services were tagged for rollout sequencing.",
  },
];

function getSeverityClass(severity: FindingCard["severity"]) {
  if (severity === "Critical") return "severity-pill critical";
  if (severity === "High") return "severity-pill high";
  return "severity-pill medium";
}

function getReachabilityClass(reachability: FindingCard["reachability"]) {
  if (reachability === "Reachable") return "reachability-pill reachable";
  if (reachability === "Needs Review") return "reachability-pill review";
  return "reachability-pill unreachable";
}

export function SupplyChainDashboardPage() {
  const [queueMode, setQueueMode] = useState<QueueMode>("priority");

  const visibleFindings = useMemo(
    () => findings.filter((finding) => finding.mode.includes(queueMode)),
    [queueMode],
  );

  return (
    <section className="page-shell supply-page">
      <header className="hero-panel supply-hero">
        <div className="supply-hero-copy">
          <p className="workspace-eyebrow">Software Supply Chain</p>
          <h2 className="page-title">Agent-native risk triage for dependencies, not just findings</h2>
          <p className="page-copy">
            This dashboard borrows the fast signal density of supply chain scanners, then
            adds agents that explain reachability, cluster fixes, and prepare remediation
            work for humans.
          </p>
          <div className="tag-row">
            <span className="tag success">12 reachable criticals</span>
            <span className="tag">3 ecosystems</span>
            <span className="tag">18 agent plans in progress</span>
          </div>
          <div className="action-row">
            <button className="primary-button" type="button">
              Run agent triage
            </button>
            <button className="secondary-button" type="button">
              Create remediation batch
            </button>
          </div>
        </div>

        <div className="supply-hero-side">
          <div className="supply-signal-card">
            <span className="supply-signal-label">Current pressure point</span>
            <strong>Auth-facing JavaScript dependencies are driving the real risk</strong>
            <p>
              The dashboard is intentionally opinionated: reachable browser-path issues stay
              at the top, while low-signal transitive noise gets routed into agent-assisted
              batching.
            </p>
          </div>
          <div className="supply-highlight-list">
            <div className="supply-highlight-item">
              <strong>74% EPSS</strong>
              <span>Highest exploitability finding in active use.</span>
            </div>
            <div className="supply-highlight-item">
              <strong>6 safe upgrades</strong>
              <span>Already sequenced into low-conflict rollout windows.</span>
            </div>
            <div className="supply-highlight-item">
              <strong>2 draft PRs</strong>
              <span>Agent-generated change packs waiting for owner review.</span>
            </div>
          </div>
        </div>
      </header>

      <section className="supply-summary-grid">
        {kpis.map((item) => (
          <article key={item.label} className="supply-kpi-card">
            <div className="supply-kpi-label">{item.label}</div>
            <div className="supply-kpi-value">{item.value}</div>
            <div className="supply-kpi-delta">{item.delta}</div>
            <p>{item.detail}</p>
          </article>
        ))}
      </section>

      <div className="dashboard-grid supply-deck">
        <CatalogSection
          title="Priority Findings Queue"
          description="A working queue for the issues that should consume team attention right now."
        >
          <div className="queue-filter-row">
            <button
              className={queueMode === "priority" ? "nav-item active" : "nav-item"}
              onClick={() => setQueueMode("priority")}
              type="button"
            >
              Priority focus
            </button>
            <button
              className={queueMode === "all" ? "nav-item active" : "nav-item"}
              onClick={() => setQueueMode("all")}
              type="button"
            >
              All findings
            </button>
            <button
              className={queueMode === "agents" ? "nav-item active" : "nav-item"}
              onClick={() => setQueueMode("agents")}
              type="button"
            >
              Agent queue
            </button>
          </div>

          <div className="priority-list">
            {visibleFindings.map((finding) => (
              <article key={finding.id} className="priority-item">
                <div className="priority-item-head">
                  <div className="priority-item-title">
                    <strong>{finding.packageName}</strong>
                    <span>
                      {finding.repo} · {finding.id}
                    </span>
                  </div>
                  <div className="priority-pill-row">
                    <span className={getSeverityClass(finding.severity)}>{finding.severity}</span>
                    <span className={getReachabilityClass(finding.reachability)}>
                      {finding.reachability}
                    </span>
                  </div>
                </div>

                <p className="priority-summary">{finding.summary}</p>

                <div className="priority-metrics">
                  <div>
                    <span>Current version</span>
                    <strong>{finding.version}</strong>
                  </div>
                  <div>
                    <span>Fixed version</span>
                    <strong>{finding.fixedVersion}</strong>
                  </div>
                  <div>
                    <span>EPSS</span>
                    <strong>{finding.epss}</strong>
                  </div>
                  <div>
                    <span>Blast radius</span>
                    <strong>{finding.blastRadius}</strong>
                  </div>
                </div>

                <div className="priority-footnote">
                  <strong>Dependency path</strong>
                  <p>{finding.path}</p>
                </div>

                <div className="priority-footnote">
                  <strong>Agent note</strong>
                  <p>{finding.agentHint}</p>
                </div>

                <div className="tag-row">
                  <span className="tag">{finding.owner}</span>
                  <span className="tag">Fix candidate ready</span>
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>

        <CatalogSection
          title="Agent Remediation Desk"
          description="Our differentiator: findings do not stop at triage. Agents keep decomposing work until humans can act."
        >
          <div className="agent-lane-list">
            {agentLanes.map((lane) => (
              <article key={lane.name} className="agent-lane-card">
                <div className="agent-lane-head">
                  <div>
                    <h3>{lane.name}</h3>
                    <p>{lane.mission}</p>
                  </div>
                  <span className="tag success">{lane.status}</span>
                </div>
                <div className="agent-lane-queue">
                  {lane.queue.map((item) => (
                    <div key={item} className="agent-lane-task">
                      {item}
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>
      </div>

      <div className="dashboard-grid supply-deck">
        <CatalogSection
          title="Dependency Pressure Map"
          description="Repository-level pressure shows where reachability and graph depth combine into real operational drag."
        >
          <div className="pressure-grid">
            {dependencyPressure.map((item) => (
              <article key={item.repo} className="pressure-card">
                <div className="pressure-head">
                  <strong>{item.repo}</strong>
                  <span>Risk {item.riskScore}</span>
                </div>
                <div className="pressure-bar">
                  <div className="pressure-bar-fill" style={{ width: `${item.riskScore}%` }} />
                </div>
                <div className="pressure-stats">
                  <span>Direct {item.direct}</span>
                  <span>Transitive {item.transitive}</span>
                </div>
                <div className="tag-row">
                  {item.hotspots.map((hotspot) => (
                    <span key={hotspot} className="tag">
                      {hotspot}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>

        <CatalogSection
          title="Ecosystem Exposure"
          description="A compact view of where package manager risk is accumulating across the org."
        >
          <div className="ecosystem-list">
            {ecosystems.map((item) => (
              <article key={item.name} className="ecosystem-card">
                <div className="ecosystem-head">
                  <strong>{item.name}</strong>
                  <span>{item.openFindings} open findings</span>
                </div>
                <div className="ecosystem-metric">
                  <span>Reachable now</span>
                  <strong>{item.reachable}</strong>
                </div>
                <p>{item.note}</p>
              </article>
            ))}
          </div>
        </CatalogSection>
      </div>

      <div className="dashboard-grid supply-deck">
        <CatalogSection
          title="Recent Scan Activity"
          description="A dashboard should feel operational. This timeline makes scan-to-action flow visible."
        >
          <div className="scan-timeline">
            {timelineItems.map((item) => (
              <article key={`${item.time}-${item.title}`} className="scan-timeline-item">
                <div className="scan-timeline-time">{item.time}</div>
                <div className="scan-timeline-body">
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>

        <CatalogSection
          title="Why This View Is Different"
          description="The page is intentionally not a pure scanner clone. It keeps the scanning mental model, but shifts the product center toward agent execution."
        >
          <div className="difference-list">
            <article className="difference-card">
              <span>1</span>
              <strong>Observe</strong>
              <p>Findings, dependency paths, EPSS, and repo pressure still stay visible.</p>
            </article>
            <article className="difference-card">
              <span>2</span>
              <strong>Explain</strong>
              <p>Agents translate scanner output into human-readable exploitability and upgrade context.</p>
            </article>
            <article className="difference-card">
              <span>3</span>
              <strong>Execute</strong>
              <p>Remediation plans, rollout batches, and PR-ready artifacts become first-class UI objects.</p>
            </article>
          </div>
        </CatalogSection>
      </div>
    </section>
  );
}
