import { fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";
vi.mock("./game3d/webgl",()=>({supportsWebGL:()=>false}));
describe("App",()=>{
  afterEach(()=>vi.restoreAllMocks());
  it("mantém HUD e agentes acessíveis sem WebGL",()=>{render(<App/>);expect(screen.getByText("Visualização 3D indisponível")).toBeInTheDocument();expect(screen.getByRole("button",{name:"Criar sessão demo"})).toBeEnabled();fireEvent.click(screen.getByRole("button",{name:"Maya"}));expect(screen.getByRole("heading",{name:"Maya"})).toBeInTheDocument();expect(screen.getByText("Estratégia")).toBeInTheDocument();expect(screen.getByText("Disponível")).toBeInTheDocument()});
  it("carrega carteira e preços fictícios identificados",async()=>{
    const responses=[
      {id:"session-1",name:"Demo",initial_capital:"10000.00000000",currency:"USDT",is_demo:true,created_at:"2026-01-01",session_token:"token"},
      {simulation_id:"session-1",available_balance:"10000.00000000",reserved_balance:"0.00000000",positions_value:"0.00000000",total_equity:"10000.00000000",realized_pnl:"0.00000000",unrealized_pnl:"0.00000000",currency:"USDT",positions:[],market_snapshot_id:"snapshot",demo_notice:"Dados fictícios.",updated_at:"2026-01-01"},
      {snapshot_id:"snapshot",source:"DEMO_FIXTURE",status:"READY",observed_at:"2026-01-01",valid_until:"2099-01-01",stale:false,using_fallback:false,error:null,quotes:[{symbol:"BTC/USDT",price:"50000.00000000",observed_at:"2026-01-01"},{symbol:"ETH/USDT",price:"3000.00000000",observed_at:"2026-01-01"}],demo_notice:"Cotações fixas e fictícias para desenvolvimento offline."},
      {count:0,limit:10,offset:0,results:[]},[],[],[],
    ];
    vi.spyOn(globalThis,"fetch").mockImplementation(async()=>new Response(JSON.stringify(responses.shift()),{status:200,headers:{"Content-Type":"application/json"}}));
    render(<App/>);
    fireEvent.click(screen.getByRole("button",{name:"Criar sessão demo"}));
    expect((await screen.findAllByText("BTC/USDT")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("ETH/USDT").length).toBeGreaterThan(0);
    expect(screen.getByText("Fonte: fixture fictícia")).toBeInTheDocument();
    expect(screen.getByText("Atualizado")).toBeInTheDocument();
  });
});
