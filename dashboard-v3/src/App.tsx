import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Terminal, Activity, ShieldAlert, Cpu, Settings, 
  CheckCircle2, AlertTriangle, Menu, Search,
  BarChart3, Workflow
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// In production (HF Spaces), we use relative paths. In local dev, we point to the server.
const SERVER_URL = window.location.hostname === 'localhost' ? 'http://localhost:7860' : '';

// --- Types ---

interface AgentThought {
  role: string;
  thought: string;
  timestamp: number;
}

interface LogEntry {
  level: string;
  service: string;
  message: string;
}

interface Alert {
  message: string;
  severity: string;
  service: string;
}

interface RecoveryTask {
  task_name: string;
  completed: boolean;
}

interface ServiceNode {
  name: string;
  healthy: boolean;
  active_remediations: string[];
}

interface ServiceTopology {
  services: Record<string, ServiceNode>;
}

interface DashboardState {
  current_thoughts: AgentThought[];
  logs: LogEntry[];
  alerts: Alert[];
  reward: number;
  actions_in_progress: string[];
  recovery_status: RecoveryTask[];
  topology?: ServiceTopology;
}

// --- Sub-Components ---

interface SegmentedBarProps {
  value: number;
  segments?: number;
  colorClass?: string;
}

const SegmentedBar: React.FC<SegmentedBarProps> = ({ value, segments = 15, colorClass = "bg-accent-blue" }) => {
  return (
    <div className="flex gap-0.5 h-2.5 w-full bg-white/5 rounded-sm overflow-hidden">
      {Array.from({ length: segments }).map((_, i) => (
        <div 
          key={i}
          className={`flex-1 rounded-[1px] transition-all duration-500 ${
            i < (value / 100) * segments ? colorClass : "bg-white/5"
          }`}
        />
      ))}
    </div>
  );
};

interface CardProps {
  title: string;
  icon?: any;
  children: React.ReactNode;
  className?: string;
}

const Card: React.FC<CardProps> = ({ title, icon: Icon, children, className = "" }) => (
  <div className={`glass-card flex flex-col ${className}`}>
    <div className="flex items-center gap-2 mb-4 border-b border-white/5 pb-2 text-slate-100">
      {Icon && <Icon className="w-4 h-4 text-accent-blue" />}
      <h2 className="text-sm font-bold tracking-tight">{title}</h2>
    </div>
    <div className="flex-1 overflow-hidden">{children}</div>
  </div>
);

// --- Main App ---

