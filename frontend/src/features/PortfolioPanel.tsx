import type { Portfolio, Simulation } from "../shared/api/types";

interface Props { simulation:Simulation|null; portfolio:Portfolio|null; loading:boolean; error:string|null; onCreate:()=>void }
const formatAmount = (value?:string) => value ? new Intl.NumberFormat("pt-BR", {minimumFractionDigits:2, maximumFractionDigits:2}).format(Number(value)) : "—";

export function PortfolioPanel({ simulation, portfolio, loading, error, onCreate }: Props) {
  return <section className="panel portfolio-panel" aria-busy={loading}>
    <div><p className="eyebrow">Carteira virtual</p><h1>AI Trading World <span>3D</span></h1></div>
    {error && <p className="error" role="alert">{error}</p>}
    {simulation && portfolio ? <>
      <div className="balance"><span>Patrimônio virtual</span><strong>{formatAmount(portfolio.total_equity)} <small>USDT</small></strong></div>
      <div className="balance-breakdown"><span>Disponível <strong>{formatAmount(portfolio.available_balance)}</strong></span><span>Reservado <strong>{formatAmount(portfolio.reserved_balance)}</strong></span></div>
      <div className="session-line"><span className="live-dot" /> Sessão demo ativa</div>
      <p className="demo-notice">{portfolio.demo_notice}</p>
    </> : <>
      <p className="muted">Inicie uma empresa com 10.000 USDT exclusivamente fictícios.</p>
      <button type="button" className="primary-button" onClick={onCreate} disabled={loading}>{loading ? "Criando sessão…" : "Criar sessão demo"}</button>
    </>}
  </section>;
}
