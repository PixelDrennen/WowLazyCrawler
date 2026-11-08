import React, { useEffect, useState, useId } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Clock3,
  Database,
  FlaskConical,
  FolderOpen,
  Globe2,
  House,
  Inbox,
  LayoutDashboard,
  LogOut,
  Package,
  Play,
  PlugZap,
  Radar,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Users,
  Wallet,
  X,
  TreePine,
  Link2,
  TriangleAlert,
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
  demo_mode: boolean;
  coverage_mode: string;
  wow_path: string;
  companion_enabled: boolean;
  theme: string;
  scan_concurrency: number;
};
type Capture = {
  observed_at: number;
  count?: number;
  money: number;
  complete: boolean;
  note?: string;
  items: { item_id: number; count: number; name?: string; cod?: boolean }[];
};
type Character = {
  id: string;
  account_id: string;
  name: string;
  realm: string;
  class_name: string;
  level: number;
  professions: string[];
  last_sync: string;
  captures: Record<string, Capture>;
};
type Market = {
  connected_id: number;
  representative: string;
  name: string;
  realms: { name: string; slug: string }[];
  owned: boolean;
  characters: string[];
  status: string;
  observations: number;
  updated_at: string | null;
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
  source_covered: boolean;
  destination_covered: boolean;
  observed_at: string;
  category?: string;
};
type Craft = {
  id: string;
  name: string;
  character: string;
  profession: string;
  category: string;
  crafts: number;
  economic_cost: number | null;
  cash_required: number | null;
  net_profit: number | null;
  status: string;
  materials: {
    item_id: number;
    required: number;
    owned: number | null;
    missing: number | null;
  }[];
  assumptions: string;
  estimated_gather_minutes?: number;
  lumber?: string;
  lumber_missing?: number;
};
type Rate = {
  item_id: number;
  name?: string;
  zone: string;
  source: string;
  quantity: number;
  seconds: number;
  samples: number;
  per_hour: number;
};
type Task = {
  id: string;
  name?: string;
  character?: string;
  state: string;
  from_realm?: string;
  to_realm?: string;
  net_profit?: number;
};
type Point = {
  at: string;
  observations?: number;
  healthy?: number;
  inventory_gold?: number;
  queue_profit?: number;
  syncs?: number;
  failed?: number;
};
type Feed = {
  id: string;
  status: string;
  rows: number;
  observed_at: string | null;
  last_success: string | null;
  error: string | null;
};
type Service = {
  version: string;
  database: string;
  schema: number;
  observations: number;
  memory_bytes: number | null;
  data_bytes: number;
  disk_free: number;
  worker: string;
  uptime_seconds: number;
  next_scan: number | null;
  blizzard_configured: boolean;
  sources: Feed[];
  jobs: {
    id: number;
    status: string;
    started: string;
    finished: string | null;
    message: string;
  }[];
};
type View = {
  materials: {
    item_id: number;
    name?: string;
    character: string;
    required: number;
    owned: number;
    missing: number;
    is_lumber?: boolean;
    gather?: { minutes: number | null; source: string };
  }[];
  origin: "demo" | "live";
  generated_at: string;
  characters: Character[];
  warbanks: (Capture & { account_id: string })[];
  coverage: Market[];
  trades: Trade[];
  crafting: Craft[];
  lumber: Rate[];
  tasks: Task[];
  telemetry: Point[];
  integrations: Record<string, string>;
  last_sync: string | null;
  events: { at: string; kind: string; message: string; account_id: string }[];
  service: Service;
  companion: {
    state: string;
    error: string | null;
    pending: boolean;
    last_output: string | null;
    last_sync: string | null;
    game_state: string;
    protocol: number;
  };
  catalog: { source?: string; observed_at?: string; kind?: string };
  catalog_error: string | null;
  access: {
    provider: string;
    billing_enabled: boolean;
    features: Record<string, boolean>;
  };
};
declare global {
  interface Window {
    lazyCrawler?: { chooseWowFolder: () => Promise<string | null> };
  }
}
async function api<T>(
  route: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch("/api/" + route, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    if (r.status === 401) window.dispatchEvent(new Event("unauthorized"));
    let message = await r.text();
    try {
      const d = JSON.parse(message).detail;
      message = typeof d === "string" ? d : JSON.stringify(d);
    } catch {}
    throw new Error(message || "Request failed");
  }
  return r.json();
}
const gold = (n: number | null | undefined) =>
  n === null || n === undefined
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(n) +
      " g";
const coin = (n: number | null | undefined) => gold(n == null ? n : n / 10000);
const fmt = (n: number) =>
  new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
const date = (s: string | number | null | undefined) =>
  s
    ? new Date(typeof s === "number" ? s * 1000 : s).toLocaleString()
    : "Not observed";
const age = (s: number | undefined) =>
  !s
    ? "Not observed"
    : Date.now() / 1000 - s < 3600
      ? Math.max(0, Math.floor((Date.now() / 1000 - s) / 60)) + "m ago"
      : Math.floor((Date.now() / 1000 - s) / 3600) + "h ago";
const realm = (s: string) =>
  s
    .split("-")
    .map((w) => w[0]?.toUpperCase() + w.slice(1))
    .join(" ");
const bytes = (n: number) =>
  n > 1e9 ? (n / 1e9).toFixed(1) + " GB" : (n / 1e6).toFixed(1) + " MB";
