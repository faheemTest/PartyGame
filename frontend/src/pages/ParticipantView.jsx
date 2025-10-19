import React, { useEffect, useState } from "react";
import { io } from "socket.io-client";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const socket = io(API, { transports: ['websocket','polling'] });

export default function ParticipantView({ name, code, onBack }){
  const [connected, setConnected] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [poll, setPoll] = useState(null);
  const [qna, setQna] = useState([]);

  useEffect(()=>{
    socket.on("connect", ()=> setConnected(true));
    socket.on("disconnect", ()=> setConnected(false));

    socket.emit("participant:join", { name, code });

    socket.on("question:push", q => setCurrentQuestion(q));
    socket.on("question:timer", t => console.log("timer", t));
    socket.on("leaderboard:update", data => setLeaderboard(data));
    socket.on("question:results", res => console.log("results", res));
    socket.on("poll:push", p => setPoll(p));
    socket.on("poll:results", r => setPoll(prev=> ({...prev, results: r.counts})));
    socket.on("qna:update", items => setQna(items));

    return ()=> {
      socket.off("connect"); socket.off("disconnect");
      socket.off("question:push"); socket.off("leaderboard:update"); socket.off("poll:push");
    };
  }, []);

  const answer = (answer) => {
    socket.emit("participant:answer", { code, name, answer, qid: currentQuestion?.id });
    setCurrentQuestion(null);
  };

  const vote = (choice) => {
    socket.emit("participant:vote", { poll_id: poll.id, choice });
  };

  const postQ = () => {
    const text = prompt("Enter your question:");
    if(!text) return;
    socket.emit("participant:post-qna", { text, name, code });
  };

  return (
    <div className="container">
      <button onClick={onBack}>Leave</button>
      <h3>Participant: {name} (code: {code})</h3>
      <div>Connected: {connected ? "yes" : "no"}</div>
      {currentQuestion ? (
        <div className="card">
          <h4>{currentQuestion.text}</h4>
          {currentQuestion.options?.length ? (
            currentQuestion.options.map((opt, idx)=>
              <button key={idx} onClick={()=>answer(opt)}>{opt}</button>
            )
          ):(
            <div>
              <input id="textans" placeholder="Your answer"/>
              <button onClick={()=>answer(document.getElementById("textans").value)}>Send</button>
            </div>
          )}
        </div>
      ): <div>No active question</div>}
      {poll ? (
        <div className="card">
          <h4>Poll: {poll.text}</h4>
          {poll.options.map((o, i)=><button key={i} onClick={()=>vote(o)}>{o}</button>)}
          <div>Results: {JSON.stringify(poll.results)}</div>
        </div>
      ): null}
      <div className="card">
        <h4>Leaderboard</h4>
        <ol>
          {leaderboard.map(p => <li key={p.name}>{p.name} — {p.score}</li>)}
        </ol>
      </div>
      <div className="card">
        <h4>Q&A</h4>
        <button onClick={postQ}>Post a question</button>
        <ol>
          {qna.map(item => <li key={item.id}>{item.text} — {item.upvotes} upvotes</li>)}
        </ol>
      </div>
    </div>
  );
}
