import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  FlaskConical,
  Globe2,
  LayoutDashboard,
  LogOut,
  Play,
  Plus,
  Radar,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Terminal,
  Trash2,
  Wallet,
  X,
} from "lucide-react";
import "./style.css";
type Config = {
  region: string;
  realms: string[];
  selling_realms: string[];
  budget_gold: number;
  max_item_gold: number;
  min_profit_gold: number;
  min_roi: number;
  fee_percent: number;
  deposit_gold: number;
  max_age_hours: number;
  max_context_age_hours: number;
  min_sold_day: number;
  max_sale_days: number;
  interval_minutes: number;
  retention_days: number;
  scheduled: boolean;
  tsm_enabled: boolean;
  blizzard_enabled: boolean;
  help_enabled: boolean;
};
type Source = {
  observed_at: string | null;
  id: string;
  status: string;
  last_success: string | null;
  last_attempt: string | null;
  rows: number;
  error: string | null;
};
type Job = {
  id: number;
  status: string;
  started: string;
  finished: string | null;
  message: string;
};
type Status = {
  version: string;
  database: string;
  schema: number;
  observations: number;
  data_bytes: number;
  disk_free: number;
  memory_bytes: number | null;
  uptime_seconds: number;
  worker: string;
  sources: Source[];
  jobs: Job[];
  blizzard_configured: boolean;
  addon_status: string;
  next_scan: number | null;
};
type Trade = {
  item_key: string;
  name: string;
  source_realm: string;
  destination_realm: string;
  buyout: number;
  estimated_sale: number;
  net_profit: number;
  roi: number;
  sold_day: number;
  confidence: string;
  risks: string[];
  explanation: string;
  observed_at: string;
};
type Material = {
  item_id: number;
  quantity: number;
  owned: number;
  unit_cost_gold: number | null;
};
type Recipe = {
  id: string;
  name: string;
  character: string;
  profession: string;
  output_item_id: number;
  crafts: number;
  expected_yield: number;
  sale_price_gold: number;
  concentration: number;
  baseline_profit_gold: number | null;
  materials: Material[];
  assumptions: string;
};
type Plan = {
  id: string;
  name: string;
  character: string;
  profession: string;
  status: string;
  crafts: number;
  economic_cost: number;
  cash_required: number;
  net_profit: number | null;
  concentration: number;
  profit_per_concentration: number | null;
  assumptions: string;
  materials: {
    item_id: number;
    required: number;
    missing: number;
    owned: number;
    unit_cost_gold: number;
    source: string;
  }[];
};
async function api<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const r = await fetch("/api/" + url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    if (r.status === 401) window.dispatchEvent(new Event("unauthorized"));
    const text = await r.text();
    let message = text;
    try {
      const d = JSON.parse(text).detail;
      message = typeof d === "string" ? d : JSON.stringify(d);
    } catch {}
    throw new Error(message || "Request failed");
  }
  return r.json();
}
const gold = (n: number) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(n) + " g";
const copper = (n: number) => gold(n / 10000);
const bytes = (n: number) =>
  n > 1e9 ? (n / 1e9).toFixed(1) + " GB" : (n / 1e6).toFixed(1) + " MB";
const date = (s: string | null) =>
  s ? new Date(s).toLocaleString() : "Not yet";
const realm = (s: string) =>
  s
    .split("-")
    .map((w) => w[0]?.toUpperCase() + w.slice(1))
    .join(" ");
