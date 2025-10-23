import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .db import db
from .utils import gen_code
from .export_utils import export_csv
import socketio
import datetime
from dotenv import load_dotenv

load_dotenv()

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# In-memory session state (for realtime): session_code -> {host_sid, participants: {sid: {name, score, id}}, current_question}
SESSION_STATE = {}

@app.get("/")
async def root():
    return {"msg": "PartyGame backend running"}

@app.post("/api/session/create")
async def api_create_session(payload: dict):
    host = payload.get("host", "Host")
    code = gen_code()
    session = {"code": code, "host": host, "questions": [], "polls": [], "qna": [], "participants": [], "results": [], "created_at": datetime.datetime.utcnow()}
    await db.sessions.insert_one(session)
    # init in-memory
    SESSION_STATE[code] = {"host_sid": None, "participants": {}, "current": None}
    return {"code": code}

@app.get("/api/session/{code}/export/results")
async def api_export_results(code: str):
    s = await db.sessions.find_one({"code": code})
    if not s:
        return {"error": "session not found"}
    rows = []
    for p in s.get("participants", []):
        rows.append({"name": p.get("name"), "score": p.get("score", 0)})
    return export_csv(rows, columns=["name", "score"], filename=f"{code}-results.csv")

# Add this import near top if not present
from fastapi import HTTPException

# REST endpoint to create/start a question for a session (also emits to participants)
@app.post("/api/session/{code}/question")
async def api_create_question(code: str, payload: dict):
    """
    Body example:
    {
      "text": "What is 2+2?",
      "type": "single",            # "single" | "multi" | "text"
      "options": ["3","4","5"],    # optional for text type
      "time_limit": 20,
      "points": 100,
      "correct": "4"               # optional, used for scoring
    }
    """
    s = await db.sessions.find_one({"code": code})
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    # create question doc
    question = dict(payload)
    question["id"] = question.get("id") or gen_code(8)
    import datetime
    question["created_at"] = datetime.datetime.utcnow()

    # Save to DB
    await db.sessions.update_one({"code": code}, {"$push": {"questions": question}})

    # ensure in-memory session state exists
    if code not in SESSION_STATE:
        SESSION_STATE[code] = {"host_sid": None, "participants": {}, "current": None}

    # set current question in memory and reset answers
    SESSION_STATE[code]["current"] = {"type": "question", "payload": question, "answers": {}}

    # broadcast to room
    await sio.emit("question:push", question, room=code)
    await sio.emit("question:timer", {"time": int(question.get("time_limit", 20))}, room=code)

    # Return created question
    return {"status": "ok", "question": question}


# Socket.IO events
@sio.event
async def connect(sid, environ):
    print("connect", sid)

@sio.event
async def disconnect(sid):
    print("disconnect", sid)
    # remove participant if present
    for code, state in list(SESSION_STATE.items()):
        for psid in list(state["participants"].keys()):
            if psid == sid:
                user = state["participants"].pop(psid)
                # update DB participants list
                await db.sessions.update_one({"code": code}, {"$pull": {"participants": {"id": user.get('id')}}})
                # notify host and others
                await sio.emit("participants:update", list(state["participants"].values()), room=code)
        if state.get("host_sid") == sid:
            state["host_sid"] = None

@sio.on("host:join")
async def host_join(sid, data):
    code = data.get("code")
    name = data.get("name", "Host")
    # attach host to session
    if code not in SESSION_STATE:
        # try to load from DB
        s = await db.sessions.find_one({"code": code})
        if not s:
            await sio.emit("error", {"msg":"session not found"}, to=sid)
            return
        SESSION_STATE[code] = {"host_sid": sid, "participants": {}, "current": None}
    else:
        SESSION_STATE[code]["host_sid"] = sid
    await sio.save_session(sid, {"code": code, "role": "host"})
    await sio.enter_room(sid, code)
    await sio.emit("host:joined", {"code": code}, to=sid)

@sio.on("participant:join")
async def participant_join(sid, data):
    code = data.get("code")
    name = data.get("name", "Player")
    if code not in SESSION_STATE:
        # try to load/create from DB
        s = await db.sessions.find_one({"code": code})
        if not s:
            await sio.emit("error", {"msg":"session not found"}, to=sid)
            return
        SESSION_STATE[code] = {"host_sid": None, "participants": {}, "current": None}
    # register participant in-memory
    participant = {"id": sid, "name": name, "score": 0}
    SESSION_STATE[code]["participants"][sid] = participant
    # persist participant in DB (if not exists)
    await db.sessions.update_one({"code": code}, {"$addToSet": {"participants": participant}})
    await sio.save_session(sid, {"code": code, "role": "participant", "name": name})
    await sio.enter_room(sid, code)
    # notify room
    await sio.emit("participants:update", list(SESSION_STATE[code]["participants"].values()), room=code)