export default function App() {
  const [state, setState] = useState<DashboardState | null>(null);

  useEffect(() => {
    const poll = setInterval(async () => {
      try {
        const res = await axios.get(`${SERVER_URL}/state`);
        if (!res.data || res.data.error) {
          // If not initialized, don't crash, just show waiting state
          return;
        }
        
        const obs = res.data.observation || {};
        const rewards = res.data.rewards || [];
        
        setState({
          current_thoughts: obs.current_thoughts || [],
          logs: obs.logs || [],
          alerts: obs.alerts || [],
          reward: rewards.length > 0 ? rewards[rewards.length - 1] : 0, 
          actions_in_progress: obs.actions_in_progress || [],
          recovery_status: obs.recovery_status || [],
          topology: obs.topology
        });
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1500);
    return () => clearInterval(poll);
  }, []);

  if (!state) return (
    <div className="h-screen w-screen flex items-center justify-center bg-bg-dark">
      <div className="flex flex-col items-center gap-4 text-accent-blue animate-pulse">
        <Activity className="w-12 h-12" />
        <span className="font-mono text-xs tracking-[0.3em] uppercase opacity-70">
          Initializing Command Center...
        </span>
      </div>
    </div>
  );

  const activeRole = state.current_thoughts.length > 0 ? state.current_thoughts[state.current_thoughts.length - 1].role : "";

  return (
    <div className="min-h-screen flex flex-col p-4 gap-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <header className="flex justify-between items-center bg-white/5 backdrop-blur-md border border-white/10 rounded-xl px-6 py-3">
        <div className="flex items-center gap-4">
          <Menu className="w-6 h-6 text-slate-400 cursor-pointer" />
          <h1 className="text-xl font-extrabold tracking-tighter bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            LLAMA-IR: AUTONOMOUS INCIDENT ORCHESTRATOR
          </h1>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-lg border border-white/5 text-[10px] font-mono">
            <span className="text-slate-500 uppercase tracking-wider">Mode:</span>
            <span className="text-accent-blue font-bold glow-blue">HACKATHON_EVAL</span>
          </div>
          <div className="flex items-center gap-2 bg-black/40 px-3 py-1.5 rounded-lg border border-white/5 text-[10px] font-mono">
            <span className="text-slate-500 uppercase tracking-wider">Status:</span>
            <span className="text-accent-green font-bold glow-green">LIVE</span>
          </div>
        </div>
      </header>

      {/* Grid Layout */}
      <main className="flex-1 grid grid-cols-12 gap-4 h-[calc(100vh-100px)] overflow-hidden">
        
        {/* Left Column (3) */}
        <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
          <Card title="THOUGHT STREAM" icon={Terminal} className="flex-1 min-h-0">
            <div className="h-full overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-white/10 custom-scroll">
              <AnimatePresence initial={false}>
                {state.current_thoughts.slice().reverse().map((t, i) => (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    key={`thought-${i}-${t.timestamp}`}
                    className="flex flex-col gap-1 text-[11px] leading-relaxed border-l border-white/5 pl-2"
                  >
                    <span className={`font-black uppercase tracking-widest ${
                      t.role === 'Supervisor' ? 'text-accent-blue' :
                      t.role === 'Investigator' ? 'text-accent-orange' :
                      'text-accent-green'
                    }`}>{t.role} Agent</span>
                    <span className="text-slate-400 font-mono italic">{t.thought}</span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </Card>

          <Card title="AGENT PERFORMANCE" icon={BarChart3} className="shrink-0">
            <div className="space-y-4 py-1">
              <div>
                <div className="metric-label flex justify-between text-[10px] font-black uppercase text-slate-500 mb-1">
                  <span>Reward Index:</span> 
                  <span className="text-white">{Math.round(state.reward * 100)}%</span>
                </div>
                <SegmentedBar value={state.reward * 100} segments={15} colorClass="bg-gradient-to-r from-accent-red to-accent-green shadow-[0_0_8px_rgba(34,197,94,0.3)]" />
              </div>
              {[
                { l: "Autonomous Speed", v: state.current_thoughts.length > 5 ? 98 : 85, c: "bg-accent-blue" },
                { l: "Triage Accuracy", v: state.alerts.length > 0 ? Math.round((1 - (state.alerts.filter(a => a.severity === 'critical').length / state.alerts.length)) * 100) : 100, c: "bg-accent-orange" },
                { l: "System Stability", v: state.topology ? Math.round((Object.values(state.topology.services).filter(s => s.healthy).length / Object.keys(state.topology.services).length) * 100) : 100, c: "bg-accent-green" }
              ].map(m => (
                <div key={m.l}>
                  <div className="metric-label flex justify-between text-[10px] font-black uppercase text-slate-500 mb-1">
                    <span>{m.l}:</span> 
                    <span className="text-white">{m.v}%</span>
                  </div>
                  <SegmentedBar value={m.v} segments={15} colorClass={m.c} />
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Middle Column (6) */}
        <div className="col-span-6 flex flex-col gap-4 overflow-hidden">
          <Card title="SERVICE TOPOLOGY" icon={Workflow} className="flex-[2] min-h-0">
            <div className="h-full relative flex flex-col items-center justify-center p-8 bg-black/40 rounded-lg border border-white/5 overflow-hidden">
              <div className="flex flex-wrap items-center justify-center gap-6 w-full max-w-2xl px-4">
                 {state.topology && Object.values(state.topology.services).map((service) => (
                   <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    key={service.name}
                    className={`relative p-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 min-w-[140px] ${
                      service.healthy 
                        ? 'bg-accent-green/5 border-accent-green/20' 
                        : 'bg-accent-red/10 border-accent-red/40 shadow-[0_0_20px_rgba(255,51,51,0.2)]'
                    }`}
                   >
                     {service.healthy ? <ShieldAlert className="w-6 h-6 text-accent-green opacity-50" /> : <AlertTriangle className="w-6 h-6 text-accent-red animate-pulse" />}
                     <div className="text-center">
                        <span className="text-[10px] font-black text-white block uppercase tracking-tighter truncate max-w-[120px]">{service.name}</span>
                        <span className={`text-[8px] font-bold ${service.healthy ? 'text-accent-green' : 'text-accent-red animate-pulse'}`}>
                          {service.healthy ? 'HEALTHY' : 'CRITICAL_LATENCY'}
                        </span>
                     </div>
                     {!service.healthy && service.active_remediations.length > 0 && (
                        <div className="absolute -top-2 -right-2 bg-accent-blue text-[8px] font-black px-1.5 py-0.5 rounded-full animate-bounce shadow-lg">
                          REPAIRING...
                        </div>
                     )}
                   </motion.div>
                 ))}
                 {!state.topology && <div className="text-slate-500 font-mono text-xs italic animate-pulse">Mapping cluster topology...</div>}
              </div>
              <div className="absolute top-4 right-4 flex items-center gap-2 text-[10px] font-black text-slate-600 bg-white/5 px-3 py-1 rounded-full border border-white/5">
                 <div className="w-2 h-2 rounded-full bg-accent-blue animate-ping" />
                 REAL-TIME MAPPED
              </div>
            </div>
          </Card>

          <div className="flex-[1] grid grid-cols-2 gap-4 h-full min-h-0">
            <Card title="ACTIVE AGENTS" icon={Activity}>
              <div className="flex justify-around items-center h-full py-2">
                {[
                  { r: "Triage", i: Search, c: "text-accent-blue" },
                  { r: "Investigator", i: Cpu, c: "text-accent-orange" },
                  { r: "Remediator", i: Settings, c: "text-accent-red" },
                  { r: "Reporter", i: BarChart3, c: "text-accent-green" },
                ].map((a, i) => (
                  <div key={i} className="flex flex-col items-center group">
                    <div className="relative">
                      <div className={`w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center transition-all group-hover:scale-110 shadow-lg ${
                        activeRole.toLowerCase().includes(a.r.toLowerCase()) ? 'border-accent-blue glow-blue bg-accent-blue/5' : ''
                      }`}>
                        <a.i className={`w-7 h-7 ${a.c}`} />
                      </div>
                      <div className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-bg-dark ${
                        activeRole.toLowerCase().includes(a.r.toLowerCase()) ? 'bg-accent-blue animate-pulse' : 'bg-slate-700'
                      }`} />
                    </div>
                    <span className={`text-[10px] font-black uppercase mt-2 tracking-tighter ${
                      activeRole.toLowerCase().includes(a.r.toLowerCase()) ? 'text-white' : 'text-slate-500'
                    }`}>{a.r}</span>
                  </div>
                ))}
              </div>
            </Card>
            <Card title="ENVIRONMENT LOGS" icon={Terminal}>
              <div className="h-full overflow-y-auto space-y-1.5 font-mono text-[10px] pr-2 scrollbar-thin scrollbar-thumb-white/10 custom-scroll">
                {state.logs.map((l, i) => (
                  <div key={i} className="flex gap-2 p-1 border-b border-white/5">
                    <span className={`font-bold uppercase ${l.level === 'ERROR' ? 'text-accent-red' : l.level === 'WARN' ? 'text-accent-orange' : 'text-accent-blue'}`}>{l.level}:</span>
                    <span className="text-slate-400 leading-tight">[{l.service}] {l.message}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>

        {/* Right Column (3) */}
        <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
          <Card title="CRITICAL INCIDENTS" icon={ShieldAlert}>
            <div className="space-y-3 h-full overflow-y-auto pr-2 custom-scroll">
              {state.alerts.length > 0 ? state.alerts.map((a, i) => (
                <div key={i} className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex gap-4 items-center group cursor-help hover:bg-red-500/20 transition-all border-l-4 border-l-accent-red">
                  <div className="p-2 bg-accent-red/20 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-accent-red" />
                  </div>
                  <div className="flex flex-col overflow-hidden">
                    <span className="text-[10px] font-black uppercase tracking-wider text-accent-red">Priority: {a.severity}</span>
                    <span className="text-[11px] font-bold text-slate-200 leading-tight truncate">{a.service}</span>
                    <span className="text-[10px] text-slate-400 italic leading-tight mt-1">{a.message}</span>
                  </div>
                </div>
              )) : (
                <div className="text-center text-slate-500 py-4 text-xs font-mono italic">No critical alerts detected...</div>
              )}
            </div>
          </Card>

          <Card title="ACTION BACKLOG" icon={Workflow} className="min-h-0">
            <div className="space-y-3 py-1">
              {state.actions_in_progress.length > 0 ? (
                state.actions_in_progress.map((act, i) => (
                  <div key={i} className="flex items-center gap-3 bg-white/5 p-3 rounded-lg border-l-2 border-l-accent-blue animate-pulse backdrop-blur-sm">
                    <Settings className="w-4 h-4 animate-spin text-accent-blue" />
                    <span className="text-[10px] font-black text-slate-200 uppercase tracking-tight">{act}</span>
                  </div>
                ))
              ) : (
                <div className="text-center text-slate-500 py-4 text-xs font-mono italic">Waiting for agents to initiate actions...</div>
              )}
            </div>
          </Card>

          <Card title="RESOLUTION CHECKLIST" icon={CheckCircle2} className="flex-1 min-h-0 overflow-hidden">
             <div className="h-full overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-white/10 custom-scroll">
               {state.recovery_status.map((item, i) => (
                 <div key={i} className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${item.completed ? 'bg-accent-green/5' : ''}`}>
                   <div className={`w-6 h-6 rounded-lg flex items-center justify-center border transition-all ${
                     item.completed ? 'bg-accent-green/20 border-accent-green/40' : 'bg-white/5 border-white/10'
                   }`}>
                     {item.completed ? <CheckCircle2 className="w-4 h-4 text-accent-green" /> : <div className="w-1.5 h-1.5 rounded-full bg-slate-700" />}
                   </div>
                   <div className="flex flex-col">
                     <span className={`text-[11px] font-black uppercase tracking-tight ${item.completed ? 'text-accent-green' : 'text-slate-400'}`}>
                       {item.task_name}
                     </span>
                     <span className="text-[9px] text-slate-600 font-mono">{item.completed ? 'VERIFIED' : 'PENDING'}</span>
                   </div>
                 </div>
               ))}
             </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