const nav = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "opportunities", label: "Opportunity radar", icon: Radar },
  { id: "crafting", label: "Crafting planner", icon: FlaskConical },
  { id: "sources", label: "Data sources", icon: Database },
  { id: "system", label: "Server health", icon: Activity },
  { id: "settings", label: "Settings", icon: Settings2 },
  { id: "help", label: "Field guide", icon: CircleHelp },
];
function App() {
  const [authed, setAuthed] = useState<boolean | null>(null),
    [token, setToken] = useState(""),
    [page, setPage] = useState("overview");
  const [config, setConfig] = useState<Config | null>(null),
    [status, setStatus] = useState<Status | null>(null),
    [trades, setTrades] = useState<Trade[]>([]),
    [plans, setPlans] = useState<Plan[]>([]),
    [recipes, setRecipes] = useState<Recipe[]>([]);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState<Trade | null>(null),
    [history, setHistory] = useState<any[]>([]),
    [wizard, setWizard] = useState(
      Number(localStorage.getItem("lc-walkthrough") || 0),
    ),
    [tutorial, setTutorial] = useState(0);
  const [draft, setDraft] = useState<Config | null>(null),
    [realmInput, setRealmInput] = useState(""),
    [clientId, setClientId] = useState(""),
    [clientSecret, setClientSecret] = useState(""),
    [recipeJson, setRecipeJson] = useState("");
  async function load() {
    try {
      const [c, s, t, p, r] = await Promise.all([
        api<Config>("settings"),
        api<Status>("status"),
        api<Trade[]>("opportunities"),
        api<Plan[]>("crafting"),
        api<Recipe[]>("recipes"),
      ]);
      setConfig(c);
      setStatus(s);
      setTrades(t);
      setPlans(p);
      setRecipes(r);
      setAuthed(true);
      setDraft((d) => d || c);
      setWizard((w) => (w === 0 && c.realms.length === 0 ? 1 : w));
    } catch (e) {
      if (authed) setError((e as Error).message);
    }
  }
  useEffect(() => {
    const unauthorized = () => setAuthed(false);
    window.addEventListener("unauthorized", unauthorized);
    void load();
    return () => window.removeEventListener("unauthorized", unauthorized);
  }, []);
  useEffect(() => {
    if (!authed) return;
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [authed]);
  useEffect(() => {
    localStorage.setItem("lc-walkthrough", String(wizard));
  }, [wizard]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelected(null);
        if (wizard > 0) setWizard(-1);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [wizard]);
  useEffect(() => {
    if (notice) {
      const t = setTimeout(() => setNotice(""), 5000);
      return () => clearTimeout(t);
    }
  }, [notice]);
  async function action(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    try {
      await fn();
      setNotice(message);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(c: Config) {
    await api("settings", "PUT", c);
    setConfig(c);
    setDraft(c);
  }
  function download(endpoint: string) {
    window.location.assign("/api/" + endpoint);
  }
  async function openTrade(t: Trade) {
    setSelected(t);
    setHistory([]);
    try {
      setHistory(await api<any[]>("history/" + t.item_key));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (authed === null)
    return (
      <div className="login">
        <Radar size={40} />
        <p>Starting your command center…</p>
      </div>
    );
  if (!authed)
    return (
      <div className="login">
        <div className="login-card">
          <div className="brand-mark">
            <Radar />
          </div>
          <span className="eyebrow">WOW LAZYCRAWLER</span>
          <h1>
            Your market.
            <br />
            Your advantage.
          </h1>
          <p>
            Enter your local access token to open your auction intelligence
            workspace.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action(async () => {
                await api("login", "POST", { token });
                setToken("");
                await load();
              }, "Workspace unlocked");
            }}
          >
            <label>
              Access token
              <input
                autoFocus
                type="password"
                autoComplete="current-password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
            <button className="primary" disabled={busy}>
              Open workspace <ArrowRight size={16} />
            </button>
          </form>
          <small>
            Electron signs you in automatically. For browser access, find{" "}
            <code>admin-token</code> in your data folder.
          </small>
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    );
  if (!config || !status || !draft) return null;
  const filtered = trades.filter((t) =>
    (
      t.name +
      " " +
      t.item_key +
      " " +
      t.source_realm +
      " " +
      t.destination_realm
    )
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  const ready = status.sources.filter(
    (s) => s.status === "ready" || s.status === "unchanged",
  ).length;
  const stale = status.sources.filter(
    (s) =>
      s.observed_at &&
      Date.now() - new Date(s.observed_at).getTime() >
        (s.id.includes(":region:")
          ? config.max_context_age_hours
          : config.max_age_hours) *
          3600000,
  ).length;
  const title = nav.find((n) => n.id === page)?.label || "Overview";
  function num(key: keyof Config, label: string, unit: string, step = "1") {
    return (
      <label>
        {label}
        <div className="input-unit">
          <input
            type="number"
            min="0"
            step={step}
            value={String(draft![key])}
            onChange={(e) =>
              setDraft({ ...draft!, [key]: Number(e.target.value) })
            }
          />
          <span>{unit}</span>
        </div>
      </label>
    );
  }
  function scanButton() {
    return (
      <button
        className="primary"
        disabled={busy || status?.worker === "scanning"}
        onClick={() =>
          void action(() => api("scan", "POST"), "Market scan started")
        }
      >
        <RefreshCw
          size={15}
          className={status?.worker === "scanning" ? "spin" : ""}
        />
        {status?.worker === "scanning" ? "Scanning…" : "Scan markets"}
      </button>
    );
  }
  function tradeTable(list: Trade[]) {
    return list.length ? (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ITEM / MARKET</th>
              <th>BUY ON</th>
              <th>SELL ON</th>
              <th>ENTRY PRICE</th>
              <th>EST. NET</th>
              <th>ROI</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {list.map((t, i) => (
              <tr key={t.item_key + t.destination_realm}>
                <td>
                  <button
                    className="item-link"
                    onClick={() => void openTrade(t)}
                  >
                    <span className={"item-icon shade" + (i % 4)}>
                      {t.name.slice(0, 1)}
                    </span>
                    <span>
                      <strong>{t.name}</strong>
                      <small>
                        #{t.item_key} · {t.sold_day} regional sold/day
                      </small>
                    </span>
                  </button>
                </td>
                <td>{realm(t.source_realm)}</td>
                <td>{realm(t.destination_realm)}</td>
                <td>{copper(t.buyout)}</td>
                <td className="positive">+{copper(t.net_profit)}</td>
                <td>
                  <span className="roi">{t.roi}%</span>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={"Review " + t.name}
                    onClick={() => void openTrade(t)}
                  >
                    <ArrowUpRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty
        icon={<Radar />}
        title="Let the market come to you"
        text="Choose at least two realms and a selling realm, then run a scan. Candidates appear here when fresh evidence meets your risk limits."
        action={
          <button
            className="secondary"
            onClick={() => {
              setPage("sources");
            }}
          >
            Configure data sources <ArrowRight size={15} />
          </button>
        }
      />
    );
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Radar size={25} />
          </div>
          <div>
            LAZYCRAWLER<small>AUCTION INTELLIGENCE</small>
          </div>
        </div>
        <div className="workspace">
          <span className="dot" />
          <div>
            Personal workspace
            <small>{config.region.toUpperCase()} · WoW Retail</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav>
          {nav.map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "active" : ""}
              onClick={() => {
                setPage(n.id);
                setSearch("");
              }}
            >
              <n.icon size={18} />
              {n.label}
              {n.id === "crafting" && (
                <span className="nav-count">{recipes.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="engine">
            <span className="dot" />
            <span>
              Local engine
              <small>
                {status.worker === "scanning"
                  ? "Fetching snapshots"
                  : "Ready when you are"}
              </small>
            </span>
            <Activity size={16} />
          </div>
          <span className="version">
            v{status.version} <span>SELF-HOSTED</span>
          </span>
        </div>
      </aside>
      <div className="main">
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} /> <strong>{title}</strong>
          </div>
          <div className="header-right">
            <span className="local-tag">
              <ShieldCheck size={13} /> Local & private
            </span>
            <button
              className="icon-button"
              title="Sign out"
              onClick={() =>
                void action(async () => {
                  await api("logout", "POST");
                  setAuthed(false);
                }, "Signed out")
              }
            >
              <LogOut size={16} />
            </button>
            <span className="avatar">DD</span>
          </div>
        </header>
        <main>
          {error && (
            <div className="banner error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <Check size={16} />
              {notice}
            </div>
          )}
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {page === "overview"
                  ? "YOUR ECONOMIC COMMAND CENTER"
                  : "WOW LAZYCRAWLER / " + config.region.toUpperCase()}
              </span>
              <h1>
                {page === "overview"
                  ? "A clearer view of your next move."
                  : title}
              </h1>
              <p>
                {
                  (
                    {
                      overview:
                        "Market intelligence, crafting plans, and a little less guesswork.",
                      opportunities:
                        "Evidence first. Review the spread, the risk, and the route.",
                      crafting:
                        "Plan across professions. Know the cost before you craft.",
                      sources:
                        "Fresh data is the foundation of a good decision.",
                      system:
                        "A quiet engine. A clear picture of what’s happening.",
                      settings:
                        "Set the boundaries. Let the scanner do the searching.",
                      help: "Build your setup. Understand the numbers. Trade with intent.",
                    } as Record<string, string>
                  )[page]
                }
              </p>
            </div>
            {page === "overview" || page === "opportunities" ? (
              scanButton()
            ) : (
              <button
                className="secondary"
                onClick={() => void action(load, "Workspace refreshed")}
              >
                <RefreshCw size={15} />
                Refresh
              </button>
            )}
          </div>
          {page === "overview" && (
            <>
              {config.help_enabled && (
                <div className="intro-card">
                  <div className="intro-art">
                    <Radar size={72} />
                    <span className="orbit" />
                  </div>
                  <div>
                    <span className="eyebrow">
                      SMALL STEPS. SMARTER TRADES.
                    </span>
                    <h2>Your next opportunity starts with good data.</h2>
                    <p>
                      Connect your realms, set your limits, and build a plan.
                      <br />
                      Every candidate comes with the evidence behind it.
                    </p>
                    <button
                      className="light-button"
                      onClick={() => {
                        setWizard(1);
                        setTutorial(1);
                      }}
                    >
                      Walk me through it <ArrowRight size={15} />
                    </button>
                  </div>
                  <span className="intro-label">THE PATIENT TRADER’S EDGE</span>
                </div>
              )}
              <div className="stats">
                <Stat
                  label="Trading budget"
                  value={gold(config.budget_gold)}
                  sub="Your configured capital limit"
                  icon={<Wallet />}
                />
                <Stat
                  label="Market candidates"
                  value={String(trades.length)}
                  sub="Estimates awaiting your review"
                  icon={<Radar />}
                />
                <Stat
                  label="Connected markets"
                  value={String(config.realms.length)}
                  sub={`${ready} healthy data feeds`}
                  icon={<Globe2 />}
                />
                <Stat
                  label="Crafting plans"
                  value={String(plans.length)}
                  sub="Character-specific manual estimates"
                  icon={<FlaskConical />}
                />
              </div>
              <div className="section-title">
                <div>
                  <h2>
                    Opportunity radar{" "}
                    <span className="pill">{trades.length} candidates</span>
                  </h2>
                  <p>Conservative valuations. Transparent assumptions.</p>
                </div>
                <button
                  className="text-button"
                  onClick={() => setPage("opportunities")}
                >
                  Explore all <ArrowRight size={15} />
                </button>
              </div>
              <section className="panel">
                {tradeTable(trades.slice(0, 6))}
              </section>
              <div className="two-col bottom-cards">
                <section className="panel padded">
                  <div className="section-title">
                    <h2>
                      <Database size={17} /> Data pulse
                    </h2>
                    <span className={"pill " + (stale ? "amber" : "")}>
                      {stale
                        ? "Check freshness"
                        : ready
                          ? "Connected"
                          : "Awaiting first scan"}
                    </span>
                  </div>
                  <div className="pulse-row">
                    <span>TradeSkillMaster public data</span>
                    <strong>{config.tsm_enabled ? "Enabled" : "Paused"}</strong>
                  </div>
                  <div className="pulse-row">
                    <span>Blizzard Game Data</span>
                    <strong>
                      {config.blizzard_enabled ? "Enabled" : "Optional"}
                    </strong>
                  </div>
                  <div className="pulse-row">
                    <span>Scheduled scanning</span>
                    <strong>
                      {config.scheduled
                        ? `Every ${config.interval_minutes} min`
                        : "Manual"}
                    </strong>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setPage("sources")}
                  >
                    Manage sources <ArrowRight size={14} />
                  </button>
                </section>
                <section className="panel padded craft-promo">
                  <FlaskConical className="promo-icon" size={32} />
                  <span className="eyebrow">CRAFT WITH A PLAN</span>
                  <h2>Turn materials into possibilities.</h2>
                  <p>
                    Compare economic cost, missing reagents, and concentration
                    value across your crafting plans.
                  </p>
                  <button
                    className="secondary"
                    onClick={() => setPage("crafting")}
                  >
                    Open crafting planner <ArrowRight size={15} />
                  </button>
                </section>
              </div>
            </>
          )}
          {page === "opportunities" && (
            <>
              <div className="toolbar">
                <div className="search">
                  <Search size={17} />
                  <input
                    placeholder="Search items, IDs, or realms…"
                    aria-label="Search candidates"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                <span className="pill amber">Estimates · verify in game</span>
                <button
                  className="secondary"
                  onClick={() => download("export")}
                >
                  <ArrowDownToLine size={15} />
                  Export plan
                </button>
              </div>
              <section className="panel">{tradeTable(filtered)}</section>
              <Info title="How candidates are ranked">
                We cap the resale estimate against historical and regional
                evidence, reserve 10% for pricing uncertainty, deduct your fees,
                and rank by profit with a regional demand weight. Unknown
                transfer eligibility remains a review requirement. This is a
                candidate list, not a budget-allocated purchase queue.
              </Info>
            </>
          )}
          {page === "sources" && (
            <>
              <div className="two-col">
                <section className="panel padded">
                  <div className="section-title">
                    <h2>
                      <Globe2 size={18} /> Your markets
                    </h2>
                    <span className="pill">{draft.realms.length} / 30</span>
                  </div>
                  <label>
                    Region
                    <select
                      value={draft.region}
                      onChange={(e) =>
                        setDraft({
                          ...draft,
                          region: e.target.value,
                          realms: [],
                          selling_realms: [],
                        })
                      }
                    >
                      {["us", "eu", "kr", "tw"].map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                  </label>
                  <form
                    className="inline-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      const r = realmInput.trim().toLowerCase();
                      if (r && !draft.realms.includes(r)) {
                        setDraft({ ...draft, realms: [...draft.realms, r] });
                        setRealmInput("");
                      }
                    }}
                  >
                    <label>
                      Realm URL slug
                      <input
                        placeholder="e.g. area-52"
                        value={realmInput}
                        onChange={(e) => setRealmInput(e.target.value)}
                      />
                    </label>
                    <button className="secondary">
                      <Plus size={16} />
                      Add
                    </button>
                  </form>
                  <p className="muted">
                    Mark realms where you have a selling character.
                  </p>
                  <div className="realm-list">
                    {draft.realms.map((r) => (
                      <div key={r}>
                        <Globe2 size={16} />
                        <strong>{realm(r)}</strong>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={draft.selling_realms.includes(r)}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                selling_realms: e.target.checked
                                  ? [...draft.selling_realms, r]
                                  : draft.selling_realms.filter((x) => x !== r),
                              })
                            }
                          />
                          Selling
                        </label>
                        <button
                          className="icon-button"
                          aria-label={"Remove " + r}
                          onClick={() =>
                            setDraft({
                              ...draft,
                              realms: draft.realms.filter((x) => x !== r),
                              selling_realms: draft.selling_realms.filter(
                                (x) => x !== r,
                              ),
                            })
                          }
                        >
                          <X size={15} />
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    className="primary"
                    disabled={busy}
                    onClick={() =>
                      void action(() => save(draft), "Market preferences saved")
                    }
                  >
                    Save markets <Check size={15} />
                  </button>
                </section>
                <section className="panel padded">
                  <h2>
                    <Database size={18} /> Data connections
                  </h2>
                  <Toggle
                    label="TSM public CSV feeds"
                    detail="Realm prices, commodities, and regional demand. No key required."
                    checked={draft.tsm_enabled}
                    change={(v) => setDraft({ ...draft, tsm_enabled: v })}
                  />
                  <Toggle
                    label="Blizzard auction snapshots"
                    detail="Exact auction identities and connected-realm discovery. Credentials required."
                    checked={draft.blizzard_enabled}
                    change={(v) => setDraft({ ...draft, blizzard_enabled: v })}
                  />
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void action(async () => {
                        await api("credentials", "PUT", {
                          client_id: clientId,
                          client_secret: clientSecret,
                        });
                        setClientId("");
                        setClientSecret("");
                      }, "Blizzard credentials saved");
                    }}
                  >
                    <label>
                      Blizzard client ID
                      <input
                        autoComplete="off"
                        value={clientId}
                        onChange={(e) => setClientId(e.target.value)}
                        required
                      />
                    </label>
                    <label>
                      Client secret
                      <input
                        type="password"
                        autoComplete="new-password"
                        value={clientSecret}
                        onChange={(e) => setClientSecret(e.target.value)}
                        required
                      />
                    </label>
                    <div className="toolbar">
                      <button className="secondary" disabled={busy}>
                        Save credentials
                      </button>
                      <span className="muted">
                        {status.blizzard_configured
                          ? "Credentials stored"
                          : "Not configured"}
                      </span>
                    </div>
                  </form>
                  <small className="muted">
                    Stored with owner-only permissions; never returned to the
                    dashboard. Enable the source and save markets to activate.
                  </small>
                </section>
              </div>
              <div className="section-title">
                <h2>Ingestion feeds</h2>
                {scanButton()}
              </div>
              <section className="panel">
                {status.sources.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>SOURCE</th>
                          <th>STATE</th>
                          <th>ROWS</th>
                          <th>UPSTREAM SCAN / LAST FETCH</th>
                        </tr>
                      </thead>
                      <tbody>
                        {status.sources.map((s) => (
                          <tr key={s.id}>
                            <td>
                              <strong>{s.id}</strong>
                              {s.error && (
                                <small className="error-text">{s.error}</small>
                              )}
                            </td>
                            <td>
                              <span
                                className={
                                  "pill " +
                                  (s.status === "error" ? "amber" : "")
                                }
                              >
                                {s.status}
                              </span>
                            </td>
                            <td>{s.rows.toLocaleString()}</td>
                            <td>
                              {date(s.observed_at)}
                              <small>Fetched {date(s.last_success)}</small>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    icon={<Database />}
                    title="A clean slate"
                    text="Save your markets and run a scan to create your first snapshots."
                  />
                )}
              </section>
              <Info title="Fetch time and scan time are different">
                A successful fetch does not make an old price fresh. Candidate
                filtering uses the upstream observation timestamp. TSM realm
                files update every few hours; regional context updates daily.
                HTTP validators avoid reprocessing unchanged feeds.
              </Info>
            </>
          )}
          {page === "settings" && (
            <>
              <div className="two-col">
                <section className="panel padded">
                  <h2>
                    <Wallet size={18} /> Capital & returns
                  </h2>
                  <div className="form-grid">
                    {num("budget_gold", "Available trading budget", "gold")}
                    {num("max_item_gold", "Maximum per item", "gold")}
                    {num("min_profit_gold", "Minimum net profit", "gold")}
                    {num("min_roi", "Minimum return", "%")}
                    {num("fee_percent", "Auction house cut", "%", ".1")}
                    {num(
                      "deposit_gold",
                      "Deposit / relisting reserve",
                      "gold",
                      ".1",
                    )}
                  </div>
                </section>
                <section className="panel padded">
                  <h2>
                    <ShieldCheck size={18} /> Evidence & freshness
                  </h2>
                  <div className="form-grid">
                    {num("max_age_hours", "Maximum price age", "hours")}
                    {num(
                      "max_context_age_hours",
                      "Regional context age",
                      "hours",
                    )}
                    {num(
                      "min_sold_day",
                      "Minimum regional sold/day",
                      "units",
                      ".001",
                    )}
                    {num(
                      "max_sale_days",
                      "Maximum inverse regional demand",
                      "days",
                    )}
                    {num("retention_days", "Price history retention", "days")}
                  </div>
                  <p className="muted">
                    Inverse regional demand is a filter, not a realm
                    time-to-sale forecast.
                  </p>
                </section>
                <section className="panel padded">
                  <h2>
                    <Activity size={18} /> Background scanning
                  </h2>
                  <Toggle
                    label="Scheduled ingestion"
                    detail="The application or headless server must remain running."
                    checked={draft.scheduled}
                    change={(v) => setDraft({ ...draft, scheduled: v })}
                  />
                  {num(
                    "interval_minutes",
                    "Scan interval (minimum 60)",
                    "minutes",
                  )}
                  <Toggle
                    label="Contextual guidance"
                    detail="Show dashboard introduction and setup guidance."
                    checked={draft.help_enabled}
                    change={(v) => setDraft({ ...draft, help_enabled: v })}
                  />
                </section>
                <section className="panel padded">
                  <h2>
                    <ArrowDownToLine size={18} /> Take your workspace with you
                  </h2>
                  <p className="muted">
                    Download a consistent database backup. It contains settings,
                    history, and plans; credentials and login tokens are
                    excluded.
                  </p>
                  <button
                    className="secondary"
                    onClick={() => download("backup")}
                  >
                    Download database backup
                  </button>
                  <p className="muted">
                    For a full migration, quit LazyCrawler and copy its data
                    folder. See the field guide for paths and restoration.
                  </p>
                </section>
              </div>
              <div className="save-bar">
                <span>Changes take effect after saving.</span>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    void action(() => save(draft), "Settings saved")
                  }
                >
                  Save settings <Check size={16} />
                </button>
              </div>
            </>
          )}
          {page === "system" && (
            <>
              <div className="stats">
                <Stat
                  label="Worker"
                  value={status.worker}
                  sub="One ingestion job at a time"
                  icon={<Activity />}
                />
                <Stat
                  label="Database"
                  value={bytes(status.data_bytes)}
                  sub={"SQLite · schema " + status.schema}
                  icon={<Database />}
                />
                <Stat
                  label="Free disk"
                  value={bytes(status.disk_free)}
                  sub="On the data volume"
                  icon={<Terminal />}
                />
                <Stat
                  label="Backend memory"
                  value={
                    status.memory_bytes
                      ? bytes(status.memory_bytes)
                      : "Unavailable"
                  }
                  sub={
                    "Up " + Math.floor(status.uptime_seconds / 60) + " minutes"
                  }
                  icon={<Activity />}
                />
              </div>
              <section className="panel padded">
                <h2>Service connections</h2>
                <div className="pulse-row">
                  <span>Database</span>
                  <span className="pill">{status.database}</span>
                </div>
                <div className="pulse-row">
                  <span>Addon / companion</span>
                  <span className="muted">{status.addon_status}</span>
                </div>
                <div className="pulse-row">
                  <span>Next scheduled scan</span>
                  <span>
                    {config.scheduled && status.next_scan
                      ? date(new Date(status.next_scan * 1000).toISOString())
                      : config.scheduled
                        ? "At next scheduler tick"
                        : "Scheduling disabled"}
                  </span>
                </div>
              </section>
              <div className="section-title">
                <h2>Recent scan jobs</h2>
                {scanButton()}
              </div>
              <section className="panel">
                {status.jobs.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>JOB</th>
                          <th>STARTED</th>
                          <th>STATUS</th>
                          <th>DETAILS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {status.jobs.map((j) => (
                          <tr key={j.id}>
                            <td>#{j.id}</td>
                            <td>{date(j.started)}</td>
                            <td>
                              <span
                                className={
                                  "pill " +
                                  (j.status === "error" ? "amber" : "")
                                }
                              >
                                {j.status}
                              </span>
                            </td>
                            <td className="job-message">{j.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    icon={<Activity />}
                    title="All quiet here"
                    text="Scan runs and recoverable errors appear here after your first ingestion job."
                  />
                )}
              </section>
            </>
          )}
          {page === "crafting" && (
            <>
              <Info title="Crafting is a first-class workflow">
                This milestone supports explicit recipe estimates and material
                shopping plans. Import character-specific yield, quality, and
                concentration values manually from your verified simulation.
                Live CraftSim, Knowledge planning, orders, dependency graphs,
                and Auctionator exchange arrive with later addon work.
              </Info>
              <div className="two-col">
                <section className="panel padded">
                  <h2>
                    <Plus size={18} /> Add or update a recipe plan
                  </h2>
                  <p className="muted">
                    Use the template, enter your recipe’s actual materials and
                    simulated output, then save. Quality-specific reagent IDs
                    remain distinct.
                  </p>
                  <button
                    className="text-button"
                    onClick={() =>
                      setRecipeJson(
                        JSON.stringify(
                          {
                            id: "my-plan",
                            name: "My crafting plan",
                            character: "Hanami",
                            profession: "Alchemy",
                            output_item_id: 1,
                            crafts: 1,
                            expected_yield: 1,
                            sale_price_gold: 0,
                            concentration: 0,
                            baseline_profit_gold: null,
                            materials: [
                              {
                                item_id: 1,
                                quantity: 1,
                                owned: 0,
                                unit_cost_gold: null,
                              },
                            ],
                            assumptions:
                              "Manual estimate. Replace IDs, prices, and yield with verified values.",
                          },
                          null,
                          2,
                        ),
                      )
                    }
                  >
                    Load editable template <ArrowRight size={14} />
                  </button>
                  <label>
                    Recipe JSON
                    <textarea
                      className="code-input"
                      rows={14}
                      value={recipeJson}
                      onChange={(e) => setRecipeJson(e.target.value)}
                      placeholder="Paste a recipe plan…"
                      spellCheck={false}
                    />
                  </label>
                  <button
                    className="primary"
                    disabled={busy || !recipeJson}
                    onClick={() =>
                      void action(async () => {
                        const r = JSON.parse(recipeJson);
                        await api(
                          "recipes/" + encodeURIComponent(r.id),
                          "PUT",
                          r,
                        );
                        setRecipeJson("");
                      }, "Crafting plan saved")
                    }
                  >
                    Save recipe plan <Check size={15} />
                  </button>
                </section>
                <section className="panel padded">
                  <h2>
                    <FlaskConical size={18} /> Production queue
                  </h2>
                  {plans.length ? (
                    plans.map((p) => (
                      <div className="recipe-card" key={p.id}>
                        <div className="section-title">
                          <div>
                            <h3>{p.name}</h3>
                            <small>
                              {p.character} · {p.profession} · {p.crafts} crafts
                            </small>
                          </div>
                          <button
                            className="icon-button"
                            aria-label={"Delete " + p.name}
                            onClick={() =>
                              void action(
                                () => api("recipes/" + p.id, "DELETE"),
                                "Recipe removed",
                              )
                            }
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                        {p.net_profit === null ? (
                          <span className="pill amber">
                            Missing reagent prices
                          </span>
                        ) : (
                          <>
                            <div className="pulse-row">
                              <span>Economic material cost</span>
                              <strong>{gold(p.economic_cost)}</strong>
                            </div>
                            <div className="pulse-row">
                              <span>Cash for missing materials</span>
                              <strong>{gold(p.cash_required)}</strong>
                            </div>
                            <div className="pulse-row">
                              <span>Estimated net profit</span>
                              <strong
                                className={
                                  p.net_profit >= 0 ? "positive" : "error-text"
                                }
                              >
                                {gold(p.net_profit)}
                              </strong>
                            </div>
                            <div className="pulse-row">
                              <span>Incremental profit / concentration</span>
                              <strong>
                                {p.profit_per_concentration === null
                                  ? "Baseline required"
                                  : gold(p.profit_per_concentration)}
                              </strong>
                            </div>
                            <details>
                              <summary>Material shopping plan</summary>
                              {p.materials.map((m) => (
                                <div className="pulse-row" key={m.item_id}>
                                  <span>
                                    Item #{m.item_id}
                                    <small>{m.source}</small>
                                  </span>
                                  <strong>
                                    {m.missing} to buy / {m.required} required
                                  </strong>
                                </div>
                              ))}
                            </details>
                            <small>{p.assumptions}</small>
                          </>
                        )}
                        <button
                          className="text-button"
                          onClick={() =>
                            setRecipeJson(
                              JSON.stringify(
                                recipes.find((r) => r.id === p.id),
                                null,
                                2,
                              ),
                            )
                          }
                        >
                          Edit plan
                        </button>
                      </div>
                    ))
                  ) : (
                    <Empty
                      icon={<FlaskConical />}
                      title="Make room for your next craft"
                      text="Add a verified recipe estimate to calculate material needs and profit."
                    />
                  )}
                </section>
              </div>
              <button className="secondary" onClick={() => download("export")}>
                <ArrowDownToLine size={15} />
                Export crafting & trading plan
              </button>
            </>
          )}
          {page === "help" && (
            <>
              <div className="two-col">
                <section className="panel padded">
                  <span className="eyebrow">GET ORIENTED</span>
                  <h2>A short path to your first scan.</h2>
                  <p>
                    Choose markets, configure your budget, and review evidence
                    before spending gold.
                  </p>
                  <button
                    className="primary"
                    onClick={() => {
                      setWizard(1);
                      setTutorial(1);
                    }}
                  >
                    Replay setup walkthrough <Play size={15} />
                  </button>
                </section>
                <section className="panel padded">
                  <span className="eyebrow">DESKTOP LIFECYCLE</span>
                  <h2>Open. Scan. Close when done.</h2>
                  <p>
                    Electron starts its own local backend and signs you in.
                    Closing the window stops that backend. For continuous
                    scheduled ingestion, run the separate headless service.
                  </p>
                </section>
              </div>
              {[
                [
                  "Where is my data on Fedora?",
                  "By default: ~/.local/share/wowlazycrawler. XDG_DATA_HOME and LAZYCRAWLER_DATA overrides are supported. The RPM application is separate from your data. backend.log contains startup diagnostics.",
                ],
                [
                  "How do I move to a new computer?",
                  "Quit the application on both computers. Copy the entire data folder to the same location on the new machine, then install and launch the RPM. Credentials and your token are sensitive: transfer privately. Do not copy the Python virtual environment.",
                ],
                [
                  "How do I restore a downloaded backup?",
                  "Quit all LazyCrawler processes. Move your current data folder to a safe backup location. Create a new data folder, place the downloaded database inside as crawler.sqlite, and restart. Re-enter Blizzard credentials. A new access token is generated automatically.",
                ],
                [
                  "What does estimated net profit mean?",
                  "A conservative resale estimate minus purchase cost, the configured auction cut, and the deposit reserve. It excludes uncertain sale timing and is not realized profit. Regional daily sales are not per-realm demand.",
                ],
                [
                  "Why are there no candidates?",
                  "Use two or more separate auction markets, mark a selling realm, and run a scan. Stale prices, insufficient regional sales, budget limits, and conservative valuation caps can eliminate every candidate. Check ingestion errors and Settings.",
                ],
                [
                  "What connects to WoW right now?",
                  "Nothing reads or writes your game files in this milestone. Planning exports are versioned JSON for inspection. Addon and companion work will use a supported, validated exchange; SavedVariables must never be overwritten while WoW is running.",
                ],
                [
                  "What about CraftSim and Auctionator?",
                  "Recipe estimates can be entered manually now. Their supported APIs and installed versions will be verified before addon integration. The server does not invent character stats, Knowledge, recipes, or live crafting orders.",
                ],
              ].map(([q, a]) => (
                <details className="panel faq" key={q}>
                  <summary>{q}</summary>
                  <p>{a}</p>
                </details>
              ))}
            </>
          )}
          <footer>
            <span>
              <ShieldCheck size={12} /> Your data stays on your machine.
            </span>
            <span>
              Made for the long game. <span className="footer-dot">✦</span>
            </span>
          </footer>
        </main>
      </div>
      {selected && (
        <div className="overlay" onClick={() => setSelected(null)}>
          <section
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Candidate details"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close icon-button"
              aria-label="Close details"
              onClick={() => setSelected(null)}
            >
              <X />
            </button>
            <span className="eyebrow">
              CANDIDATE REVIEW · #{selected.item_key}
            </span>
            <h1>{selected.name}</h1>
            <p>
              {realm(selected.source_realm)} <ArrowRight size={15} />{" "}
              {realm(selected.destination_realm)}
            </p>
            <div className="detail-profit positive">
              +{copper(selected.net_profit)}
            </div>
            <small>Estimated net · {selected.roi}% ROI</small>
            <div className="pulse-row">
              <span>Entry snapshot</span>
              <strong>{copper(selected.buyout)}</strong>
            </div>
            <div className="pulse-row">
              <span>Conservative sale estimate</span>
              <strong>{copper(selected.estimated_sale)}</strong>
            </div>
            <div className="pulse-row">
              <span>Oldest supporting observation</span>
              <strong>{date(selected.observed_at)}</strong>
            </div>
            <h3>Why this surfaced</h3>
            <p>{selected.explanation}</p>
            <h3>Check before you act</h3>
            <ul>
              {selected.risks.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <h3>Stored price observations</h3>
            <div className="history-list">
              {history.length ? (
                history.slice(0, 20).map((h, i) => (
                  <div className="pulse-row" key={i}>
                    <span>
                      {h.realm || h.scope}
                      <small>{date(h.observed_at)}</small>
                    </span>
                    <strong>{copper(h.buyout || h.market)}</strong>
                  </div>
                ))
              ) : (
                <p>No stored history yet.</p>
              )}
            </div>
          </section>
        </div>
      )}
      {wizard > 0 && (
        <div className="overlay">
          <section
            className="wizard"
            role="dialog"
            aria-modal="true"
            aria-labelledby="wizard-title"
          >
            <button
              className="close icon-button"
              aria-label="Skip setup"
              onClick={() => setWizard(-1)}
            >
              <X size={20} />
            </button>
            <div className="steps">
              {[1, 2, 3].map((s) => (
                <span key={s} className={wizard >= s ? "done" : ""} />
              ))}
            </div>
            <span className="eyebrow">SETUP / {wizard} OF 3</span>
            <h1 id="wizard-title">
              {
                [
                  "",
                  "Meet your market workspace.",
                  "Choose your auction markets.",
                  "Make the limits yours.",
                ][wizard]
              }
            </h1>
            <p>
              {
                [
                  "",
                  "Your local engine turns market snapshots into explainable trading candidates and crafting plans. Start small, verify in game, and keep capital moving.",
                  "Add at least two realm slugs in Data sources. Mark where you have a selling character. Regional commodities are shared across all realms.",
                  "Set your budget and risk limits in Settings, then run a scan. You can replay this walkthrough from the field guide at any time.",
                ][wizard]
              }
            </p>
            <div className="wizard-tip">
              <Sparkles size={20} />
              <span>
                {
                  [
                    "",
                    "No subscription. No fabricated sales. Your own data, on your own machine.",
                    "Example slugs: area-52 and stormrage. Connected realms share an auction house.",
                    "Start with a small purchase limit. Price snapshots can change before you reach the auction house.",
                  ][wizard]
                }
              </span>
            </div>
            <div className="toolbar">
              <button className="text-button" onClick={() => setWizard(-1)}>
                Skip for now
              </button>
              <button
                className="primary"
                onClick={() => {
                  if (wizard < 3) setWizard(wizard + 1);
                  else {
                    setWizard(-1);
                    setPage("sources");
                    setTutorial(tutorial + 1);
                  }
                }}
              >
                {wizard === 3 ? "Set up my markets" : "Continue"}
                <ArrowRight size={16} />
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
function Stat({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
}) {
  return (
    <section className="stat panel">
      <div>
        {label}
        <span>{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{sub}</small>
    </section>
  );
}
function Empty({
  icon,
  title,
  text,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">{icon}</span>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
function Info({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <aside className="info">
      <CircleHelp size={19} />
      <div>
        <strong>{title}</strong>
        <p>{children}</p>
      </div>
    </aside>
  );
}
function Toggle({
  label,
  detail,
  checked,
  change,
}: {
  label: string;
  detail: string;
  checked: boolean;
  change: (v: boolean) => void;
}) {
  return (
    <label className="toggle-row">
      <span>
        <strong>{label}</strong>
        <small>{detail}</small>
      </span>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => change(e.target.checked)}
      />
    </label>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
