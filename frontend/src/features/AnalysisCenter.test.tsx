import { fireEvent, render, screen } from "@testing-library/react";

import * as api from "../shared/api/client";
import type { AnalysisRun, TradeProposal } from "../shared/api/types";
import { AnalysisCenter } from "./AnalysisCenter";

vi.mock("../shared/api/client",()=>({
  listAnalysisRuns:vi.fn(),createAnalysisRun:vi.fn(),getAnalysisRun:vi.fn(),cancelAnalysisRun:vi.fn(),
  approveProposal:vi.fn(),rejectProposal:vi.fn(),
}));

const proposal:TradeProposal={id:"proposal",asset:"BTC/USDT",side:"BUY",origin:"AI_AGENT",analysis_run_id:"run",evidence:{},requested_quantity:"0.005",requested_amount:"250.00000000",reference_price:"50000.00000000",estimated_notional:"250.00000000",estimated_fee:"0.25000000",estimated_total:"250.25000000",justification:"Alex, Maya e Victor",risk_summary:{approved:true,codes:[],metrics:{},policy_version:1},version:1,status:"PENDING_APPROVAL",snapshot_id:"snapshot",authorized_at:null,expires_at:"2099-01-01",created_at:"2026-01-01"};
const run:AnalysisRun={id:"run",simulation_id:"session",snapshot_id:"snapshot",requested_assets:["BTC/USDT"],status:"COMPLETED",current_node:"completed",provider:"deterministic_mock",provider_mode:"mock",model_name:"deterministic-mock-v1",conclusion:{action:"HOLD",summary:"Evidência insuficiente."},error:{},input_tokens:0,output_tokens:0,estimated_cost_usd:"0",attempts:1,started_at:"2026-01-01",completed_at:"2026-01-01",created_at:"2026-01-01",updated_at:"2026-01-01",agent_results:[{id:1,agent:"ALEX",role:"Análise técnica",status:"COMPLETED",provider:"deterministic_mock",model_name:"deterministic-mock-v1",schema_version:1,indicators:{"BTC/USDT":{}},evidence:{},hypotheses:[],conclusion:{summary:"Sem histórico suficiente."},disagreements:[],input_tokens:0,output_tokens:0,estimated_cost_usd:"0",started_at:"2026-01-01",completed_at:"2026-01-01"}],proposal:null,mock_notice:"Análise gerada pelo mock determinístico."};

describe("AnalysisCenter",()=>{
  beforeEach(()=>{
    vi.mocked(api.listAnalysisRuns).mockResolvedValue({count:0,limit:10,offset:0,results:[]});
    vi.mocked(api.createAnalysisRun).mockResolvedValue(run);
  });
  afterEach(()=>vi.clearAllMocks());

  it("inicia uma análise mock e exibe HOLD sem bloquear a interface",async()=>{
    const changed=vi.fn(),refresh=vi.fn().mockResolvedValue(undefined);
    render(<AnalysisCenter simulationId="session" sessionToken="token" onRunChange={changed} onPortfolioChanged={refresh}/>);
    fireEvent.click(screen.getByRole("button",{name:"Iniciar análise"}));
    expect(await screen.findByText("Decisão final: HOLD")).toBeInTheDocument();
    expect(screen.getByText("Análise gerada pelo mock determinístico.")).toBeInTheDocument();
    expect(api.createAnalysisRun).toHaveBeenCalledWith("session","token",["BTC/USDT"],expect.any(String));
    expect(changed).toHaveBeenCalledWith(expect.objectContaining({id:"run"}));
  });

  it("aprova uma proposta de agente pelo fluxo financeiro existente",async()=>{
    const withProposal={...run,conclusion:{action:"BUY",summary:"Sinal válido."},proposal};
    vi.mocked(api.listAnalysisRuns).mockResolvedValue({count:1,limit:10,offset:0,results:[withProposal]});
    vi.mocked(api.approveProposal).mockResolvedValue({proposal:{...proposal,status:"EXECUTED"},order:{id:"order",proposal_id:"proposal",asset:"BTC/USDT",side:"BUY",order_type:"MARKET",state:"FILLED",requested_quantity:"0.005",execution_price:"50050.00000000",reserved_amount:"250.25000000",total_fee:"0.25000000",market_snapshot_id:"snapshot",created_at:"2026-01-01",executed_at:"2026-01-01",fills:[]},duplicate:false});
    const refresh=vi.fn().mockResolvedValue(undefined);
    render(<AnalysisCenter simulationId="session" sessionToken="token" onRunChange={vi.fn()} onPortfolioChanged={refresh}/>);
    fireEvent.click(await screen.findByRole("button",{name:"Aprovar proposta virtual"}));
    expect(await screen.findByText("Proposta dos agentes aprovada e executada virtualmente.")).toBeInTheDocument();
    expect(api.approveProposal).toHaveBeenCalledOnce();
    expect(refresh).toHaveBeenCalledOnce();
  });
});
