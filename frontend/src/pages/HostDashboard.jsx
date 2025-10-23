import React, { useEffect, useState } from "react";
import { io } from "socket.io-client";
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const socket = io(API, { transports: ['websocket','polling'] });

export default function HostDashboard({onBack}){
  const [code, setCode] = useState("");
  const [created, setCreated] = useState(false);
  const [name, setName] = useState("Host");
  const [questionText, setQuestionText] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [participants, setParticipants] = useState([]);

  useEffect(()=>{
    socket.on("connect", ()=> console.log("host socket connected"));
    socket.on("host:joined", d => setCode(d.code));
    socket.on("participants:update", data => setParticipants(data));
    socket.on("leaderboard:update", lb => console.log("LB", lb));
    socket.on("qna:update", q => console.log("qna", q));
  }, []);

  const createSession = async () => {
    const res = await fetch((import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/session/create", { method: "POST", headers: {'Content-Type':'application/json'}, body: JSON.stringify({host: name})});
    const j = await res.json();
    setCode(j.code);
    setCreated(true);
    // join as host socket room
    socket.emit("host:join", { code: j.code, name });
  };

 const pushQuestion = async () => {
  const options = optionsText.split("|").map(s=>s.trim()).filter(Boolean);
  const q = { text: questionText, type: options.length ? "single" : "text", options, time_limit: 20, points: 100, correct: null };
  // call backend REST endpoint
  const api = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const resp = await fetch(`${api}/api/session/${code}/question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(q)
  });
  const data = await resp.json();
  if (!resp.ok) {
    alert("Failed to create question: " + (data.detail || JSON.stringify(data)));
    return;
  }
  // Optionally reset UI fields
  setQuestionText("");
  setOptionsText("");
};


  const startPoll = () => {
    const options = optionsText.split("|").map(s=>s.trim()).filter(Boolean);
    const poll = { text: questionText, options };
    socket.emit("host:start-poll", { code, poll });
  };

  return (
    <div className="container">
      <button onClick={onBack}>Back</button>
      <h2>Host Dashboard</h2>
      {!created ? (
        <>
          <input value={name} onChange={e=>setName(e.target.value)} />
          <button onClick={createSession}>Create Session</button>
        </>
      ): (
        <>
          <div>Session Code: <strong>{code}</strong></div>
          <div className="card">
            <h4>Push Question</h4>
            <input placeholder="Question text" value={questionText} onChange={e=>setQuestionText(e.target.value)} />
            <input placeholder="Options (pipe `|` separated) — leave empty for text answer" value={optionsText} onChange={e=>setOptionsText(e.target.value)} />
            <button onClick={pushQuestion}>Start Question</button>
            <button onClick={startPoll}>Start Poll</button>
          </div>
          <div className="card">
            <h4>Participants</h4>
            <ol>
              {participants.map(p => <li key={p.id}>{p.name} — {p.score}</li>)}
            </ol>
          </div>
          <div className="card">
            <h4>Export</h4>
            <a href={(import.meta.env.VITE_API_URL || "http://localhost:8000") + "/api/session/" + code + "/export/results"} target="_blank" rel="noreferrer">Export Results CSV</a>
          </div>
        </>
      )}
    </div>
  );
}