@sio.on("host:start-question")
async def host_start_question(sid, data):
    code = data.get("code")
    question = data.get("question")
    # question should have: id (optional), text, type (single/multi/text), options (list), time_limit (sec), points
    if code not in SESSION_STATE:
        await sio.emit("error", {"msg":"session not found"}, to=sid)
        return
    # store in DB's questions
    question = dict(question)
    question["id"] = question.get("id") or gen_code(8)
    question["created_at"] = datetime.datetime.utcnow()
    await db.sessions.update_one({"code": code}, {"$push": {"questions": question}})
    # set current
    SESSION_STATE[code]["current"] = {"type": "question", "payload": question, "answers": {}}
    # broadcast question to room
    await sio.emit("question:push", question, room=code)
    # start timer
    time_limit = int(question.get("time_limit", 20))
    await sio.emit("question:timer", {"time": time_limit}, room=code)
    # wait for time_limit seconds
    await asyncio.sleep(time_limit)
    # compute results
    state = SESSION_STATE.get(code)
    if not state:
        return
    answers = state["current"].get("answers", {})
    correct = question.get("correct")  # optional field with correct answer(s)
    results = []
    # scoring: if correct provided, award points for correct answers
    for sid_p, ans in answers.items():
        p = state["participants"].get(sid_p)
        points_awarded = 0
        if correct is not None:
            qtype = question.get("type", "single")
            try:
                if qtype == "text":
                    if str(ans).strip().lower() == str(correct).strip().lower():
                        points_awarded = int(question.get("points",100))
                elif qtype == "single":
                    if ans == correct:
                        points_awarded = int(question.get("points",100))
                elif qtype == "multi":
                    # require sets equal
                    if set(ans) == set(correct):
                        points_awarded = int(question.get("points",100))
            except Exception:
                points_awarded = 0
        # update participant score in-memory and DB
        if p:
            p["score"] = p.get("score",0) + points_awarded
            await db.sessions.update_one({"code": code, "participants.id": p["id"]}, {"$set": {"participants.$.score": p["score"]}})
            results.append({"name": p["name"], "score": p["score"], "awarded": points_awarded})
    # clear current
    SESSION_STATE[code]["current"] = None
    # broadcast leaderboard and results
    leaderboard = sorted([{"name": x["name"], "score": x["score"]} for x in SESSION_STATE[code]["participants"].values()], key=lambda r: -r["score"])
    await sio.emit("leaderboard:update", leaderboard, room=code)
    await sio.emit("question:results", {"results": results}, room=code)

@sio.on("participant:answer")
async def participant_answer(sid, data):
    session = await sio.get_session(sid)
    code = session.get("code")
    answer = data.get("answer")
    qid = data.get("qid")
    if not code or code not in SESSION_STATE:
        await sio.emit("error", {"msg":"session not found"}, to=sid)
        return
    state = SESSION_STATE[code]
    # record answer
    if state.get("current") and state["current"]["payload"]["id"] == qid:
        state["current"]["answers"][sid] = answer
    # optional: emit ack
    await sio.emit("answer:ack", {"qid": qid}, to=sid)

@sio.on("host:start-poll")
async def host_start_poll(sid, data):
    code = data.get("code")
    poll = data.get("poll")
    if code not in SESSION_STATE:
        await sio.emit("error", {"msg":"session not found"}, to=sid)
        return
    poll = dict(poll)
    poll["id"] = poll.get("id") or gen_code(8)
    poll["created_at"] = datetime.datetime.utcnow()
    poll["votes"] = {}
    await db.sessions.update_one({"code": code}, {"$push": {"polls": poll}})
    SESSION_STATE[code]["current"] = {"type": "poll", "payload": poll}
    await sio.emit("poll:push", poll, room=code)

@sio.on("participant:vote")
async def participant_vote(sid, data):
    session = await sio.get_session(sid)
    code = session.get("code")
    poll_id = data.get("poll_id")
    choice = data.get("choice")
    if not code or code not in SESSION_STATE:
        await sio.emit("error", {"msg":"session not found"}, to=sid)
        return
    state = SESSION_STATE[code]
    cur = state.get("current")
    if not cur or cur.get("type") != "poll" or cur["payload"]["id"] != poll_id:
        await sio.emit("error", {"msg":"poll not active"}, to=sid)
        return
    # record vote
    cur["payload"].setdefault("votes", {})
    cur["payload"]["votes"][sid] = choice
    # compute aggregated results
    counts = {}
    for v in cur["payload"]["votes"].values():
        counts[v] = counts.get(v, 0) + 1
    await sio.emit("poll:results", {"counts": counts}, room=code)

@sio.on("participant:post-qna")
async def participant_post_qna(sid, data):
    session = await sio.get_session(sid)
    code = session.get("code")
    text = data.get("text")
    if not code or code not in SESSION_STATE:
        await sio.emit("error", {"msg":"session not found"}, to=sid)
        return
    item = {"id": gen_code(8), "text": text, "upvotes": 0, "author": data.get("name")}
    await db.sessions.update_one({"code": code}, {"$push": {"qna": item}})
    # broadcast updated qna
    s = await db.sessions.find_one({"code": code})
    await sio.emit("qna:update", s.get("qna", []), room=code)

@sio.on("participant:upvote-qna")
async def participant_upvote_qna(sid, data):
    session = await sio.get_session(sid)
    code = session.get("code")
    qid = data.get("qna_id")
    await db.sessions.update_one({"code": code, "qna.id": qid}, {"$inc": {"qna.$.upvotes": 1}})
    s = await db.sessions.find_one({"code": code})
    await sio.emit("qna:update", s.get("qna", []), room=code)

# to run with uvicorn: uvicorn app.main:sio_app --host 0.0.0.0 --port 8000
