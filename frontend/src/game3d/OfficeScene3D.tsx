import { OrbitControls, OrthographicCamera } from "@react-three/drei";
import { Canvas, ThreeEvent } from "@react-three/fiber";
import { Suspense } from "react";
import type { Agent } from "./agents";

interface Props { agents:Agent[]; selectedAgent:Agent|null; onSelectAgent:(agent:Agent)=>void }
function Desk({x}:{x:number}) { return <group position={[x,0,-.8]}>
  <mesh position={[0,1.05,0]} castShadow receiveShadow><boxGeometry args={[2.7,.18,1.45]}/><meshStandardMaterial color="#7e6858" roughness={.85}/></mesh>
  {[-1.05,1.05].map(leg=><mesh key={leg} position={[leg,.5,0]} castShadow><boxGeometry args={[.14,1,1.05]}/><meshStandardMaterial color="#3c4655"/></mesh>)}
  <mesh position={[0,1.72,-.1]} castShadow><boxGeometry args={[1.15,.72,.12]}/><meshStandardMaterial color="#172438"/></mesh>
  <mesh position={[0,1.72,-.02]}><planeGeometry args={[.96,.53]}/><meshStandardMaterial color="#4fd7c8" emissive="#153f48"/></mesh>
  <mesh position={[0,1.32,-.1]} castShadow><boxGeometry args={[.1,.35,.1]}/><meshStandardMaterial color="#303b48"/></mesh>
</group> }
function Avatar({agent,selected,onSelect}:{agent:Agent;selected:boolean;onSelect:(agent:Agent)=>void}) {
  const select=(event:ThreeEvent<MouseEvent>)=>{event.stopPropagation();onSelect(agent)};
  const active=agent.status==="ANALYZING"||agent.status==="REVIEWING"||agent.status==="WAITING_APPROVAL";
  const stateColor=agent.status==="ERROR"?"#ff4d6d":agent.status==="COMPLETED"?"#60e6a8":"#7df9e7";
  return <group position={agent.position} onClick={select} onPointerEnter={()=>document.body.style.cursor="pointer"} onPointerLeave={()=>document.body.style.cursor="default"}>
    {(selected||active||agent.status==="ERROR"||agent.status==="COMPLETED")&&<mesh position={[0,.05,0]} rotation={[-Math.PI/2,0,0]}><ringGeometry args={[.65,.82,32]}/><meshBasicMaterial color={stateColor}/></mesh>}
    <mesh position={[0,1.42,0]} castShadow><sphereGeometry args={[.34,24,16]}/><meshStandardMaterial color="#f1c8a8" roughness={.75}/></mesh>
    <mesh position={[0,.82,0]} castShadow><capsuleGeometry args={[.38,.72,8,16]}/><meshStandardMaterial color={agent.color} roughness={.6}/></mesh>
  </group>;
}
function Office(props:Props) { return <>
  <color attach="background" args={["#101a29"]}/><ambientLight intensity={1.3}/>
  <directionalLight position={[7,12,8]} intensity={2.2} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024}/>
  <OrthographicCamera makeDefault position={[10,12,10]} zoom={45} near={.1} far={100}/>
  <OrbitControls makeDefault target={[0,.6,0]} enableRotate={false} enablePan={false} minZoom={34} maxZoom={70}/>
  <mesh position={[0,-.18,0]} receiveShadow><boxGeometry args={[13,.35,9]}/><meshStandardMaterial color="#314257" roughness={.95}/></mesh>
  <mesh position={[0,1,-4.35]} castShadow receiveShadow><boxGeometry args={[13,2.3,.3]}/><meshStandardMaterial color="#607389"/></mesh>
  <mesh position={[-6.35,1,0]} castShadow receiveShadow><boxGeometry args={[.3,2.3,9]}/><meshStandardMaterial color="#52677f"/></mesh>
  {[-4,0,4].map(x=><Desk key={x} x={x}/>)}
  {props.agents.map(agent=><Avatar key={agent.id} agent={agent} selected={props.selectedAgent?.id===agent.id} onSelect={props.onSelectAgent}/>) }
</> }
export function OfficeScene3D(props:Props) { return <Canvas shadows dpr={[1,1.5]} className="office-canvas" gl={{antialias:true}}><Suspense fallback={null}><Office {...props}/></Suspense></Canvas> }

