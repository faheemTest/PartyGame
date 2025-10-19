import React, { useState } from "react";
import HostDashboard from "./pages/HostDashboard";
import ParticipantJoin from "./pages/ParticipantJoin";

export default function App(){
  const [role, setRole] = useState(null);

  if(!role){
    return (
      <div className="container">
        <h1>PartyGame</h1>
        <div className="card">
          <button onClick={()=>setRole("host")}>Host (create session)</button>
          <button onClick={()=>setRole("participant")}>Join as Participant</button>
        </div>
      </div>
    );
  }

  if(role === "host"){
    return <HostDashboard onBack={()=>setRole(null)} />;
  }

  return <ParticipantJoin onBack={()=>setRole(null)} />;
}