const scopes = [
  { id: "bags", name: "Bags & wallet", when: "Login and inventory changes" },
  { id: "bank", name: "Character bank", when: "When the bank is open" },
  {
    id: "reagents",
    name: "Reagent storage",
    when: "When available at the bank",
  },
  { id: "mail", name: "Mailbox", when: "When mail is opened and updated" },
  {
    id: "auctions",
    name: "Active auctions",
    when: "When owned auctions are queried",
  },
  { id: "equipped", name: "Equipped items", when: "Equipment changes" },
  {
    id: "guild_bank",
    name: "Guild bank",
    when: "Viewed tabs only; guild money is excluded from your budget",
  },
];
const navigation = [
  { id: "overview", label: "Command center", icon: LayoutDashboard },
  { id: "characters", label: "Characters & storage", icon: Users },
  { id: "markets", label: "Market coverage", icon: Globe2 },
  { id: "radar", label: "Opportunity radar", icon: Radar },
  { id: "crafting", label: "Crafting review", icon: FlaskConical },
  { id: "housing", label: "Décor & lumber", icon: House },
  { id: "companion", label: "Addon connection", icon: PlugZap },
  { id: "health", label: "Server health", icon: Activity },
  { id: "settings", label: "Configuration", icon: Settings2 },
];
function App() {
  const [auth, setAuth] = useState<boolean | null>(null),
    [token, setToken] = useState(""),
    [page, setPage] = useState("overview"),
    [config, setConfig] = useState<Config | null>(null),
    [draft, setDraft] = useState<Config | null>(null),
    [view, setView] = useState<View | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all"),
    [selected, setSelected] = useState<Trade | null>(null),
    [character, setCharacter] = useState<Character | null>(null),
    [clientId, setClientId] = useState(""),
    [clientSecret, setClientSecret] = useState(""),
    [estimate, setEstimate] = useState(120);
  async function load() {
    try {
      const [c, v] = await Promise.all([
        api<Config>("settings"),
        api<View>("admin"),
      ]);
      setConfig(c);
      setDraft((d) => d || c);
      setView(v);
      setAuth(true);
    } catch (e) {
      setError((e as Error).message);
      if (auth === null) setAuth(false);
    }
  }
  useEffect(() => {
    const fn = () => setAuth(false);
    window.addEventListener("unauthorized", fn);
    void load();
    return () => window.removeEventListener("unauthorized", fn);
  }, []);
  useEffect(() => {
    if (!auth) return;
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [auth]);
  useEffect(() => {
    const fn = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelected(null);
        setCharacter(null);
      }
    };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(t);
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
    const result = await api<Config>("settings", "PUT", c);
    setConfig(result);
    setDraft(result);
  }
  const go = (p: string) => {
    setPage(p);
    setSearch("");
    setFilter("all");
  };
  if (auth === null)
    return (
      <div className="login">
        <Radar size={40} />
        <p>Connecting to your addon’s engine…</p>
      </div>
    );
  if (!auth)
    return (
      <div className="login">
        <div className="login-card">
          <div className="brand-mark">
            <Radar />
          </div>
          <span className="eyebrow">LAZYCRAWLER ADMINISTRATION</span>
          <h1>
            Your addon.
            <br />A clearer overview.
          </h1>
          <p>
            Electron connects automatically. For remote administration, enter
            the access token from your server’s data folder.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void action(async () => {
                await api("login", "POST", { token });
                setToken("");
                await load();
              }, "Connected");
            }}
          >
            <label>
              Server access token
              <input
                type="password"
                autoComplete="current-password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </label>
            <button disabled={busy} className="primary">
              Connect to server <ArrowRight size={16} />
            </button>
          </form>
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    );
  if (!config || !draft || !view) return null;
  const demo = view.origin === "demo",
    service = view.service;
  const own = view.coverage.filter((m) => m.owned),
    ready = view.coverage.filter((m) =>
      ["ready", "unchanged"].includes(m.status),
    );
  const wallet = view.characters.reduce(
      (sum, c) => sum + (c.captures.bags?.money || 0),
      0,
    ),
    warbank = view.warbanks.reduce((sum, c) => sum + c.money, 0),
    mail = view.characters.reduce(
      (sum, c) => sum + (c.captures.mail?.money || 0),
      0,
    );
  const countCapture = (c: Capture | undefined) =>
    c ? (c.count ?? c.items.reduce((sum, i) => sum + i.count, 0)) : null;
  const title =
    navigation.find((n) => n.id === page)?.label || "Command center";
  const subtitle = (
    {
      overview:
        "A view of your addon, its data, and the work happening in game.",
      characters:
        "Automatically observed. Timestamped by source. Never guessed.",
      markets: "Every supported realm. One feed per shared auction house.",
      radar: "Review the routes that feed the in-game guided experience.",
      crafting: "The addon makes the plan. This is where you observe it.",
      housing:
        "A focused view of décor production and the time behind each material.",
      companion:
        "One connection. Automatic character discovery. Safe data exchange.",
      health: "Ingestion, storage, synchronization, and recovery in one place.",
      settings: "Configure the service that powers the in-game experience.",
    } as Record<string, string>
  )[page];
  function scan() {
    return (
      <button
        disabled={busy || service.worker === "scanning"}
        className="primary"
        onClick={() =>
          void action(() => api("scan", "POST"), "Region-wide refresh started")
        }
      >
        <RefreshCw
          size={15}
          className={service.worker === "scanning" ? "spin" : ""}
        />
        {service.worker === "scanning"
          ? "Refreshing region…"
          : "Refresh region"}
      </button>
    );
  }
  function searchBox(placeholder: string) {
    return (
      <div className="search">
        <Search size={16} />
        <input
          aria-label={placeholder}
          placeholder={placeholder}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
    );
  }
  function tradesTable(rows: Trade[]) {
    return rows.length ? (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ITEM</th>
              <th>ACQUIRE ON</th>
              <th>DESTINATION</th>
              <th>EST. NET</th>
              <th>RETURN</th>
              <th>ROUTE</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => (
              <tr key={t.item_key + t.source_realm + t.destination_realm}>
                <td>
                  <button className="item-link" onClick={() => setSelected(t)}>
                    <span className={"item-icon shade" + (i % 4)}>
                      {t.category === "Housing décor" ? (
                        <House size={17} />
                      ) : (
                        <Package size={17} />
                      )}
                    </span>
                    <span>
                      <strong>{t.name}</strong>
                      <small>
                        {t.category || "Market candidate"} · #{t.item_key}
                      </small>
                    </span>
                  </button>
                </td>
                <td>{realm(t.source_realm)}</td>
                <td>{realm(t.destination_realm)}</td>
                <td className="positive">+{coin(t.net_profit)}</td>
                <td>
                  <span className="roi">{t.roi}%</span>
                </td>
                <td>
                  <span
                    className={
                      "pill " +
                      (!t.source_covered || !t.destination_covered
                        ? "amber"
                        : "")
                    }
                  >
                    {!t.source_covered || !t.destination_covered
                      ? "Alt needed"
                      : "Character coverage"}
                  </span>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={"Inspect " + t.name}
                    onClick={() => setSelected(t)}
                  >
                    <ArrowUpRight size={16} />
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
        title="Waiting for actionable context"
        text="The server compares all auction clusters against your synced characters. Connect the addon and allow a region refresh; fresh prices and your limits determine which candidates appear."
      />
    );
  }
  function craftingTable(rows: Craft[]) {
    return rows.length ? (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>RECIPE</th>
              <th>CHARACTER / PROFESSION</th>
              <th>QUEUED</th>
              <th>MATERIAL COST</th>
              <th>EST. PROFIT</th>
              <th>OBSERVATION</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id + r.character}>
                <td>
                  <strong>{r.name}</strong>
                  <small>{r.category}</small>
                </td>
                <td>
                  {r.character}
                  <small>{r.profession}</small>
                </td>
                <td>{r.crafts || "Not queued"}</td>
                <td>{gold(r.economic_cost)}</td>
                <td
                  className={
                    r.net_profit != null && r.net_profit > 0 ? "positive" : ""
                  }
                >
                  {gold(r.net_profit)}
                </td>
                <td>
                  <span className="pill">{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty
        icon={<FlaskConical />}
        title="Recipes come from your characters"
        text="Open a profession in game to capture known recipes. Open a recipe in CraftSim for character-specific simulation evidence. No manual recipe JSON is needed."
      />
    );
  }
  function numberField(
    key: keyof Config,
    label: string,
    unit: string,
    step = "1",
  ) {
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
  return (
    <div className="shell" data-theme={config.theme}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Radar size={25} />
          </div>
          <div>
            LAZYCRAWLER<small>ADDON CONTROL PLANE</small>
          </div>
        </div>
        <div className="workspace">
          <span className="dot" />
          <div>
            Personal server
            <small>
              {config.region.toUpperCase()} · Retail · Administration
            </small>
          </div>
          <ChevronRight size={14} />
        </div>
        <span className="nav-label">OBSERVE & CONFIGURE</span>
        <nav>
          {navigation.map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "active" : ""}
              onClick={() => go(n.id)}
              title={n.label}
            >
              <n.icon size={17} />
              {n.label}
              {n.id === "characters" && (
                <span className="nav-count">{view.characters.length}</span>
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
                {service.worker === "scanning"
                  ? "Refreshing all markets"
                  : "Running · " + view.companion.state}
              </small>
            </span>
            <Activity size={15} />
          </div>
          <span className="version">
            v{service.version}
            <span>SELF-HOSTED</span>
          </span>
        </div>
      </aside>
      <div className="main">
        <header>
          <div className="breadcrumb">
            Administration <ChevronRight size={13} />
            <strong>{title}</strong>
          </div>
          <div className="header-right">
            <span className="mode-button"><span className="dot" />Live observations</span>
            <span className="local-tag">
              <ShieldCheck size={13} />
              Local & private
            </span>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={() =>
                void action(async () => {
                  await api("logout", "POST");
                  setAuth(false);
                }, "Signed out")
              }
            >
              <LogOut size={16} />
            </button>
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
          {demo && (
            <div className="demo-banner">
              <Sparkles size={16} />
              <div>
                <strong>Demonstration workspace</strong>
                <span>
                  Characters, market values, queues, and graphs below are
                  simulated. Service health is live. Demo data is never sent to
                  WoW.
                </span>
              </div>
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  void action(
                    () => save({ ...config, demo_mode: false }),
                    "Showing live observations",
                  )
                }
              >
                View live data <ArrowRight size={14} />
              </button>
            </div>
          )}
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                {page === "overview"
                  ? "THE ENGINE BEHIND YOUR ADDON"
                  : "LAZYCRAWLER / " + config.region.toUpperCase() + " REGION"}
              </span>
              <h1>
                {page === "overview"
                  ? "Your addon. A little more in focus."
                  : title}
              </h1>
              <p>{subtitle}</p>
            </div>
            {["overview", "markets", "radar"].includes(page) ? (
              scan()
            ) : (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => void action(load, "Administration refreshed")}
              >
                <RefreshCw size={14} />
                Refresh view
              </button>
            )}
          </div>
          <section className="data-health" aria-label="Data availability">
            <strong>Data availability · observed sources only</strong>
            {!view.last_sync && <p>No addon export received. Open LazyCrawler in WoW, then /reload. The companion imports the saved capture within about 20 seconds.</p>}
            {view.characters.length > 0 && <p>{view.characters.filter(c => !c.captures.bank).length} characters without bank captures · {view.characters.filter(c => !c.captures.mail).length} without mailbox captures · {view.characters.filter(c => !c.captures.auctions).length} without auction captures. Open each interface on the relevant character, then /reload.</p>}
            {view.warbanks.length === 0 && <p>Warbank balance unknown. Open a purchased warbank tab and wait for its contents to load.</p>}
            {ready.length === 0 && <p>No fresh market feeds loaded. Run a region refresh and review ingestion errors in Service health. Opportunity and crafting estimates remain unavailable until their source data exists.</p>}
            {view.companion.error && <p role="alert">Companion error: {view.companion.error}</p>}
            <p>Last capture import: {view.last_sync ? date(view.last_sync) : "Not received"} · Data file: {view.companion.last_output ? date(view.companion.last_output) + " — /reload to load it" : "Not published"}</p>
          </section>
          {page === "overview" && (
            <>
              <div className="intro-card admin-intro">
                <div>
                  <span className="eyebrow">PLAY IN WOW. REVIEW IT HERE.</span>
                  <h2>
                    One connected view.
                    <br />
                    Every character. Every market.
                  </h2>
                  <p>
                    The addon captures your characters and guides the work.
                    <br />
                    LazyCrawler keeps the data fresh and the bigger picture
                    clear.
                  </p>
                  <button
                    className="light-button"
                    onClick={() => go("companion")}
                  >
                    Review addon connection <ArrowRight size={15} />
                  </button>
                </div>
                <div className="connection-orbit">
                  <div>
                    <Radar size={44} />
                    <small>LAZYCRAWLER</small>
                  </div>
                  <span className="orbit-node node-1">
                    <Users size={19} />
                  </span>
                  <span className="orbit-node node-2">
                    <Inbox size={19} />
                  </span>
                  <span className="orbit-node node-3">
                    <House size={19} />
                  </span>
                  <span className="orbit-node node-4">
                    <Globe2 size={19} />
                  </span>
                </div>
              </div>
              <div className="stats">
                <Stat
                  label="Observed personal gold"
                  value={view.characters.some(c => c.captures.bags) || view.warbanks.length ? coin(wallet + warbank) : "Unknown"}
                  sub={view.characters.some(c => c.captures.mail) ? `${coin(mail)} observed pending mail · excluded` : "Mailbox balances unknown"}
                  icon={<Wallet />}
                />
                <Stat
                  label="Auction markets covered"
                  value={`${ready.length} / ${view.coverage.length}`}
                  sub={`${view.coverage.reduce((s, m) => s + m.realms.length, 0)} realms · ${own.length} with characters`}
                  icon={<Globe2 />}
                />
                <Stat
                  label="Synced characters"
                  value={String(view.characters.length)}
                  sub={
                    demo
                      ? "Simulated addon observations"
                      : view.last_sync
                        ? "Last export " + date(view.last_sync)
                        : "Waiting for first addon snapshot"
                  }
                  icon={<Users />}
                />
                <Stat
                  label="Guided tasks"
                  value={String(view.tasks.length)}
                  sub={`${view.crafting.length} crafting plans observed`}
                  icon={<Link2 />}
                />
              </div>
              <div className="two-col">
                <section className="panel padded">
                  <div className="section-title">
                    <div>
                      <h2>Region ingestion</h2>
                      <p>
                        {demo
                          ? "Simulated loaded observations"
                          : "Stored market observations over time"}
                      </p>
                    </div>
                    <span className="pill">
                      {config.region.toUpperCase()} · all clusters
                    </span>
                  </div>
                  <Chart
                    points={view.telemetry}
                    field="observations"
                    label="Loaded observations"
                  />
                </section>
                <section className="panel padded">
                  <div className="section-title">
                    <div>
                      <h2>Character coverage</h2>
                      <p>Capture freshness, without visiting every alt here.</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => go("characters")}
                    >
                      Inspect <ArrowRight size={14} />
                    </button>
                  </div>
                  {view.characters.slice(0, 4).map((c) => (
                    <button
                      className="character-line"
                      key={c.id}
                      onClick={() => setCharacter(c)}
                    >
                      <span
                        className={"class-dot " + c.class_name.toLowerCase()}
                      />
                      <span>
                        <strong>{c.name}</strong>
                        <small>
                          {realm(c.realm)} ·{" "}
                          {c.professions.join(" / ") || "No profession capture"}
                        </small>
                      </span>
                      <div className="mini-captures">
                        {["bags", "bank", "mail", "auctions"].map((s) => (
                          <span
                            className={c.captures[s] ? "captured" : "unknown"}
                            key={s}
                            title={s + ": " + age(c.captures[s]?.observed_at)}
                          >
                            {s === "mail" ? (
                              <Inbox size={13} />
                            ) : s === "bags" ? (
                              <Package size={13} />
                            ) : s === "bank" ? (
                              <Database size={13} />
                            ) : (
                              <Radar size={13} />
                            )}
                          </span>
                        ))}
                      </div>
                      <ChevronRight size={15} />
                    </button>
                  ))}
                  {!view.characters.length && (
                    <Empty
                      icon={<Users />}
                      title="The addon will introduce your characters"
                      text="Log in once on each character. Bags, banks, mail, and auction captures then arrive through the companion."
                      action={
                        <button
                          className="secondary"
                          onClick={() => go("companion")}
                        >
                          Connect addon
                        </button>
                      }
                    />
                  )}
                </section>
              </div>
              <div className="section-title">
                <div>
                  <h2>
                    Opportunity radar{" "}
                    <span className="pill">
                      {view.trades.length} candidates
                    </span>
                  </h2>
                  <p>Read-only review of the routes surfaced to your addon.</p>
                </div>
                <button className="text-button" onClick={() => go("radar")}>
                  Review all <ArrowRight size={14} />
                </button>
              </div>
              <section className="panel">
                {tradesTable(view.trades.slice(0, 4))}
              </section>
              <div className="two-col bottom-cards">
                <section className="panel padded">
                  <div className="section-title">
                    <h2>
                      <Activity size={17} /> Recent addon activity
                    </h2>
                    <span className="pill">
                      {demo ? "Simulated" : "Observed"}
                    </span>
                  </div>
                  <ActivityList events={view.events.slice(0, 4)} />
                </section>
                <section className="panel padded craft-promo">
                  <TreePine className="promo-icon" size={34} />
                  <span className="eyebrow">THE HOUSING WORKSHOP</span>
                  <h2>See the time behind the craft.</h2>
                  <p>
                    Décor queues, missing lumber, and gathering estimates from
                    measured sessions. The production workflow stays in game.
                  </p>
                  <button className="secondary" onClick={() => go("housing")}>
                    Review décor & lumber <ArrowRight size={15} />
                  </button>
                </section>
              </div>
            </>
          )}
          {page === "characters" && (
            <>
              <div className="stats">
                <Stat
                  label="Character wallets"
                  value={view.characters.some(c => c.captures.bags) ? coin(wallet) : "Unknown"}
                  sub="Observed wallet balances"
                  icon={<Wallet />}
                />
                <Stat
                  label="Shared warbank gold"
                  value={view.warbanks.length ? coin(warbank) : "Unknown"}
                  sub="Counted once per account"
                  icon={<Database />}
                />
                <Stat
                  label="Mailbox receivables"
                  value={view.characters.some(c => c.captures.mail) ? coin(mail) : "Unknown"}
                  sub="Uncollected · not liquid capital"
                  icon={<Inbox />}
                />
                <Stat
                  label="Storage coverage"
                  value={`${view.characters.reduce((n, c) => n + Object.keys(c.captures).length, 0)}`}
                  sub="Timestamped character captures"
                  icon={<Package />}
                />
              </div>
              <div className="toolbar">
                {searchBox("Find a character, realm, or profession…")}
                <span className="pill">Discovered from addon</span>
              </div>
              <section className="panel padded portfolio-chart">
                <div className="section-title">
                  <div>
                    <h2>Observed portfolio gold</h2>
                    <p>
                      Character wallets plus shared warbank. Uncollected mail
                      stays separate.
                    </p>
                  </div>
                  <span className="pill">
                    {demo ? "Simulated history" : "Addon observations"}
                  </span>
                </div>
                <Chart
                  points={view.telemetry}
                  field="inventory_gold"
                  label="Observed personal gold"
                />
              </section>
              <div className="character-grid">
                {view.characters
                  .filter((c) =>
                    (c.name + c.realm + c.professions.join(" "))
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  )
                  .map((c) => (
                    <section className="panel padded character-card" key={c.id}>
                      <div className="section-title">
                        <div className="character-name">
                          <span
                            className={
                              "class-emblem " + c.class_name.toLowerCase()
                            }
                          >
                            {c.name[0]}
                          </span>
                          <div>
                            <h2>{c.name}</h2>
                            <small>
                              {realm(c.realm)} · {c.level} {c.class_name}
                            </small>
                          </div>
                        </div>
                        <button
                          className="icon-button"
                          aria-label={"Inspect " + c.name}
                          onClick={() => setCharacter(c)}
                        >
                          <ArrowUpRight size={18} />
                        </button>
                      </div>
                      <p className="profession-label">
                        {c.professions.join(" · ") || "Profession not observed"}
                      </p>
                      {["bags", "bank", "mail", "auctions"].map((scope) => (
                        <div className="capture-row" key={scope}>
                          <span>
                            {scopes.find((s) => s.id === scope)?.name}
                          </span>
                          <strong>
                            {countCapture(c.captures[scope]) ?? "Unknown"}
                            {c.captures[scope] ? " items" : ""}
                          </strong>
                          <span
                            className={
                              "pill " +
                              (!c.captures[scope]
                                ? "neutral"
                                : Date.now() / 1000 -
                                      c.captures[scope].observed_at >
                                    86400
                                  ? "amber"
                                  : "")
                            }
                          >
                            {age(c.captures[scope]?.observed_at)}
                          </span>
                        </div>
                      ))}
                      <div className="character-gold">
                        <Wallet size={15} />
                        {coin(c.captures.bags?.money)}
                        <small>Observed wallet</small>
                      </div>
                    </section>
                  ))}
              </div>
              <div className="section-title">
                <h2>Shared account storage</h2>
                <span className="pill">Deduplicated by account</span>
              </div>
              <section className="panel padded">
                {view.warbanks.length ? (
                  view.warbanks.map((w) => (
                    <div className="pulse-row" key={w.account_id}>
                      <span>
                        Warband bank
                        <small>
                          {w.account_id === "demo"
                            ? "Demonstration account"
                            : w.account_id}{" "}
                          · {date(w.observed_at)}
                        </small>
                      </span>
                      <strong>
                        {countCapture(w)} items · {coin(w.money)}
                      </strong>
                    </div>
                  ))
                ) : (
                  <Empty
                    icon={<Database />}
                    title="Warbank not observed yet"
                    text="Open the warband bank in game. The addon records accessible tabs and updates this shared snapshot without counting it once per character."
                  />
                )}
              </section>
              <Info title="A missing observation is not an empty container">
                Mail is observed when the mailbox is open; auctions when owned
                auctions are available; bank storage when accessible.
                Attachments with COD are not treated as usable stock. Guild bank
                money is displayed in capture details and excluded from personal
                capital.
              </Info>
            </>
          )}
          {page === "markets" && (
            <>
              <div className="stats">
                <Stat
                  label="Supported realms"
                  value={String(
                    view.coverage.reduce((n, m) => n + m.realms.length, 0),
                  )}
                  sub="Discovered for the entire region"
                  icon={<Globe2 />}
                />
                <Stat
                  label="Unique auction houses"
                  value={String(view.coverage.length)}
                  sub="Connected realms share one feed"
                  icon={<Database />}
                />
                <Stat
                  label="Character markets"
                  value={String(own.length)}
                  sub="Derived from synced characters"
                  icon={<Users />}
                />
                <Stat
                  label="Loaded markets"
                  value={String(ready.length)}
                  sub="Ready or unchanged snapshots"
                  icon={<Check />}
                />
              </div>
              <Info title="Gurubashi is one shared market, not six opportunities">
                Connected realms are grouped before scanning and comparison. A
                character on Gurubashi covers its whole auction cluster.
                Comparisons exclude every other realm in that same cluster;
                additional character markets are discovered automatically.
              </Info>
              <div className="toolbar">
                {searchBox("Search any realm in a connected cluster…")}
                <div className="segmented">
                  {[
                    ["all", "All markets"],
                    ["owned", "With characters"],
                    ["pending", "Needs data"],
                  ].map(([id, label]) => (
                    <button
                      className={filter === id ? "selected" : ""}
                      key={id}
                      onClick={() => setFilter(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <section className="panel">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>AUCTION CLUSTER / REALMS</th>
                        <th>CHARACTER COVERAGE</th>
                        <th>DATA STATE</th>
                        <th>LOADED ROWS</th>
                        <th>UPSTREAM SCAN</th>
                      </tr>
                    </thead>
                    <tbody>
                      {view.coverage
                        .filter(
                          (m) =>
                            (filter === "all" ||
                              (filter === "owned" && m.owned) ||
                              (filter === "pending" &&
                                !["ready", "unchanged"].includes(m.status))) &&
                            m.name.toLowerCase().includes(search.toLowerCase()),
                        )
                        .map((m) => (
                          <tr key={m.connected_id}>
                            <td className="cluster-cell">
                              <details>
                                <summary>
                                  <strong>{m.realms[0]?.name || m.name}</strong>
                                  <span className="cluster-count">
                                    {m.realms.length} realm
                                    {m.realms.length === 1 ? "" : "s"}
                                  </span>
                                </summary>
                                <p>{m.realms.map((r) => r.name).join(" · ")}</p>
                              </details>
                            </td>
                            <td>
                              {m.characters.length ? (
                                <>
                                  <span className="pill">Your market</span>
                                  <small>{m.characters.join(", ")}</small>
                                </>
                              ) : (
                                <small>No character observed</small>
                              )}
                            </td>
                            <td>
                              <span
                                className={
                                  "pill " +
                                  (!["ready", "unchanged"].includes(m.status)
                                    ? "amber"
                                    : "")
                                }
                              >
                                {m.status}
                              </span>
                            </td>
                            <td>{m.observations.toLocaleString()}</td>
                            <td>{date(m.updated_at)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <p className="muted catalog-note">
                Catalog: {view.catalog.source || "Not discovered"} ·{" "}
                {date(view.catalog.observed_at)}.{" "}
                {view.catalog_error ||
                  "Catalog refresh is automatic; no realm selection is required."}
              </p>
            </>
          )}
          {page === "radar" && (
            <>
              <Info title="Review here. Act through the addon">
                Routes require at least one market covered by your characters.
                Expanding to an uncovered market is marked “Alt needed.” In-game
                checks verify exact variants, transfer eligibility, live price,
                and existing stock before the guided queue proceeds.
              </Info>
              <div className="toolbar">
                {searchBox("Search an item, route, or realm…")}
                <span className="pill">
                  {demo ? "Simulated values" : "Estimates · verify in game"}
                </span>
              </div>
              <section className="panel">
                {tradesTable(
                  view.trades.filter((t) =>
                    (t.name + t.source_realm + t.destination_realm)
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  ),
                )}
              </section>
              <div className="section-title">
                <h2>Observed in-game workflow</h2>
                <span className="pill">Addon owns task state</span>
              </div>
              <section className="panel padded">
                {view.tasks.length ? (
                  view.tasks.map((t) => (
                    <div className="task-row" key={t.id}>
                      <span className="task-stage">{t.state}</span>
                      <span>
                        <strong>{t.name || t.id}</strong>
                        <small>
                          {t.character || "Character not assigned"}
                          {t.from_realm
                            ? " · " +
                              realm(t.from_realm) +
                              " → " +
                              realm(t.to_realm || "")
                            : ""}
                        </small>
                      </span>
                      {t.net_profit != null && (
                        <strong className="positive">
                          {coin(t.net_profit)}
                        </strong>
                      )}
                    </div>
                  ))
                ) : (
                  <Empty
                    icon={<Link2 />}
                    title="No tasks observed"
                    text="Add a candidate to the guided queue inside the addon. Its capture, acquisition, transfer, posting, and collection state will appear here after synchronization."
                  />
                )}
              </section>
            </>
          )}
          {page === "crafting" && (
            <>
              <Info title="No manual recipe entry">
                The addon captures known recipes when professions are opened,
                and imports available CraftSim simulations through its supported
                API. Missing character-specific data remains unavailable. Queue
                quantities and progress are controlled in game.
              </Info>
              <div className="toolbar">
                {searchBox("Search recipes, professions, or characters…")}
                <span className="pill">
                  {view.crafting.length} observed plans
                </span>
              </div>
              <section className="panel">
                {craftingTable(
                  view.crafting.filter((r) =>
                    (r.name + r.character + r.profession)
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  ),
                )}
              </section>
              <div className="two-col bottom-cards">
                <section className="panel padded">
                  <h2>
                    <FlaskConical size={18} /> CraftSim observations
                  </h2>
                  <p>
                    Quality, yield, skill, and concentration come from the
                    character’s simulation. This server does not invent
                    specialization bonuses or assume that inventory materials
                    are free.
                  </p>
                  <div className="pulse-row">
                    <span>CraftSim</span>
                    <span className="pill">
                      {view.integrations.CraftSim || "Not yet observed"}
                    </span>
                  </div>
                  <div className="pulse-row">
                    <span>Auctionator</span>
                    <span className="pill">
                      {view.integrations.Auctionator || "Not yet observed"}
                    </span>
                  </div>
                </section>
                <section className="panel padded craft-promo">
                  <House className="promo-icon" size={32} />
                  <span className="eyebrow">FOCUSED PRODUCTION</span>
                  <h2>A workshop for your next home.</h2>
                  <p>
                    Review housing recipes alongside lumber requirements,
                    measured gathering rates, and missing stock.
                  </p>
                  <button className="secondary" onClick={() => go("housing")}>
                    Open housing workshop <ArrowRight size={15} />
                  </button>
                </section>
              </div>
            </>
          )}
          {page === "housing" && (
            <>
              <div className="stats">
                <Stat
                  label="Décor plans"
                  value={String(
                    view.crafting.filter((c) => c.category === "Housing décor")
                      .length,
                  )}
                  sub="Observed housing recipe queues"
                  icon={<House />}
                />
                <Stat
                  label="Gathering observations"
                  value={String(view.lumber.reduce((n, l) => n + l.samples, 0))}
                  sub={
                    demo
                      ? "Simulated session samples"
                      : "Completed measured sessions"
                  }
                  icon={<TreePine />}
                />
                <Stat
                  label="Tracked lumber types"
                  value={String(view.lumber.length)}
                  sub="Rates remain source and zone specific"
                  icon={<Package />}
                />
                <Stat
                  label="Estimated session time"
                  value={
                    view.materials.some((m) => m.is_lumber) &&
                    view.materials
                      .filter((m) => m.is_lumber && m.missing > 0)
                      .every((m) => m.gather?.minutes != null)
                      ? Math.round(
                          view.materials
                            .filter((m) => m.is_lumber)
                            .reduce((n, m) => n + (m.gather?.minutes || 0), 0),
                        ) + " min"
                      : "Awaiting matched data"
                  }
                  sub="Queue estimate · not a guarantee"
                  icon={<Clock3 />}
                />
              </div>
              <div className="section-title">
                <div>
                  <h2>Housing production review</h2>
                  <p>The character chooses and crafts recipes in the addon.</p>
                </div>
              </div>
              <section className="panel">
                {craftingTable(
                  view.crafting.filter((r) => r.category === "Housing décor"),
                )}
              </section>
              <div className="section-title">
                <h2>Consolidated material review</h2>
                <span className="pill">Addon inventory deduction</span>
              </div>
              <section className="panel padded">
                {view.materials.length ? (
                  view.materials.map((m, i) => (
                    <div
                      className="pulse-row"
                      key={m.item_id + ":" + m.character + ":" + i}
                    >
                      <span>
                        {m.name || "Item #" + m.item_id}
                        <small>
                          {m.character} · {m.owned} observed / {m.required}{" "}
                          required
                        </small>
                      </span>
                      <strong>
                        {m.missing} missing
                        {m.is_lumber && (
                          <small>
                            {m.gather?.minutes != null
                              ? m.gather.minutes + " min observed gathering"
                              : "No matched gathering rate"}
                          </small>
                        )}
                      </strong>
                    </div>
                  ))
                ) : (
                  <p className="muted">
                    Queue resolved recipes in game. Consolidated material
                    requirements arrive automatically with the next export.
                  </p>
                )}
              </section>
              <div className="two-col bottom-cards">
                <section className="panel padded">
                  <div className="section-title">
                    <h2>
                      <TreePine size={18} /> Observed lumber rates
                    </h2>
                    <span className="pill">Time weighted</span>
                  </div>
                  {view.lumber.length ? (
                    view.lumber.map((r, i) => (
                      <div
                        className="lumber-row"
                        key={r.item_id + r.zone + r.source}
                      >
                        <div>
                          <strong>{r.name || "Item #" + r.item_id}</strong>
                          <small>
                            {r.zone || "Zone unknown"} · {r.samples} sessions
                          </small>
                        </div>
                        <div className="rate-bar">
                          <span
                            style={{
                              width:
                                Math.max(
                                  5,
                                  (r.per_hour /
                                    Math.max(
                                      ...view.lumber.map((r) => r.per_hour),
                                    )) *
                                    100,
                                ) + "%",
                            }}
                          />
                        </div>
                        <strong>
                          {Math.round(r.per_hour)}
                          <small>per hour</small>
                        </strong>
                      </div>
                    ))
                  ) : (
                    <Empty
                      icon={<TreePine />}
                      title="Measure a route in game"
                      text="Track a gathering session in the addon. External providers can supply validated samples; unsupported addons are identified without inventing their API or statistics."
                    />
                  )}
                </section>
                <section className="panel padded">
                  <h2>
                    <Clock3 size={18} /> Gathering time estimate
                  </h2>
                  <p>
                    Estimate the observed time required for a missing quantity.
                    Existing stock is deducted in the addon’s material plan.
                  </p>
                  <label>
                    Missing lumber quantity
                    <input
                      type="number"
                      min="0"
                      max="1000000"
                      value={estimate}
                      onChange={(e) =>
                        setEstimate(Math.max(0, Number(e.target.value)))
                      }
                    />
                  </label>
                  {view.lumber.map((r) => (
                    <div
                      className="pulse-row"
                      key={r.item_id + r.zone + r.source}
                    >
                      <span>
                        {r.name || "Item #" + r.item_id}
                        <small>
                          {r.zone} · {r.source}
                        </small>
                      </span>
                      <strong>
                        {Math.round((estimate / r.per_hour) * 60)} min
                        <small>At {Math.round(r.per_hour)} / hour</small>
                      </strong>
                    </div>
                  ))}
                  <small className="estimate-note">
                    Time = missing quantity ÷ observed rate. Travel,
                    competition, buffs, and sample size can change the result.
                    This calculator does not alter the in-game queue.
                  </small>
                </section>
              </div>
            </>
          )}
          {page === "companion" && (
            <>
              <div className="two-col">
                <section className="panel padded">
                  <div className="section-title">
                    <h2>
                      <PlugZap size={18} /> Desktop ↔ addon
                    </h2>
                    <span className="pill">
                      Protocol {view.companion.protocol}
                    </span>
                  </div>
                  <div className="pulse-row">
                    <span>Actual companion state</span>
                    <strong>{view.companion.state}</strong>
                  </div>
                  <div className="pulse-row">
                    <span>Actual game process</span>
                    <strong>{view.companion.game_state}</strong>
                  </div>
                  <div className="pulse-row">
                    <span>Last actual addon import</span>
                    <strong>{date(view.companion.last_sync)}</strong>
                  </div>
                  <div className="pulse-row">
                    <span>Last data-addon update</span>
                    <strong>{date(view.companion.last_output)}</strong>
                  </div>
                  <div className="pulse-row">
                    <span>Pending outgoing data</span>
                    <span
                      className={
                        "pill " + (view.companion.pending ? "amber" : "")
                      }
                    >
                      {view.companion.pending
                        ? "Preparing data file"
                        : "No pending write"}
                    </span>
                  </div>
                  {view.companion.error && (
                    <p className="error-text">{view.companion.error}</p>
                  )}
                  <small className="estimate-note">
                    Published data loads on the next /reload. Installing addon code still requires WoW to be closed.
                  </small>
                </section>
                <section className="panel padded">
                  <h2>
                    <FolderOpen size={18} /> WoW installation
                  </h2>
                  <label>
                    Retail installation folder
                    <input
                      placeholder="/path/to/World of Warcraft/_retail_"
                      value={draft.wow_path}
                      onChange={(e) =>
                        setDraft({ ...draft, wow_path: e.target.value })
                      }
                    />
                  </label>
                  <div className="toolbar">
                    {window.lazyCrawler && (
                      <button
                        className="secondary"
                        onClick={() =>
                          void action(async () => {
                            const path =
                              await window.lazyCrawler!.chooseWowFolder();
                            if (path) setDraft({ ...draft, wow_path: path });
                          }, "Folder selection updated")
                        }
                      >
                        <FolderOpen size={15} />
                        Choose folder
                      </button>
                    )}
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() =>
                        void action(
                          () => save(draft),
                          "Connection settings saved",
                        )
                      }
                    >
                      Save connection
                    </button>
                  </div>
                  <Toggle
                    label="Automatic companion"
                    detail="Read stable addon exports and prepare safe outgoing updates."
                    checked={draft.companion_enabled}
                    change={(v) => setDraft({ ...draft, companion_enabled: v })}
                  />
                  <button
                    className="secondary"
                    disabled={
                      busy ||
                      !config.wow_path ||
                      view.companion.game_state !== "closed"
                    }
                    onClick={() =>
                      void action(
                        () => api("companion/install", "POST"),
                        "Addon installed. Enable LazyCrawler and LazyCrawler Data in WoW.",
                      )
                    }
                  >
                    <ArrowDownToLine size={15} />
                    Install / update addon files
                  </button>
                  <small className="estimate-note">
                    Close WoW to install or replace the data addon. No
                    SavedVariables are overwritten.
                  </small>
                </section>
              </div>
              <div className="section-title">
                <h2>Automatic capture lifecycle</h2>
                <span className="pill">No character forms</span>
              </div>
              <div className="capture-guide">
                {[
                  {
                    n: "01",
                    title: "Play normally",
                    text: "Log in to an alt. Open bags, banks, mailbox, auctions, or professions as needed.",
                  },
                  {
                    n: "02",
                    title: "The addon observes",
                    text: "Only accessible data is captured, with separate timestamps and completeness markers.",
                  },
                  {
                    n: "03",
                    title: "The client saves",
                    text: "A reload or logout flushes SavedVariables. The companion reads the stable export automatically.",
                  },
                  {
                    n: "04",
                    title: "Plans return safely",
                    text: "Server results enter the separate data addon atomically. Use /reload to load a published bundle.",
                  },
                ].map((s) => (
                  <section className="panel padded" key={s.n}>
                    <span className="eyebrow">{s.n}</span>
                    <h3>{s.title}</h3>
                    <p>{s.text}</p>
                  </section>
                ))}
              </div>
              <div className="section-title">
                <h2>Observed integrations</h2>
              </div>
              <section className="panel padded">
                {Object.entries(view.integrations).length ? (
                  Object.entries(view.integrations).map(([name, state]) => (
                    <div className="pulse-row" key={name}>
                      <span>{name}</span>
                      <strong>{state}</strong>
                    </div>
                  ))
                ) : (
                  <p>No addon integration report received yet.</p>
                )}
              </section>
              <Info title="WoW’s file boundary is visible, not hidden">
                The addon cannot send arbitrary HTTP requests. Inbound character
                captures arrive after the game saves them; outgoing data files
                load on your next /reload. In-game inventory capture and
                workflow updates happen immediately within the addon.
              </Info>
            </>
          )}
          {page === "health" && (
            <>
              <div className="stats">
                <Stat
                  label="Worker"
                  value={service.worker}
                  sub="Bounded, non-overlapping ingestion"
                  icon={<Activity />}
                />
                <Stat
                  label="Database"
                  value={bytes(service.data_bytes)}
                  sub={"Schema " + service.schema + " · " + service.database}
                  icon={<Database />}
                />
                <Stat
                  label="Backend memory"
                  value={
                    service.memory_bytes
                      ? bytes(service.memory_bytes)
                      : "Unavailable"
                  }
                  sub={
                    "Uptime " +
                    Math.floor(service.uptime_seconds / 60) +
                    " minutes"
                  }
                  icon={<Activity />}
                />
                <Stat
                  label="Free data volume"
                  value={bytes(service.disk_free)}
                  sub="Live filesystem measurement"
                  icon={<ShieldCheck />}
                />
              </div>
              <div className="two-col">
                <section className="panel padded">
                  <h2>Market observations over time</h2>
                  <Chart
                    points={view.telemetry}
                    field="observations"
                    label="Loaded observations"
                  />
                </section>
                <section className="panel padded">
                  <h2>Healthy source feeds</h2>
                  <Chart
                    points={view.telemetry}
                    field="healthy"
                    label="Healthy feeds"
                  />
                </section>
              </div>
              <div className="section-title">
                <h2>Actual refresh jobs</h2>
                {scan()}
              </div>
              <section className="panel">
                {service.jobs.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>JOB</th>
                          <th>STARTED</th>
                          <th>STATE</th>
                          <th>PROGRESS / RESULT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {service.jobs.map((j) => (
                          <tr key={j.id}>
                            <td>#{j.id}</td>
                            <td>{date(j.started)}</td>
                            <td>
                              <span
                                className={
                                  "pill " +
                                  (j.status === "error" ||
                                  j.status === "interrupted"
                                    ? "amber"
                                    : "")
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
                    title="No refresh jobs yet"
                    text="Start a region refresh or enable scheduling. Live job progress appears here; demo data does not create fake jobs."
                  />
                )}
              </section>
              <div className="section-title">
                <h2>Actual source diagnostics</h2>
                <span className="pill">Always live</span>
              </div>
              <section className="panel">
                {service.sources.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>FEED</th>
                          <th>STATE</th>
                          <th>ROWS</th>
                          <th>UPSTREAM / FETCHED</th>
                        </tr>
                      </thead>
                      <tbody>
                        {service.sources.map((s) => (
                          <tr key={s.id}>
                            <td>
                              {s.id}
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
                            <td>{fmt(s.rows)}</td>
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
                    title="Feeds populate automatically"
                    text="The region catalog is loaded; the first region refresh creates price snapshots for every distinct auction house."
                  />
                )}
              </section>
            </>
          )}
          {page === "settings" && (
            <>
              <div className="two-col">
                <section className="panel padded">
                  <h2>
                    <RefreshCw size={18} /> Region service
                  </h2>
                  <label>
                    Region
                    <select
                      value={draft.region}
                      onChange={(e) =>
                        setDraft({ ...draft, region: e.target.value })
                      }
                    >
                      {["us", "eu", "kr", "tw"].map((r) => (
                        <option value={r} key={r}>
                          {r.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="coverage-lock">
                    <Globe2 size={18} />
                    <span>
                      <strong>All unique auction houses</strong>
                      <small>
                        Realm selection is automatic. Characters determine
                        portfolio coverage.
                      </small>
                    </span>
                    <ShieldCheck size={17} />
                  </div>
                  <Toggle
                    label="Scheduled region refresh"
                    detail="The server must stay running. Unchanged feeds use HTTP validators."
                    checked={draft.scheduled}
                    change={(v) => setDraft({ ...draft, scheduled: v })}
                  />
                  <div className="form-grid">
                    {numberField("interval_minutes", "Refresh interval", "min")}
                    {numberField(
                      "scan_concurrency",
                      "Concurrent downloads",
                      "feeds",
                    )}
                    {numberField("retention_days", "History retention", "days")}
                    {numberField("max_age_hours", "Price freshness", "hours")}
                    {numberField(
                      "max_context_age_hours",
                      "Regional context freshness",
                      "hours",
                    )}
                  </div>
                </section>
                <section className="panel padded">
                  <h2>
                    <Wallet size={18} /> Addon recommendation limits
                  </h2>
                  <p className="muted">
                    Service defaults for the in-game planner. Character funds
                    and accessible inventory come from observations.
                  </p>
                  <div className="form-grid">
                    {numberField("budget_gold", "Capital ceiling", "gold")}
                    {numberField("max_item_gold", "Maximum per item", "gold")}
                    {numberField(
                      "min_profit_gold",
                      "Minimum estimated net",
                      "gold",
                    )}
                    {numberField("min_roi", "Minimum return", "%")}
                    {numberField("fee_percent", "Auction cut", "%", ".1")}
                    {numberField(
                      "deposit_gold",
                      "Relisting reserve",
                      "gold",
                      ".1",
                    )}
                    {numberField(
                      "min_sold_day",
                      "Regional demand floor",
                      "units",
                      ".001",
                    )}
                    {numberField("max_sale_days", "Inverse demand cap", "days")}
                  </div>
                </section>
                <section className="panel padded">
                  <h2>
                    <Database size={18} /> Data providers
                  </h2>
                  <Toggle
                    label="TSM public market feeds"
                    detail="All realm clusters, regional context, and regional commodities. No key required."
                    checked={draft.tsm_enabled}
                    change={(v) => setDraft({ ...draft, tsm_enabled: v })}
                  />
                  <Toggle
                    label="Blizzard auction evidence"
                    detail="Optional exact auction identities and connected-realm verification."
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
                    <button className="secondary" disabled={busy}>
                      Save credentials
                    </button>
                    <small className="estimate-note">
                      {service.blizzard_configured
                        ? "Credentials stored"
                        : "Optional provider not configured"}
                      . Secrets are never returned to this view.
                    </small>
                  </form>
                </section>
                <section className="panel padded">
                  <h2>
                    <Sparkles size={18} /> Presentation & portability
                  </h2>
                  <label>
                    Color palette
                    <select
                      value={draft.theme}
                      onChange={(e) =>
                        setDraft({ ...draft, theme: e.target.value })
                      }
                    >
                      <option value="grove">
                        Grove · original sage & lime
                      </option>
                      <option value="spectral">Spectral · cyan & lime</option>
                      <option value="ember">Ember · apricot & violet</option>
                    </select>
                  </label>
                  <p className="muted">
                    Database backups preserve settings, observations, captures,
                    and workflow history. Login sessions and provider credential
                    files are excluded.
                  </p>
                  <button
                    className="secondary"
                    onClick={() => window.location.assign("/api/backup")}
                  >
                    <ArrowDownToLine size={15} />
                    Download database backup
                  </button>
                  <div className="access-note">
                    <ShieldCheck size={17} />
                    <span>
                      Self-hosted access · all features available
                      <small>
                        Provider authorization is extensible. No billing or paid
                        addon gates are enabled.
                      </small>
                    </span>
                  </div>
                </section>
              </div>
              <div className="save-bar">
                <span>Save to apply server and addon defaults.</span>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    void action(() => save(draft), "Server configuration saved")
                  }
                >
                  Save configuration <Check size={15} />
                </button>
              </div>
            </>
          )}
          <footer>
            <span>
              <ShieldCheck size={12} />
              Administrative companion · the player experience lives in WoW.
            </span>
            <span>
              {demo ? "SIMULATED REVIEW DATA" : "OBSERVED DATA"}
              <span className="footer-dot">✦</span>
            </span>
          </footer>
        </main>
      </div>
      {selected && (
        <Modal label="Route evidence" close={() => setSelected(null)}>
          <span className="eyebrow">
            {demo ? "DEMONSTRATION ROUTE" : "ADDON ROUTE REVIEW"} · #
            {selected.item_key}
          </span>
          <h1>{selected.name}</h1>
          <p>
            {realm(selected.source_realm)} → {realm(selected.destination_realm)}
          </p>
          <div className="detail-profit positive">
            +{coin(selected.net_profit)}
          </div>
          <small>Estimated net · {selected.roi}% ROI</small>
          <div className="pulse-row">
            <span>Acquisition snapshot</span>
            <strong>{coin(selected.buyout)}</strong>
          </div>
          <div className="pulse-row">
            <span>Conservative exit estimate</span>
            <strong>{coin(selected.estimated_sale)}</strong>
          </div>
          <div className="pulse-row">
            <span>Oldest supporting observation</span>
            <strong>{date(selected.observed_at)}</strong>
          </div>
          <h3>Route coverage</h3>
          <p>
            {selected.source_covered
              ? "A source character is available."
              : "An acquisition character is needed."}{" "}
            {selected.destination_covered
              ? "A destination character is available."
              : "A destination character is needed."}
          </p>
          <h3>Evidence & checks</h3>
          <p>{selected.explanation}</p>
          <ul>
            {selected.risks.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <Info title="Controlled in game">
            Use the addon’s guided queue to verify the live item, acquire it,
            move accessible stock, post it, and collect proceeds. This dashboard
            does not execute those actions.
          </Info>
        </Modal>
      )}
      {character && (
        <Modal label="Character captures" close={() => setCharacter(null)}>
          <span className="eyebrow">
            {demo ? "SIMULATED CHARACTER" : "ADDON OBSERVATION"}
          </span>
          <h1>{character.name}</h1>
          <p>
            {realm(character.realm)} · {character.class_name} ·{" "}
            {character.professions.join(" / ")}
          </p>
          {scopes.map((s) => {
            const c = character.captures[s.id];
            return (
              <section className="capture-detail" key={s.id}>
                <div className="section-title">
                  <h3>{s.name}</h3>
                  <span
                    className={
                      "pill " + (!c ? "neutral" : !c.complete ? "amber" : "")
                    }
                  >
                    {c ? (c.complete ? "Observed" : "Partial") : "Unknown"}
                  </span>
                </div>
                <p>{s.when}</p>
                {c ? (
                  <>
                    <div className="pulse-row">
                      <span>
                        {countCapture(c)} items · {coin(c.money)}
                      </span>
                      <strong>{date(c.observed_at)}</strong>
                    </div>
                    {c.note && <small>{c.note}</small>}
                    {c.items.length > 0 && (
                      <details>
                        <summary>Captured items</summary>
                        {c.items.slice(0, 100).map((item, i) => (
                          <div className="pulse-row" key={i}>
                            <span>
                              {item.name || "Item #" + item.item_id}
                              {item.cod ? " · COD attachment" : ""}
                            </span>
                            <strong>{item.count}</strong>
                          </div>
                        ))}
                      </details>
                    )}
                  </>
                ) : (
                  <small>
                    Not captured. The addon will update this source when you
                    open it in game.
                  </small>
                )}
              </section>
            );
          })}
        </Modal>
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
      <ShieldCheck size={18} />
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
function ActivityList({ events }: { events: View["events"] }) {
  return events.length ? (
    <div className="activity-list">
      {events.map((e, i) => (
        <div key={i}>
          <span className="activity-dot" />
          <span>
            <strong>{e.message}</strong>
            <small>{date(e.at)}</small>
          </span>
        </div>
      ))}
    </div>
  ) : (
    <Empty
      icon={<Activity />}
      title="Waiting for observations"
      text="Capture and sync events appear here when the addon reports them."
    />
  );
}
function Modal({
  label,
  close,
  children,
}: {
  label: string;
  close: () => void;
  children: React.ReactNode;
}) {
  const ref = React.useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    (ref.current?.querySelector("button") as HTMLElement | null)?.focus();
    return () => previous?.focus();
  }, []);
  return (
    <div className="overlay" onClick={close}>
      <section
        tabIndex={-1}
        ref={ref}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Tab") {
            const items = ref.current?.querySelectorAll<HTMLElement>(
              'button,summary,input,select,[tabindex="0"]',
            );
            if (!items?.length) return;
            const first = items[0],
              last = items[items.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first.focus();
            }
          }
        }}
      >
        <button
          className="close icon-button"
          aria-label="Close details"
          onClick={close}
        >
          <X size={20} />
        </button>
        {children}
      </section>
    </div>
  );
}
function Chart({
  points,
  field,
  label,
}: {
  points: Point[];
  field: keyof Point;
  label: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const id = useId().replace(/:/g, "");
  const valid = points.filter((p) => typeof p[field] === "number");
  if (!valid.length)
    return (
      <Empty
        icon={<Activity />}
        title="History will grow here"
        text="The first server refresh records a point. Subsequent observations build this chart."
      />
    );
  const max = Math.max(...valid.map((p) => Number(p[field])), 1),
    min = 0;
  const x = (i: number) => 40 + (i / Math.max(valid.length - 1, 1)) * 590,
    y = (v: number) => 160 - ((v - min) / (max - min)) * 125;
  const line = valid.map((p, i) => `${x(i)},${y(Number(p[field]))}`).join(" ");
  const activeIndex = Math.min(hover ?? valid.length - 1, valid.length - 1);
  const selected = valid[activeIndex];
  return (
    <div className="chart">
      <div className="chart-value">
        <strong>{fmt(Number(selected[field]))}</strong>
        <small>{date(selected.at)}</small>
      </div>
      <svg
        viewBox="0 0 650 190"
        role="img"
        aria-label={label + " over time"}
        onPointerLeave={() => setHover(null)}
        onPointerMove={(e) => {
          const box = e.currentTarget.getBoundingClientRect();
          setHover(
            Math.max(
              0,
              Math.min(
                valid.length - 1,
                Math.round(
                  ((((e.clientX - box.left) / box.width) * 650 - 40) / 590) *
                    (valid.length - 1),
                ),
              ),
            ),
          );
        }}
      >
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--lime)" stopOpacity=".19" />
            <stop offset="100%" stopColor="var(--lime)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((r) => (
          <g key={r}>
            <line
              x1="40"
              x2="630"
              y1={y(max * r)}
              y2={y(max * r)}
              className="chart-grid"
            />
            <text x="0" y={y(max * r) + 3}>
              {fmt(max * r)}
            </text>
          </g>
        ))}
        <polygon points={`40,160 ${line} 630,160`} fill={`url(#${id})`} />
        <polyline
          points={line}
          fill="none"
          stroke="var(--lime)"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />
        {hover !== null && (
          <>
            <line
              x1={x(activeIndex)}
              x2={x(activeIndex)}
              y1="25"
              y2="165"
              className="chart-crosshair"
            />
            <circle
              cx={x(activeIndex)}
              cy={y(Number(selected[field]))}
              r="4"
              fill="var(--lime)"
            />
          </>
        )}
        <text x="40" y="185">
          {new Date(valid[0].at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </text>
        <text x="580" y="185">
          {new Date(valid[valid.length - 1].at).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </text>
      </svg>
      <details className="chart-data">
        <summary>View exact observations</summary>
        <div className="history-list">
          {valid.map((p, i) => (
            <div className="pulse-row" key={i}>
              <span>{date(p.at)}</span>
              <strong>{Number(p[field]).toLocaleString()}</strong>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
