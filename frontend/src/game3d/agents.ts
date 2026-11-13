export type AgentStatus = "IDLE"|"ANALYZING"|"REVIEWING"|"WAITING_APPROVAL"|"COMPLETED"|"ERROR";
export interface Agent { id:"alex"|"maya"|"victor"; name:string; role:string; status:AgentStatus; color:string; position:[number,number,number] }
export const agents: Agent[] = [
  {id:"alex",name:"Alex",role:"Análise técnica",status:"IDLE",color:"#48a8ff",position:[-4,0,-2.2]},
  {id:"maya",name:"Maya",role:"Estratégia",status:"IDLE",color:"#bd72ff",position:[0,0,-2.2]},
  {id:"victor",name:"Victor",role:"Risco determinístico",status:"IDLE",color:"#ff9766",position:[4,0,-2.2]},
];

