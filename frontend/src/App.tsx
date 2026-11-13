import { useCallback, useMemo, useState } from "react";

import { AnalysisCenter } from "./features/AnalysisCenter";
import { AgentPanel } from "./features/AgentPanel";
import { MarketPanel } from "./features/MarketPanel";
import { PortfolioPanel } from "./features/PortfolioPanel";
import { TradingPanel } from "./features/TradingPanel";
import type { Agent } from "./game3d/agents";
import { agents } from "./game3d/agents";
import { OfficeScene3D } from "./game3d/OfficeScene3D";
import { supportsWebGL } from "./game3d/webgl";
import { createDemoSession, getMarketOverview, getPortfolio } from "./shared/api/client";
import type { AnalysisRun, MarketOverview, Portfolio, Simulation } from "./shared/api/types";

export function App() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [latestRun, setLatestRun] = useState<AnalysisRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const webglAvailable = useMemo(() => supportsWebGL(), []);
  const handleRunChange = useCallback((run:AnalysisRun|null)=>setLatestRun(run),[]);
  const displayAgents = useMemo(()=>agents.map(agent=>{
    let status:Agent["status"]="IDLE";
    if(latestRun?.status==="FAILED")status="ERROR";
    else if(latestRun?.status==="COMPLETED")status=latestRun.proposal?.status==="PENDING_APPROVAL"?"WAITING_APPROVAL":"COMPLETED";
    else if(latestRun?.status==="RUNNING"||latestRun?.status==="PENDING"){
      const result=latestRun.agent_results.find(item=>item.agent===agent.id.toUpperCase());
      if(result?.status==="COMPLETED")status="COMPLETED";
      else if(result?.status==="RUNNING")status=agent.id==="victor"?"REVIEWING":"ANALYZING";
      else if(agent.id==="alex"&&latestRun.agent_results.length===0)status="ANALYZING";
    }
    return {...agent,status};
  }),[latestRun]);
  const currentSelected=selectedAgent?displayAgents.find(agent=>agent.id===selectedAgent.id)??selectedAgent:null;

  const handleCreateSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await createDemoSession();
      const [loadedPortfolio, loadedMarket] = await Promise.all([
        getPortfolio(created.id, created.session_token),
        getMarketOverview(created.id, created.session_token),
      ]);
      setSimulation(created);
      setPortfolio(loadedPortfolio);
      setMarket(loadedMarket);
      setSessionToken(created.session_token);
      sessionStorage.setItem(
        "ai-trading-world-demo-session",
        JSON.stringify({ id: created.id, token: created.session_token }),
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Erro inesperado ao criar sessão.");
    } finally {
      setLoading(false);
    }
  };

  const refreshFinancials = async () => {
    if (!simulation || !sessionToken) return;
    const [loadedPortfolio, loadedMarket] = await Promise.all([
      getPortfolio(simulation.id, sessionToken),
      getMarketOverview(simulation.id, sessionToken),
    ]);
    setPortfolio(loadedPortfolio);
    setMarket(loadedMarket);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-mark">AW</div>
        <div><strong>AI Trading World</strong><span>Escritório de investimentos virtuais</span></div>
        <div className="demo-badge">DEMO · CAPITAL FICTÍCIO</div>
      </header>
      <div className="workspace">
        <div className="scene-column">
          <div className="scene-frame" aria-label="Escritório 3D isométrico">
            {webglAvailable ? (
              <OfficeScene3D agents={displayAgents} selectedAgent={currentSelected} onSelectAgent={setSelectedAgent} />
            ) : (
              <div className="webgl-fallback" role="status">
                <div className="fallback-icon">3D</div>
                <h2>Visualização 3D indisponível</h2>
                <p>Seu navegador não ofereceu WebGL. A carteira e a seleção de agentes continuam acessíveis.</p>
              </div>
            )}
            <div className="scene-caption"><span>Escritório central</span><small>{webglAvailable ? "Scroll para zoom" : "Modo sem WebGL"}</small></div>
          </div>
          <nav className="agent-shortcuts" aria-label="Selecionar agente">
            {displayAgents.map((agent) => (
              <button key={agent.id} type="button" aria-pressed={selectedAgent?.id === agent.id} onClick={() => setSelectedAgent(agent)}>
                <span style={{ backgroundColor: agent.color }} />{agent.name}
              </button>
            ))}
          </nav>
          <AnalysisCenter simulationId={simulation?.id??null} sessionToken={sessionToken} onRunChange={handleRunChange} onPortfolioChanged={refreshFinancials}/>
          <TradingPanel
            simulationId={simulation?.id ?? null}
            sessionToken={sessionToken}
            market={market}
            onPortfolioChanged={refreshFinancials}
          />
        </div>
        <aside className="sidebar">
          <PortfolioPanel simulation={simulation} portfolio={portfolio} loading={loading} error={error} onCreate={handleCreateSession} />
          <MarketPanel market={market} loading={loading} />
          <AgentPanel agent={currentSelected} result={latestRun?.agent_results.find(item=>item.agent===currentSelected?.id.toUpperCase())} />
        </aside>
      </div>
    </main>
  );
}
