import React, { useState } from "react";
import ParticipantView from "./ParticipantView";

export default function ParticipantJoin({onBack}){
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [joined, setJoined] = useState(false);

  const join = () => {
    if(!name || !code) return alert("Provide name and code");
    setJoined(true);
  };

  if(joined) return <ParticipantView name={name} code={code} onBack={onBack} />;
  return (
    <div className="container">
      <h2>Join Session</h2>
      <input placeholder="Your name" value={name} onChange={e=>setName(e.target.value)} />
      <input placeholder="Session code" value={code} onChange={e=>setCode(e.target.value)} />
      <button onClick={join}>Join</button>
      <button onClick={onBack}>Back</button>
    </div>
  );
}
