import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Clock3,
  Database,
  Gauge,
  MapPin,
  Moon,
  Navigation,
  Radio,
  Route,
  Search,
  Sun,
  TrainFront,
} from "lucide-react";

const API_BASE = "http://192.168.0.230:8000";

function App() {
  const [mode, setMode] = useState("train");
  const [darkMode, setDarkMode] = useState(true);

  const [trainNumber, setTrainNumber] = useState("");
  const [train, setTrain] = useState(null);

  const [stationQuery, setStationQuery] = useState("");
  const [stationSuggestions, setStationSuggestions] = useState([]);
  const [station, setStation] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const searchTrain = async () => {
    if (!trainNumber.trim()) {
      setError("Enter a train number to begin.");
      return;
    }

    setLoading(true);
    setError("");
    setTrain(null);
    setStation(null);

    try {
      const response = await fetch(
        `${API_BASE}/train/${trainNumber.trim()}`
      );

      if (!response.ok) throw new Error();

      const data = await response.json();
      setTrain(data);
    } catch {
      setError("Train not found or backend is unavailable.");
    } finally {
      setLoading(false);
    }
  };

  const handleStationInput = async (value) => {
    setStationQuery(value);
    setStation(null);

    if (!value.trim()) {
      setStationSuggestions([]);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/stations/search?q=${encodeURIComponent(value)}`
      );

      if (!response.ok) throw new Error();

      const data = await response.json();
      setStationSuggestions(data);
    } catch {
      setStationSuggestions([]);
    }
  };

  const selectStation = async (stationItem) => {
    setStationQuery(`${stationItem.name} (${stationItem.code})`);
    setStationSuggestions([]);
    setLoading(true);
    setError("");
    setStation(null);
    setTrain(null);

    try {
      const response = await fetch(
        `${API_BASE}/station/${stationItem.code}`
      );

      if (!response.ok) throw new Error();

      const data = await response.json();
      setStation(data);
    } catch {
      setError("Unable to load station information.");
    } finally {
      setLoading(false);
    }
  };

  const openTrainFromStation = async (number) => {
    setMode("train");
    setTrainNumber(String(number));
    setStation(null);
    setStationSuggestions([]);
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/train/${number}`);

      if (!response.ok) throw new Error();

      const data = await response.json();
      setTrain(data);
    } catch {
      setError("Unable to open train information.");
    } finally {
      setLoading(false);
    }
  };

  const isDark = darkMode;

  const page = isDark
    ? "bg-[#071015] text-slate-100"
    : "bg-[#edf4f5] text-slate-900";

  const panel = isDark
    ? "border-white/10 bg-[#0b171d]/88"
    : "border-slate-300/80 bg-white/85";

  const panelSoft = isDark
    ? "border-white/8 bg-[#0d1b21]/72"
    : "border-slate-200 bg-slate-50/90";

  const textMuted = isDark ? "text-slate-400" : "text-slate-600";
  const textSoft = isDark ? "text-slate-500" : "text-slate-500";

  return (
    <div className={`min-h-screen transition-colors duration-500 ${page}`}>
      <TelemetryBackground darkMode={darkMode} />

      <div className="relative z-10 flex min-h-screen">
        <Sidebar
          mode={mode}
          setMode={setMode}
          darkMode={darkMode}
          panel={panel}
          textMuted={textMuted}
        />

        <main className="min-w-0 flex-1 px-3 py-3 sm:px-5 lg:px-7">
          <TopBar
            darkMode={darkMode}
            setDarkMode={setDarkMode}
            panel={panel}
            textMuted={textMuted}
          />

          <section className="mx-auto mt-4 w-full max-w-[1500px]">
            <HeroHeader textMuted={textMuted} />

            <SearchConsole
              mode={mode}
              setMode={setMode}
              trainNumber={trainNumber}
              setTrainNumber={setTrainNumber}
              searchTrain={searchTrain}
              stationQuery={stationQuery}
              handleStationInput={handleStationInput}
              stationSuggestions={stationSuggestions}
              selectStation={selectStation}
              panel={panel}
              panelSoft={panelSoft}
              darkMode={darkMode}
              textMuted={textMuted}
            />

            <AnimatePresence mode="wait">
              {loading && (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <LoadingMatrix
                    panel={panel}
                    darkMode={darkMode}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`mt-4 rounded-xl border px-4 py-3 text-sm ${
                  isDark
                    ? "border-rose-400/30 bg-rose-400/8 text-rose-300"
                    : "border-rose-300 bg-rose-50 text-rose-700"
                }`}
              >
                <span className="mr-2 font-mono text-xs">SYS_ERR //</span>
                {error}
              </motion.div>
            )}

            <AnimatePresence mode="wait">
              {!loading && train && (
                <motion.div
                  key={`train-${train.number}`}
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.35 }}
                >
                  <TrainDashboard
                    train={train}
                    darkMode={darkMode}
                    panel={panel}
                    panelSoft={panelSoft}
                    textMuted={textMuted}
                    textSoft={textSoft}
                  />
                </motion.div>
              )}

              {!loading && station && (
                <motion.div
                  key={`station-${station.station_code}`}
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.35 }}
                >
                  <StationDashboard
                    station={station}
                    darkMode={darkMode}
                    panel={panel}
                    panelSoft={panelSoft}
                    textMuted={textMuted}
                    textSoft={textSoft}
                    openTrainFromStation={openTrainFromStation}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {!loading && !train && !station && (
              <EmptyDashboard
                panel={panel}
                panelSoft={panelSoft}
                textMuted={textMuted}
                darkMode={darkMode}
              />
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

function TelemetryBackground({ darkMode }) {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden">
      <div
        className={`absolute inset-0 ${
          darkMode
            ? "bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.08),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(34,211,238,0.06),transparent_26%)]"
            : "bg-[radial-gradient(circle_at_20%_20%,rgba(16,185,129,0.08),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(14,116,144,0.06),transparent_26%)]"
        }`}
      />

      <div
        className={`absolute inset-0 opacity-[0.07] ${
          darkMode ? "telemetry-grid-dark" : "telemetry-grid-light"
        }`}
      />

      <motion.div
        className={`absolute left-0 right-0 top-0 h-px ${
          darkMode ? "bg-emerald-300/30" : "bg-emerald-500/20"
        }`}
        animate={{ y: ["0vh", "100vh"] }}
        transition={{
          duration: 7,
          repeat: Infinity,
          ease: "linear",
        }}
      />
    </div>
  );
}

function Sidebar({
  mode,
  setMode,
  darkMode,
  panel,
  textMuted,
}) {
  return (
    <aside
      className={`sticky top-0 hidden h-screen w-[92px] shrink-0 border-r xl:flex xl:flex-col xl:items-center xl:py-5 ${panel}`}
    >
      <div
        className={`flex h-12 w-12 items-center justify-center rounded-xl border ${
          darkMode
            ? "border-emerald-300/30 bg-emerald-300/5 text-emerald-300"
            : "border-emerald-600/20 bg-emerald-50 text-emerald-700"
        }`}
      >
        <TrainFront size={24} />
      </div>

      <div className="mt-7 flex flex-1 flex-col gap-3">
        <SideButton
          active={mode === "train"}
          onClick={() => setMode("train")}
          icon={<Activity size={19} />}
          label="Train"
          darkMode={darkMode}
        />

        <SideButton
          active={mode === "station"}
          onClick={() => setMode("station")}
          icon={<MapPin size={19} />}
          label="Station"
          darkMode={darkMode}
        />

        <SideButton
          active={false}
          onClick={() => {}}
          icon={<Database size={19} />}
          label="Data"
          darkMode={darkMode}
        />
      </div>

      <div className={`text-center font-mono text-[9px] uppercase tracking-[0.18em] ${textMuted}`}>
        rail
        <br />
        core
      </div>
    </aside>
  );
}

function SideButton({
  active,
  onClick,
  icon,
  label,
  darkMode,
}) {
  return (
    <motion.button
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className={`flex w-14 flex-col items-center gap-1 rounded-xl border px-2 py-3 text-[10px] uppercase tracking-wider ${
        active
          ? darkMode
            ? "border-emerald-300/35 bg-emerald-300/10 text-emerald-300"
            : "border-emerald-600/25 bg-emerald-50 text-emerald-700"
          : darkMode
          ? "border-transparent text-slate-500 hover:border-white/10 hover:bg-white/5"
          : "border-transparent text-slate-500 hover:border-slate-200 hover:bg-white"
      }`}
    >
      {icon}
      {label}
    </motion.button>
  );
}

function TopBar({
  darkMode,
  setDarkMode,
  panel,
  textMuted,
}) {
  return (
    <header
      className={`mx-auto flex w-full max-w-[1500px] items-center justify-between rounded-2xl border px-4 py-3 backdrop-blur-xl sm:px-5 ${panel}`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Radio
            size={15}
            className={darkMode ? "text-emerald-300" : "text-emerald-700"}
          />

          <p className="truncate font-mono text-xs font-semibold uppercase tracking-[0.16em] sm:text-sm">
            [RAIL_CORE] // TRAIN_INTELLIGENCE_MATRIX
          </p>
        </div>

        <p className={`mt-1 hidden font-mono text-[10px] uppercase tracking-[0.18em] sm:block ${textMuted}`}>
          NTES-derived timetable snapshot · local telemetry interface
        </p>
      </div>

      <div className="ml-3 flex shrink-0 items-center gap-2">
        <div
          className={`hidden items-center gap-2 rounded-lg border px-3 py-2 font-mono text-[10px] uppercase tracking-wider sm:flex ${
            darkMode
              ? "border-emerald-300/20 bg-emerald-300/5 text-emerald-300"
              : "border-emerald-600/20 bg-emerald-50 text-emerald-700"
          }`}
        >
          <span className="h-2 w-2 animate-pulse rounded-full bg-current" />
          system active
        </div>

        <motion.button
          whileHover={{ rotate: 8 }}
          whileTap={{ scale: 0.94 }}
          onClick={() => setDarkMode(!darkMode)}
          className={`rounded-lg border p-2.5 ${
            darkMode
              ? "border-white/10 bg-white/5 text-slate-200"
              : "border-slate-300 bg-white text-slate-700"
          }`}
        >
          {darkMode ? <Sun size={17} /> : <Moon size={17} />}
        </motion.button>
      </div>
    </header>
  );
}

function HeroHeader({ textMuted }) {
  return (
    <div className="mt-7 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-emerald-400">
          railway intelligence console
        </p>

        <h1
          className="mt-2 text-3xl font-semibold uppercase tracking-[0.035em] sm:text-4xl lg:text-5xl"
          style={{
            fontFamily:
              '"Trebuchet MS", "Arial Narrow", "Segoe UI", sans-serif',
          }}
        >
          Indian Railways Train Information
        </h1>

        <p className={`mt-2 max-w-2xl text-sm sm:text-base ${textMuted}`}>
          Search trains, inspect routes and analyse station traffic through a
          command-centre style railway dashboard.
        </p>
      </div>

      <div className={`font-mono text-[10px] uppercase tracking-[0.2em] ${textMuted}`}>
        data_core / timetable_analytics / v1.0
      </div>
    </div>
  );
}

function SearchConsole({
  mode,
  setMode,
  trainNumber,
  setTrainNumber,
  searchTrain,
  stationQuery,
  handleStationInput,
  stationSuggestions,
  selectStation,
  panel,
  panelSoft,
  darkMode,
  textMuted,
}) {
  return (
    <section className={`relative mt-6 rounded-2xl border p-3 sm:p-4 ${panel}`}>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-2">
          <ConsoleTab
            active={mode === "train"}
            onClick={() => setMode("train")}
            label="TRAIN QUERY"
            darkMode={darkMode}
          />

          <ConsoleTab
            active={mode === "station"}
            onClick={() => setMode("station")}
            label="STATION QUERY"
            darkMode={darkMode}
          />
        </div>

        <div className={`font-mono text-[10px] uppercase tracking-[0.18em] ${textMuted}`}>
          query channel: {mode.toUpperCase()}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {mode === "train" ? (
          <motion.div
            key="train-console"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            className={`flex flex-col gap-2 rounded-xl border p-2 sm:flex-row ${panelSoft}`}
          >
            <div className="flex min-w-0 flex-1 items-center gap-3 px-3">
              <TrainFront size={18} className="shrink-0 text-emerald-400" />

              <input
                value={trainNumber}
                onChange={(e) => setTrainNumber(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") searchTrain();
                }}
                placeholder="Enter train number, e.g. 12723"
                className="min-w-0 flex-1 bg-transparent py-3 font-mono text-sm outline-none placeholder:text-slate-500"
              />
            </div>

            <motion.button
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.98 }}
              onClick={searchTrain}
              className={`flex items-center justify-center gap-2 rounded-lg px-5 py-3 font-mono text-xs font-semibold uppercase tracking-[0.16em] ${
                darkMode
                  ? "bg-emerald-300 text-[#071015]"
                  : "bg-emerald-700 text-white"
              }`}
            >
              <Search size={16} />
              execute
            </motion.button>
          </motion.div>
        ) : (
          <motion.div
            key="station-console"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="relative"
          >
            <div className={`flex items-center gap-3 rounded-xl border px-4 ${panelSoft}`}>
              <MapPin size={18} className="shrink-0 text-cyan-400" />

              <input
                value={stationQuery}
                onChange={(e) => handleStationInput(e.target.value)}
                placeholder="Search station name or code..."
                className="min-w-0 flex-1 bg-transparent py-4 font-mono text-sm outline-none placeholder:text-slate-500"
              />
            </div>

            <AnimatePresence>
              {stationSuggestions.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className={`absolute left-0 right-0 top-[calc(100%+8px)] z-50 max-h-72 overflow-y-auto rounded-xl border p-2 shadow-2xl backdrop-blur-xl ${panel}`}
                >
                  {stationSuggestions.map((item) => (
                    <button
                      key={item.code}
                      onClick={() => selectStation(item)}
                      className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left transition ${
                        darkMode ? "hover:bg-white/5" : "hover:bg-slate-100"
                      }`}
                    >
                      <div>
                        <p
                          className="text-sm font-medium tracking-[0.01em]"
                          style={{
                            fontFamily:
                              '"Trebuchet MS", "Arial Narrow", "Segoe UI", sans-serif',
                          }}
                        >
                          {item.name}
                        </p>
                        <p className={`mt-1 font-mono text-[10px] uppercase tracking-wider ${textMuted}`}>
                          {item.code}
                        </p>
                      </div>

                      <ArrowRight size={15} className="text-emerald-400" />
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function ConsoleTab({
  active,
  onClick,
  label,
  darkMode,
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg border px-3 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] transition ${
        active
          ? darkMode
            ? "border-emerald-300/30 bg-emerald-300/10 text-emerald-300"
            : "border-emerald-600/25 bg-emerald-50 text-emerald-700"
          : darkMode
          ? "border-white/10 text-slate-500 hover:text-slate-300"
          : "border-slate-300 text-slate-500 hover:text-slate-800"
      }`}
    >
      {label}
    </button>
  );
}

function TrainDashboard({
  train,
  darkMode,
  panel,
  panelSoft,
  textMuted,
  textSoft,
}) {
  return (
    <section className="mt-5 grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard
          label="TRAIN"
          value={train.number}
          sub={train.name}
          icon={<TrainFront size={18} />}
          accent="emerald"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="DISTANCE"
          value={
            <AnimatedNumber
              value={train.distance_km}
              suffix=" km"
            />
          }
          sub="total corridor"
          icon={<Route size={18} />}
          accent="cyan"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="TRAVEL TIME"
          value={train.travel_time}
          sub="scheduled"
          icon={<Clock3 size={18} />}
          accent="amber"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="STOPS"
          value={<AnimatedNumber value={train.num_stops} />}
          sub="scheduled halts"
          icon={<MapPin size={18} />}
          accent="rose"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="SOURCE"
          value={train.source}
          sub={train.route?.[0]?.station_code ?? "—"}
          icon={<Navigation size={18} />}
          accent="emerald"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="DESTINATION"
          value={train.destination}
          sub={train.route?.[train.route.length - 1]?.station_code ?? "—"}
          icon={<Gauge size={18} />}
          accent="cyan"
          panel={panel}
          textMuted={textMuted}
        />
      </div>

      <JourneyTelemetry
        train={train}
        darkMode={darkMode}
        panel={panel}
        panelSoft={panelSoft}
        textMuted={textMuted}
      />

      <div className="grid gap-5 xl:grid-cols-[1.65fr_0.75fr]">
        <RouteMatrix
          train={train}
          darkMode={darkMode}
          panel={panel}
          panelSoft={panelSoft}
          textMuted={textMuted}
          textSoft={textSoft}
        />

        <TrainMetaPanel
          train={train}
          darkMode={darkMode}
          panel={panel}
          panelSoft={panelSoft}
          textMuted={textMuted}
        />
      </div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  sub,
  icon,
  accent,
  panel,
  textMuted,
}) {
  const accents = {
    emerald: "text-emerald-400 border-emerald-400/20",
    cyan: "text-cyan-400 border-cyan-400/20",
    amber: "text-amber-400 border-amber-400/20",
    rose: "text-rose-400 border-rose-400/20",
  };

  return (
    <motion.div
      whileHover={{ y: -3 }}
      className={`min-w-0 rounded-xl border p-4 ${panel}`}
    >
      <div className="flex items-center justify-between gap-3">
        <p className={`font-mono text-[10px] uppercase tracking-[0.16em] ${textMuted}`}>
          {label}
        </p>

        <div className={`rounded-md border p-1.5 ${accents[accent]}`}>
          {icon}
        </div>
      </div>

      <div className="mt-3 min-w-0">
        <div className="break-words text-lg font-semibold leading-tight">
          {value}
        </div>

        <p className={`mt-2 truncate font-mono text-[10px] uppercase tracking-wider ${textMuted}`}>
          {sub}
        </p>
      </div>
    </motion.div>
  );
}

function JourneyTelemetry({
  train,
  darkMode,
  panel,
  panelSoft,
  textMuted,
}) {
  return (
    <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
      <SectionHeader
        eyebrow="ROUTE_STREAM"
        title="Journey telemetry"
        meta={`${train.source} → ${train.destination}`}
        textMuted={textMuted}
      />

      <div className={`mt-4 rounded-xl border p-4 sm:p-5 ${panelSoft}`}>
        <div className="flex items-start justify-between gap-5">
          <div className="min-w-0">
            <p
              className="truncate text-sm font-semibold tracking-[0.01em] sm:text-base"
              style={{
                fontFamily:
                  '"Trebuchet MS", "Arial Narrow", "Segoe UI", sans-serif',
              }}
            >
              {train.source}
            </p>
            <p className={`mt-1 font-mono text-[10px] uppercase tracking-wider ${textMuted}`}>
              {train.route?.[0]?.station_code ?? "SRC"}
            </p>
          </div>

          <div className="min-w-0 text-right">
            <p
              className="truncate text-sm font-semibold tracking-[0.01em] sm:text-base"
              style={{
                fontFamily:
                  '"Trebuchet MS", "Arial Narrow", "Segoe UI", sans-serif',
              }}
            >
              {train.destination}
            </p>
            <p className={`mt-1 font-mono text-[10px] uppercase tracking-wider ${textMuted}`}>
              {train.route?.[train.route.length - 1]?.station_code ?? "DST"}
            </p>
          </div>
        </div>

        <div className="relative mt-5 h-16">
          <div
            className={`absolute left-4 right-4 top-1/2 h-px ${
              darkMode ? "bg-emerald-300/30" : "bg-emerald-700/25"
            }`}
          />

          <div className="absolute left-4 right-4 top-1/2 flex -translate-y-1/2 justify-between">
            {Array.from({ length: 24 }).map((_, index) => (
              <span
                key={index}
                className={`h-5 w-px ${
                  darkMode ? "bg-white/15" : "bg-slate-400/35"
                }`}
              />
            ))}
          </div>

          <div className="absolute left-2 top-1/2 z-20 h-4 w-4 -translate-y-1/2 rounded-full bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.65)]" />
          <div className="absolute right-2 top-1/2 z-20 h-4 w-4 -translate-y-1/2 rounded-full bg-cyan-400 shadow-[0_0_18px_rgba(34,211,238,0.55)]" />

          <motion.div
            className="absolute top-1/2 z-30 -translate-y-1/2"
            initial={{ left: "3%" }}
            animate={{ left: "91%" }}
            transition={{
              duration: 6,
              repeat: Infinity,
              ease: "linear",
            }}
          >
            <motion.div
              animate={{ y: [0, -2, 0] }}
              transition={{
                duration: 0.65,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className={`rounded-lg border p-2 shadow-lg ${
                darkMode
                  ? "border-emerald-300/25 bg-[#071015] text-emerald-300"
                  : "border-emerald-600/20 bg-white text-emerald-700"
              }`}
            >
              <TrainFront size={20} />
            </motion.div>
          </motion.div>
        </div>

        <div className={`mt-1 flex items-center justify-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] ${textMuted}`}>
          <span>{train.route?.[0]?.station_code ?? "SRC"}</span>
          <ArrowRight size={13} />
          <span>{train.route?.[train.route.length - 1]?.station_code ?? "DST"}</span>
        </div>
      </div>
    </section>
  );
}

function RouteMatrix({
  train,
  darkMode,
  panel,
  panelSoft,
  textMuted,
  textSoft,
}) {
  return (
    <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
      <SectionHeader
        eyebrow="STOP_MATRIX"
        title="Route sequence"
        meta={`${train.route.length} scheduled halts`}
        textMuted={textMuted}
      />

      <div className="relative mt-5">
        <motion.div
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ duration: 0.8 }}
          style={{ transformOrigin: "top" }}
          className={`absolute bottom-4 left-[17px] top-4 w-px ${
            darkMode
              ? "bg-gradient-to-b from-emerald-300/50 via-cyan-300/25 to-white/5"
              : "bg-gradient-to-b from-emerald-600/40 via-cyan-600/20 to-slate-300"
          }`}
        />

        <div className="space-y-3">
          {train.route.map((stop, index) => (
            <motion.div
              key={`${stop.station_code}-${index}`}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(index * 0.025, 0.45) }}
              className="relative flex gap-3"
            >
              <div
                className={`relative z-10 mt-4 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border ${
                  darkMode
                    ? "border-emerald-300/25 bg-[#071015]"
                    : "border-emerald-700/20 bg-white"
                }`}
              >
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              </div>

              <motion.div
                whileHover={{ x: 3 }}
                className={`min-w-0 flex-1 rounded-xl border p-4 ${panelSoft}`}
              >
                <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] text-emerald-400">
                        STOP_{String(index + 1).padStart(2, "0")}
                      </span>

                      <span className={`font-mono text-[10px] uppercase tracking-wider ${textSoft}`}>
                        {stop.station_code}
                      </span>
                    </div>

                    <p
                      className="mt-1 break-words text-[1.03rem] font-medium tracking-[0.01em]"
                      style={{
                        fontFamily:
                          '"Trebuchet MS", "Arial Narrow", "Segoe UI", sans-serif',
                      }}
                    >
                      {stop.station_name}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-x-5 gap-y-1 text-sm sm:text-right">
                    <div>
                      <p className={`font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
                        arr
                      </p>
                      <p className="mt-1">{stop.arrival ?? "—"}</p>
                    </div>

                    <div>
                      <p className={`font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
                        dep
                      </p>
                      <p className="mt-1">{stop.departure ?? "—"}</p>
                    </div>

                    <p className={`col-span-2 mt-1 font-mono text-[10px] uppercase tracking-wider ${textSoft}`}>
                      D{stop.day} · {stop.distance_km} km
                    </p>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TrainMetaPanel({
  train,
  darkMode,
  panel,
  panelSoft,
  textMuted,
}) {
  return (
    <aside className="grid content-start gap-5">
      <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
        <SectionHeader
          eyebrow="SERVICE_PROFILE"
          title="Train profile"
          meta="live view"
          textMuted={textMuted}
        />

        <div className="mt-4 grid gap-3">
          <MetaRow
            label="SERVICE TYPE"
            value={train.type}
            panelSoft={panelSoft}
            textMuted={textMuted}
          />
          <MetaRow
            label="RUNNING DAYS"
            value={train.runs_days}
            panelSoft={panelSoft}
            textMuted={textMuted}
          />
          <MetaRow
            label="TOTAL DISTANCE"
            value={`${train.distance_km} km`}
            panelSoft={panelSoft}
            textMuted={textMuted}
          />
          <MetaRow
            label="SCHEDULED TIME"
            value={train.travel_time}
            panelSoft={panelSoft}
            textMuted={textMuted}
          />
        </div>
      </section>

      <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
        <SectionHeader
          eyebrow="NETWORK_SIGNAL"
          title="Route density"
          meta="derived"
          textMuted={textMuted}
        />

        <div className="mt-5 flex items-end gap-2">
          {[62, 85, 43, 71, 54, 92, 68, 79].map((height, index) => (
            <motion.div
              key={index}
              initial={{ height: 0 }}
              animate={{ height }}
              transition={{ delay: index * 0.04, duration: 0.45 }}
              className={`flex-1 rounded-t-sm ${
                darkMode ? "bg-emerald-300/70" : "bg-emerald-600/70"
              }`}
            />
          ))}
        </div>

        <div className={`mt-3 flex justify-between font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
          <span>origin</span>
          <span>corridor</span>
          <span>terminal</span>
        </div>
      </section>
    </aside>
  );
}

function MetaRow({
  label,
  value,
  panelSoft,
  textMuted,
}) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${panelSoft}`}>
      <p className={`font-mono text-[9px] uppercase tracking-[0.16em] ${textMuted}`}>
        {label}
      </p>
      <p className="mt-1 text-sm font-medium">{value ?? "—"}</p>
    </div>
  );
}

function StationDashboard({
  station,
  darkMode,
  panel,
  panelSoft,
  textMuted,
  textSoft,
  openTrainFromStation,
}) {
  const arriving = station.trains.filter((item) => item.arrival).length;
  const departing = station.trains.filter((item) => item.departure).length;

  return (
    <section className="mt-5 grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="STATION"
          value={station.station_code}
          sub={station.station_name}
          icon={<MapPin size={18} />}
          accent="cyan"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="TRAINS FOUND"
          value={<AnimatedNumber value={station.train_count} />}
          sub="services"
          icon={<TrainFront size={18} />}
          accent="emerald"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="ARRIVAL EVENTS"
          value={<AnimatedNumber value={arriving} />}
          sub="scheduled entries"
          icon={<Clock3 size={18} />}
          accent="amber"
          panel={panel}
          textMuted={textMuted}
        />

        <MetricCard
          label="DEPARTURE EVENTS"
          value={<AnimatedNumber value={departing} />}
          sub="scheduled exits"
          icon={<Navigation size={18} />}
          accent="rose"
          panel={panel}
          textMuted={textMuted}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.45fr_0.55fr]">
        <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
          <SectionHeader
            eyebrow="STATION_TRAFFIC"
            title={`${station.station_name} services`}
            meta={`${station.train_count} trains`}
            textMuted={textMuted}
          />

          <div className="mt-4 grid gap-3">
            {station.trains.map((item, index) => (
              <motion.button
                key={`${item.number}-${index}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.02, 0.4) }}
                whileHover={{ x: 3 }}
                onClick={() => openTrainFromStation(item.number)}
                className={`w-full rounded-xl border p-4 text-left ${panelSoft}`}
              >
                <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] uppercase tracking-wider text-emerald-400">
                        TRAIN_{item.number}
                      </span>
                      <span className={`font-mono text-[10px] uppercase tracking-wider ${textSoft}`}>
                        {item.type}
                      </span>
                    </div>

                    <p className="mt-1 font-medium">{item.name}</p>
                    <p className={`mt-1 text-sm ${textMuted}`}>
                      {item.source} → {item.destination}
                    </p>
                  </div>

                  <div className="flex gap-6 text-sm">
                    <div>
                      <p className={`font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
                        arr
                      </p>
                      <p className="mt-1">{item.arrival ?? "—"}</p>
                    </div>

                    <div>
                      <p className={`font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
                        dep
                      </p>
                      <p className="mt-1">{item.departure ?? "—"}</p>
                    </div>

                    <ArrowRight size={16} className="mt-4 text-emerald-400" />
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </section>

        <section className={`rounded-2xl border p-4 sm:p-5 ${panel}`}>
          <SectionHeader
            eyebrow="TRAFFIC_PROFILE"
            title="Service distribution"
            meta="analytics"
            textMuted={textMuted}
          />

          <div className="mt-6 flex justify-center">
            <div className="relative flex h-44 w-44 items-center justify-center rounded-full bg-[conic-gradient(#34d399_0_45%,#22d3ee_45%_76%,#fb7185_76%_100%)]">
              <div
                className={`flex h-28 w-28 flex-col items-center justify-center rounded-full ${
                  darkMode ? "bg-[#0b171d]" : "bg-white"
                }`}
              >
                <span className="text-2xl font-semibold">
                  {station.train_count}
                </span>
                <span className={`font-mono text-[9px] uppercase tracking-wider ${textMuted}`}>
                  services
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-2">
            <Legend label="Through traffic" colorClass="bg-emerald-400" textMuted={textMuted} />
            <Legend label="Arrival events" colorClass="bg-cyan-400" textMuted={textMuted} />
            <Legend label="Departure events" colorClass="bg-rose-400" textMuted={textMuted} />
          </div>
        </section>
      </div>
    </section>
  );
}

function Legend({
  label,
  colorClass,
  textMuted,
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${colorClass}`} />
        <span className={`text-sm ${textMuted}`}>{label}</span>
      </div>
    </div>
  );
}

function EmptyDashboard({
  panel,
  panelSoft,
  textMuted,
  darkMode,
}) {
  return (
    <section className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
      <div className={`rounded-2xl border p-5 ${panel}`}>
        <SectionHeader
          eyebrow="SYSTEM_IDLE"
          title="Awaiting query"
          meta="ready"
          textMuted={textMuted}
        />

        <div className={`mt-4 rounded-xl border p-6 ${panelSoft}`}>
          <div className="grid gap-4 sm:grid-cols-3">
            <GhostMetric label="TRAIN DATA" value="10K+" textMuted={textMuted} />
            <GhostMetric label="QUERY MODE" value="READY" textMuted={textMuted} />
            <GhostMetric label="NETWORK" value="INDIA" textMuted={textMuted} />
          </div>

          <div className="relative mt-8 h-28 overflow-hidden rounded-lg">
            <div
              className={`absolute left-0 right-0 top-1/2 h-px ${
                darkMode ? "bg-emerald-300/25" : "bg-emerald-700/20"
              }`}
            />

            {Array.from({ length: 22 }).map((_, index) => (
              <span
                key={index}
                className={`absolute top-1/2 h-5 w-px -translate-y-1/2 ${
                  darkMode ? "bg-white/10" : "bg-slate-300"
                }`}
                style={{
                  left: `${(index / 21) * 100}%`,
                }}
              />
            ))}

            <motion.div
              className="absolute top-1/2 -translate-y-1/2 text-emerald-400"
              animate={{ left: ["0%", "94%"] }}
              transition={{
                duration: 5,
                repeat: Infinity,
                ease: "linear",
              }}
            >
              <TrainFront size={24} />
            </motion.div>
          </div>
        </div>
      </div>

      <div className={`rounded-2xl border p-5 ${panel}`}>
        <SectionHeader
          eyebrow="DATA_CORE"
          title="Telemetry status"
          meta="nominal"
          textMuted={textMuted}
        />

        <div className="mt-5 space-y-4">
          <StatusBar label="Train index" value={92} textMuted={textMuted} />
          <StatusBar label="Station index" value={84} textMuted={textMuted} />
          <StatusBar label="Route matrix" value={96} textMuted={textMuted} />
        </div>
      </div>
    </section>
  );
}

function GhostMetric({
  label,
  value,
  textMuted,
}) {
  return (
    <div>
      <p className={`font-mono text-[9px] uppercase tracking-[0.16em] ${textMuted}`}>
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function StatusBar({
  label,
  value,
  textMuted,
}) {
  return (
    <div>
      <div className="mb-2 flex justify-between gap-3">
        <span className={`text-sm ${textMuted}`}>{label}</span>
        <span className="font-mono text-xs text-emerald-400">{value}%</span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-500/10">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.7 }}
          className="h-full rounded-full bg-emerald-400"
        />
      </div>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  meta,
  textMuted,
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-emerald-400">
          {eyebrow}
        </p>
        <h2 className="mt-1 text-lg font-semibold sm:text-xl">{title}</h2>
      </div>

      <p className={`font-mono text-[9px] uppercase tracking-[0.16em] ${textMuted}`}>
        {meta}
      </p>
    </div>
  );
}

function LoadingMatrix({
  panel,
  darkMode,
}) {
  return (
    <div className={`mt-5 rounded-2xl border p-5 ${panel}`}>
      <div className="animate-pulse">
        <div
          className={`h-3 w-32 rounded ${
            darkMode ? "bg-white/10" : "bg-slate-300"
          }`}
        />

        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className={`h-28 rounded-xl ${
                darkMode ? "bg-white/5" : "bg-slate-200/80"
              }`}
            />
          ))}
        </div>

        <div
          className={`mt-5 h-36 rounded-xl ${
            darkMode ? "bg-white/5" : "bg-slate-200/80"
          }`}
        />
      </div>
    </div>
  );
}

function AnimatedNumber({
  value,
  suffix = "",
  duration = 750,
}) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const target = Number(value);

    if (Number.isNaN(target)) return;

    let startTime = null;
    let frameId;

    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;

      const progress = Math.min(
        (timestamp - startTime) / duration,
        1
      );

      setDisplayValue(target * progress);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      }
    };

    frameId = requestAnimationFrame(animate);

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, [value, duration]);

  const isInteger = Number(value) % 1 === 0;

  return (
    <span>
      {isInteger
        ? Math.round(displayValue).toLocaleString()
        : displayValue.toFixed(1)}
      {suffix}
    </span>
  );
}

export default App;
