from flask import Flask, send_from_directory, jsonify
import sqlite3
import os

DB_PATH = "/Users/hasib/htm_ledger.db"
PHOTO_DIR = os.path.expanduser("~/htm_photos")

ALL_RECIPIENTS = ["Shanto", "Tonmoy", "Kabir", "Puja", "Hasib"]
ALL_DENOMINATIONS = [1000, 500, 200, 100]

app = Flask(__name__)

def get_raw_state():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM current_state WHERE id = 1")
    state = dict(cur.fetchone())
    cur.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 4")
    history = [dict(r) for r in cur.fetchall()]
    conn.close()
    return state, history

@app.route("/photos/<filename>")
def photos(filename):
    return send_from_directory(PHOTO_DIR, filename)

@app.route("/api/state")
def api_state():
    state, history = get_raw_state()
    locked = state["session_status"] == "locked"
    payload = {
        "locked": locked,
        "all_recipients": ALL_RECIPIENTS,
        "all_denominations": ALL_DENOMINATIONS,
        "banner_text": state["banner_text"],
        "banner_type": state["banner_type"],
        "banner_timestamp": state["banner_timestamp"],
    }
    if locked:
        payload.update({"recipient": "", "amount": 0, "balance": None, "tokens": [],
                        "hold_active": False, "hold_percent": 0,
                        "idle_warning_active": False, "idle_seconds_left": 0, "history": []})
    else:
        tokens = [int(t) for t in state["current_tokens"].split(",") if t]
        payload.update({"recipient": state["selected_recipient"], "amount": state["current_amount"],
                        "balance": state["current_balance"], "tokens": tokens,
                        "hold_active": bool(state["hold_active"]), "hold_percent": state["hold_percent"],
                        "idle_warning_active": bool(state["idle_warning_active"]),
                        "idle_seconds_left": state["idle_seconds_left"], "history": history})
    return jsonify(payload)

@app.route("/")
def index():
    return PAGE

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>HTM — Live</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0B161D; --bg2:#10222D; --panel:#132A37; --panel2:#0F212B; --line:#1F3A48;
  --ink:#F3F6F8; --muted:#8FA6AF; --dim:#5C7683;
  --navy:#1B3A4B; --copper:#C97B3D; --copper2:#E8A05A; --teal:#2ED3A6; --teal2:#2A9D8F;
  --red:#E23B2E; --amber:#F5A623; --yellow:#F2C230; --yellow2:#D9A81C; --pink:#E8608A; --green:#3DDC84;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:Inter,-apple-system,system-ui,sans-serif;background:
  radial-gradient(1200px 700px at 50% 42%, #16303E 0%, var(--bg) 60%);
  color:var(--ink);overflow:hidden;padding:22px 30px 18px;display:flex;flex-direction:column;gap:14px}
.hidden{display:none!important}

/* ---------- header ---------- */
header{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:20px}
.brand h1{font-family:Fraunces,Georgia,serif;font-size:30px;color:var(--copper2);letter-spacing:.2px;line-height:1}
.brand .sub{color:var(--muted);font-size:12.5px;margin-top:5px;letter-spacing:.3px}
.status-pill{justify-self:end;display:flex;align-items:center;gap:10px;background:var(--panel);
  border:1px solid var(--line);border-radius:999px;padding:8px 14px 8px 10px}
.status-pill .dot{width:10px;height:10px;border-radius:50%;background:var(--red);box-shadow:0 0 12px var(--red)}
.status-pill.on .dot{background:var(--teal);box-shadow:0 0 12px var(--teal)}
.status-pill span{font-size:12.5px;font-weight:600;letter-spacing:.6px;text-transform:uppercase;color:var(--muted)}
.status-pill.on span{color:var(--ink)}

/* stepper */
.stepper{display:flex;align-items:center;gap:0;justify-self:center}
.step{display:flex;align-items:center;gap:9px}
.step .n{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:12.5px;font-weight:700;
  background:var(--panel);border:1.5px solid var(--line);color:var(--dim);transition:all .3s}
.step .t{font-size:12.5px;font-weight:600;color:var(--dim);letter-spacing:.3px;transition:color .3s}
.step.done .n{background:var(--teal2);border-color:var(--teal2);color:#fff}
.step.done .t{color:var(--muted)}
.step.active .n{background:var(--copper);border-color:var(--copper2);color:#fff;box-shadow:0 0 0 6px rgba(201,123,61,.18)}
.step.active .t{color:var(--ink)}
.step-line{width:34px;height:2px;background:var(--line);margin:0 12px;transition:background .3s}
.step-line.done{background:var(--teal2)}

/* account chip */
.account{display:flex;align-items:center;gap:12px;background:var(--panel);border:1px solid var(--line);
  border-radius:16px;padding:8px 16px 8px 8px;justify-self:end}
.account img{width:48px;height:48px;border-radius:12px;object-fit:cover;border:2px solid #24414F}
.account .name{font-size:14px;font-weight:700}
.account .bal-l{font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim);margin-top:2px}
.account .bal{font-size:20px;font-weight:800;color:var(--teal);font-variant-numeric:tabular-nums;line-height:1.05}

/* ---------- main grid ---------- */
.main{flex:1;display:grid;grid-template-columns:1.05fr 1.3fr 1.05fr;gap:18px;min-height:0}
.panel{background:linear-gradient(180deg,var(--panel) 0%,var(--panel2) 100%);border:1px solid var(--line);
  border-radius:22px;padding:22px 24px;display:flex;flex-direction:column;min-height:0;position:relative;overflow:hidden}
.panel .lbl{font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:var(--dim);font-weight:700}

/* recipient panel */
.recip-hero{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center}
.recip-hero .ph{width:170px;height:170px;border-radius:26px;object-fit:cover;border:4px solid var(--teal);
  box-shadow:0 0 0 8px rgba(46,211,166,.14),0 18px 40px rgba(0,0,0,.45)}
.recip-hero .nm{font-family:Fraunces,Georgia,serif;font-size:34px;font-weight:700;color:var(--ink);line-height:1}
.recip-hero .to{font-size:12px;text-transform:uppercase;letter-spacing:1.4px;color:var(--teal);font-weight:700}
.recip-empty{width:170px;height:170px;border-radius:26px;border:2px dashed #2C4A5A;display:grid;place-items:center;color:var(--dim)}
.recip-empty svg{width:64px;height:64px;opacity:.5}
.recip-hero .hint{color:var(--muted);font-size:13.5px;max-width:240px;line-height:1.45}
.gallery{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:6px}
.g-item{width:64px;text-align:center;padding:6px 4px;border-radius:12px;border:2px solid transparent;opacity:.55;transition:all .25s}
.g-item img{width:44px;height:44px;border-radius:10px;object-fit:cover;border:1.5px solid #2C4A5A}
.g-item .gn{font-size:10.5px;font-weight:600;margin-top:4px;color:var(--muted)}
.g-item.active{opacity:1;border-color:var(--teal);background:rgba(46,211,166,.08)}
.g-item.active .gn{color:var(--teal)}

/* device twin panel */
.device{align-items:center;justify-content:center;gap:10px}
.ring-wrap{position:relative;width:min(38vh,360px);aspect-ratio:1;display:grid;place-items:center}
.ring-wrap svg{position:absolute;inset:0;width:100%;height:100%}
.seg{fill:#213541;transition:fill .12s,filter .12s}
.seg.lit{fill:var(--teal);filter:drop-shadow(0 0 7px rgba(46,211,166,.9))}
.seg.red{fill:var(--red);filter:drop-shadow(0 0 8px rgba(226,59,46,.9))}
.seg.amber{fill:var(--amber);filter:drop-shadow(0 0 8px rgba(245,166,35,.9))}
.seg.soft{fill:var(--teal2);filter:drop-shadow(0 0 5px rgba(42,157,143,.7))}
svg.warning .seg{animation:redstrobe .4s steps(1,end) infinite}
@keyframes redstrobe{0%{fill:var(--red);filter:drop-shadow(0 0 10px rgba(226,59,46,1))}50%{fill:#2B1A1C;filter:none}}
.ybtn{position:relative;width:52%;aspect-ratio:1;border-radius:50%;
  background:radial-gradient(circle at 35% 30%,#FFE27A 0%,var(--yellow) 45%,var(--yellow2) 100%);
  box-shadow:0 10px 0 #A9811A,0 22px 40px rgba(0,0,0,.5),inset 0 -6px 12px rgba(0,0,0,.12);
  display:grid;place-items:center;transition:transform .12s,box-shadow .12s;opacity:.55;filter:saturate(.6)}
.ybtn.ready{opacity:1;filter:none;animation:breathe 1.6s ease-in-out infinite}
.ybtn.holding{opacity:1;filter:none;transform:translateY(7px) scale(.97);box-shadow:0 3px 0 #A9811A,0 10px 18px rgba(0,0,0,.5),inset 0 -3px 8px rgba(0,0,0,.18)}
.ybtn.done{opacity:1;filter:none;background:radial-gradient(circle at 35% 30%,#8FF7CF 0%,var(--teal) 50%,var(--teal2) 100%);box-shadow:0 10px 0 #1D7A67,0 22px 40px rgba(0,0,0,.5)}
@keyframes breathe{0%,100%{transform:scale(1);box-shadow:0 10px 0 #A9811A,0 22px 40px rgba(0,0,0,.5),0 0 0 0 rgba(242,194,48,.55)}
  50%{transform:scale(1.04);box-shadow:0 10px 0 #A9811A,0 22px 40px rgba(0,0,0,.5),0 0 0 26px rgba(242,194,48,0)}}
.ybtn .pct{font-size:44px;font-weight:800;color:#3A2E05;font-variant-numeric:tabular-nums;letter-spacing:-1px}
.ybtn .pct small{display:block;font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#6B5310;font-weight:700}
.ybtn .hand{width:52px;height:52px;fill:#3A2E05;opacity:.85}
.instr{text-align:center;min-height:52px}
.instr .big{font-size:19px;font-weight:700;color:var(--ink)}
.instr .small{font-size:12.5px;color:var(--muted);margin-top:4px}
.controls{display:flex;gap:26px;align-items:center;margin-top:4px}
.ctl{display:flex;flex-direction:column;align-items:center;gap:6px}
.ctl .k{width:22px;height:22px;border-radius:50%;transition:box-shadow .15s,transform .15s}
.ctl .k.green{background:#2FBF6A}
.ctl .k.pink{background:var(--pink)}
.ctl .k.pulse{transform:scale(1.25);box-shadow:0 0 0 10px rgba(255,255,255,.08),0 0 18px currentColor}
.ctl .kl{font-size:10.5px;letter-spacing:.8px;text-transform:uppercase;color:var(--dim);font-weight:700}

/* amount panel */
.amt-big{font-size:64px;font-weight:800;color:var(--ink);letter-spacing:-2px;line-height:1;margin-top:8px;font-variant-numeric:tabular-nums}
.amt-big .cur{font-size:26px;color:var(--copper2);font-weight:700;letter-spacing:0;margin-right:6px}
.amt-sub{color:var(--muted);font-size:12.5px;margin-top:6px}
.stack{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px;min-height:78px;align-content:flex-start}
.chip{width:64px;text-align:center}
.chip img{width:64px;height:64px;border-radius:12px;object-fit:cover;border:2px solid #2C4A5A;box-shadow:0 8px 18px rgba(0,0,0,.35)}
.chip .cl{font-size:10.5px;color:var(--muted);margin-top:4px;font-weight:600}
.chip.pop{animation:popIn .32s cubic-bezier(.2,1.2,.4,1)}
@keyframes popIn{from{transform:scale(.5) translateY(10px);opacity:0}to{transform:scale(1) translateY(0);opacity:1}}
.legend{margin-top:auto;padding-top:14px;border-top:1px solid var(--line)}
.legend .row{display:flex;gap:10px;margin-top:8px}
.legend .d{flex:1;text-align:center;opacity:.8}
.legend .d img{width:100%;aspect-ratio:1;max-width:58px;border-radius:9px;object-fit:cover;border:1.5px solid #2C4A5A}
.legend .d span{display:block;font-size:10.5px;color:var(--muted);margin-top:4px;font-weight:600}

/* footer log */
.log{display:flex;gap:18px;align-items:center;background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:9px 16px;min-height:42px}
.log .lbl{font-size:10.5px;text-transform:uppercase;letter-spacing:1px;color:var(--dim);font-weight:700;white-space:nowrap}
.log .items{display:flex;gap:22px;overflow:hidden}
.log .it{font-size:12.5px;color:var(--muted);white-space:nowrap}
.log .it b{color:var(--copper2)}
.log .it em{color:var(--dim);font-style:normal;margin-right:6px}

/* locked attract screen */
.locked{flex:1;display:grid;place-items:center}
.lock-card{text-align:center;display:flex;flex-direction:column;align-items:center;gap:18px}
.keyring{width:200px;height:200px;border-radius:50%;display:grid;place-items:center;position:relative}
.keyring::before,.keyring::after{content:"";position:absolute;inset:0;border-radius:50%;border:2px solid rgba(201,123,61,.55);animation:ripple 2.4s ease-out infinite}
.keyring::after{animation-delay:1.2s}
@keyframes ripple{from{transform:scale(.6);opacity:.9}to{transform:scale(1.35);opacity:0}}
.keyring svg{width:96px;height:96px;fill:none;stroke:var(--copper2);stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.lock-card h2{font-family:Fraunces,Georgia,serif;font-size:40px;font-weight:700}
.lock-card p{color:var(--muted);font-size:15px}
.lock-card .zone{display:inline-flex;align-items:center;gap:10px;background:rgba(47,191,106,.12);border:1px solid rgba(47,191,106,.4);color:#7FE3A6;
  padding:8px 14px;border-radius:999px;font-size:13px;font-weight:600}
.lock-card .zone i{width:10px;height:10px;border-radius:50%;background:#2FBF6A;box-shadow:0 0 12px #2FBF6A;display:inline-block}
.lock-card.shake{animation:shake .45s}
@keyframes shake{0%,100%{transform:translateX(0)}20%{transform:translateX(-10px)}40%{transform:translateX(10px)}60%{transform:translateX(-7px)}80%{transform:translateX(7px)}}

/* toasts */
#toasts{position:fixed;top:18px;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;gap:8px;z-index:50;pointer-events:none}
.toast{display:flex;align-items:center;gap:12px;padding:12px 18px;border-radius:14px;font-weight:700;font-size:14.5px;
  box-shadow:0 14px 40px rgba(0,0,0,.5);animation:slideDown .28s cubic-bezier(.2,1,.3,1);min-width:320px;backdrop-filter:blur(8px)}
.toast .ic{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:14px;flex-shrink:0}
.toast.success{background:rgba(29,122,103,.92);color:#E8FFF6}.toast.success .ic{background:var(--teal);color:#0B2A22}
.toast.error{background:rgba(180,72,47,.94);color:#FFEDE8}.toast.error .ic{background:#FFB4A8;color:#5A180E}
.toast.warning{background:rgba(201,123,61,.94);color:#FFF4E6}.toast.warning .ic{background:#FFD9A8;color:#5A3308}
.toast.info{background:rgba(27,58,75,.94);color:#E8F1F6}.toast.info .ic{background:#9FC3D4;color:#0E2430}
.toast.out{animation:fadeUp .3s forwards}
@keyframes slideDown{from{transform:translateY(-24px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes fadeUp{to{transform:translateY(-16px);opacity:0}}

/* idle overlay */
#idle{position:fixed;inset:0;z-index:40;display:grid;place-items:center;background:rgba(11,22,29,.55);backdrop-filter:blur(3px)}
#idle .box{text-align:center;border:3px solid var(--red);border-radius:28px;padding:34px 60px;background:rgba(40,12,10,.85);
  box-shadow:0 0 0 12px rgba(226,59,46,.12),0 30px 80px rgba(0,0,0,.6);animation:alarm .8s ease-in-out infinite}
@keyframes alarm{0%,100%{box-shadow:0 0 0 12px rgba(226,59,46,.12),0 30px 80px rgba(0,0,0,.6)}50%{box-shadow:0 0 0 26px rgba(226,59,46,.28),0 30px 80px rgba(0,0,0,.6)}}
#idle .cap{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:#FFB4A8;font-weight:800}
#idle .num{font-size:120px;font-weight:800;line-height:1;color:#fff;font-variant-numeric:tabular-nums;margin:6px 0}
#idle .msg{font-size:16px;color:#FFD9D3}

/* success overlay */
#success{position:fixed;inset:0;z-index:45;display:grid;place-items:center;background:rgba(11,22,29,.7);backdrop-filter:blur(4px)}
#success .box{text-align:center;display:flex;flex-direction:column;align-items:center;gap:14px;animation:popIn .4s cubic-bezier(.2,1.2,.4,1)}
#success .chk{width:130px;height:130px;border-radius:50%;background:var(--teal);display:grid;place-items:center;box-shadow:0 0 0 16px rgba(46,211,166,.18),0 24px 60px rgba(0,0,0,.5)}
#success .chk svg{width:70px;height:70px;fill:none;stroke:#062A20;stroke-width:8;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:60;stroke-dashoffset:60;animation:draw .5s .15s forwards}
@keyframes draw{to{stroke-dashoffset:0}}
#success h2{font-family:Fraunces,Georgia,serif;font-size:42px}
#success p{font-size:18px;color:var(--muted)}
#success p b{color:var(--ink)}
</style></head>
<body>

<div id="toasts"></div>

<header>
  <div class="brand"><h1>HTM</h1><div class="sub">Home Teller Machine · live mirror of the physical prototype</div></div>
  <div class="stepper" id="stepper">
    <div class="step" data-i="0"><div class="n">1</div><div class="t">Unlock</div></div><div class="step-line"></div>
    <div class="step" data-i="1"><div class="n">2</div><div class="t">Recipient</div></div><div class="step-line"></div>
    <div class="step" data-i="2"><div class="n">3</div><div class="t">Amount</div></div><div class="step-line"></div>
    <div class="step" data-i="3"><div class="n">4</div><div class="t">Confirm</div></div>
  </div>
  <div id="hdrRight" style="justify-self:end;display:flex;gap:12px;align-items:center">
    <div class="account hidden" id="account">
      <img src="/photos/account_holder.jpg">
      <div><div class="name">Fatema Begum</div><div class="bal-l">Balance</div><div class="bal" id="bal">৳ 0</div></div>
    </div>
    <div class="status-pill" id="pill"><div class="dot"></div><span id="pillTxt">Locked</span></div>
  </div>
</header>

<!-- LOCKED -->
<section class="locked hidden" id="lockedView">
  <div class="lock-card" id="lockCard">
    <div class="keyring"><svg viewBox="0 0 48 48"><circle cx="17" cy="17" r="9"/><path d="M23.5 23.5 40 40M34 34l4-4M30 30l4-4"/></svg></div>
    <h2>Tap your keyfob to begin</h2>
    <p>The device is locked. Nothing responds until the key is presented.</p>
    <div class="zone"><i></i>Green tap zone is waiting</div>
  </div>
</section>

<!-- UNLOCKED -->
<section class="main hidden" id="mainView">
  <div class="panel">
    <div class="lbl">Sending to</div>
    <div class="recip-hero" id="recipHero">
      <div class="recip-empty" id="recipEmpty"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5Z"/></svg></div>
      <img class="ph hidden" id="recipPhoto" src="">
      <div class="to hidden" id="recipTo">Selected recipient</div>
      <div class="nm" id="recipName" style="color:var(--dim);font-size:22px">No recipient yet</div>
      <div class="hint" id="recipHint">Tap one of the photo cards on the green zone</div>
    </div>
    <div class="lbl" style="margin-top:8px">Registered recipients</div>
    <div class="gallery" id="gallery"></div>
  </div>

  <div class="panel device">
    <div class="lbl" style="align-self:flex-start">Confirm control · 12-LED ring</div>
    <div class="ring-wrap">
      <svg id="ringSvg" viewBox="0 0 400 400"></svg>
      <div class="ybtn" id="ybtn">
        <div class="pct hidden" id="pct">0%<small>holding</small></div>
        <svg class="hand" id="hand" viewBox="0 0 24 24"><path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V11h1V4.5a1.5 1.5 0 0 1 3 0V11h1V6.5a1.5 1.5 0 0 1 3 0V14c0 3.9-3.1 7-7 7h-1.2c-1.9 0-3.6-.9-4.7-2.5L3.6 14a1.5 1.5 0 0 1 2.5-1.6L8 14.5V8.5a1.5 1.5 0 0 1 3 0V11H9Z"/></svg>
      </div>
    </div>
    <div class="instr"><div class="big" id="instrBig">—</div><div class="small" id="instrSmall"></div></div>
    <div class="controls">
      <div class="ctl"><div class="k green" id="kGreen"></div><div class="kl">Tap zone</div></div>
      <div class="ctl"><div class="k pink" id="kPink"></div><div class="kl">Balance · Cancel</div></div>
    </div>
  </div>

  <div class="panel">
    <div class="lbl">Amount composed</div>
    <div class="amt-big"><span class="cur">৳</span><span id="amt" data-v="0">0</span></div>
    <div class="amt-sub" id="amtSub">Tap denomination tokens — each tap adds a note</div>
    <div class="stack" id="stack"></div>
    <div class="legend"><div class="lbl">Denomination tokens</div><div class="row" id="legend"></div></div>
  </div>
</section>

<div class="log hidden" id="log"><div class="lbl">This session</div><div class="items" id="logItems"></div></div>

<div id="idle" class="hidden"><div class="box"><div class="cap">Inactivity</div><div class="num" id="idleNum">5</div><div class="msg">Locking automatically — tap any card or button to stay</div></div></div>
<div id="success" class="hidden"><div class="box"><div class="chk"><svg viewBox="0 0 52 52"><path d="M14 27l8 8 16-18"/></svg></div><h2>Transfer complete</h2><p id="successTxt"></p></div></div>

<script>
const N=12, ringSvg=document.getElementById('ringSvg');
(function buildRing(){const cx=200,cy=200,r=158,w=24,h=50;
  for(let i=0;i<N;i++){const e=document.createElementNS('http://www.w3.org/2000/svg','rect');
    e.setAttribute('x',cx-w/2);e.setAttribute('y',cy-r-h/2);e.setAttribute('width',w);e.setAttribute('height',h);e.setAttribute('rx',9);
    e.setAttribute('transform','rotate('+(i*30)+' '+cx+' '+cy+')');e.setAttribute('class','seg');ringSvg.appendChild(e);}})();
const segs=[...ringSvg.querySelectorAll('.seg')];

let prev={locked:null,recipient:null,tokensKey:'',bannerTs:''};
let flashUntil=0, flashClass='', successUntil=0, galleryBuilt=false;
const fmt=n=>Number(n).toLocaleString('en-US');

function toast(text,type){const t=document.createElement('div');t.className='toast '+type;
  const ic={success:'✓',error:'!',warning:'!',info:'i'}[type]||'i';
  t.innerHTML='<div class="ic">'+ic+'</div><div>'+text+'</div>';document.getElementById('toasts').appendChild(t);
  setTimeout(()=>t.classList.add('out'),2600);setTimeout(()=>t.remove(),2950);}
function flashRing(cls,ms){flashClass=cls;flashUntil=Date.now()+ms;}
function pulse(id){const k=document.getElementById(id);k.classList.add('pulse');setTimeout(()=>k.classList.remove('pulse'),450);}
function animateNumber(el,to){if(el.dataset.target==String(to))return;el.dataset.target=String(to);
  const from=parseInt(el.dataset.v||'0'),start=performance.now(),dur=520;
  (function step(t){const p=Math.min(1,(t-start)/dur),e=1-Math.pow(1-p,3);const v=Math.round(from+(to-from)*e);
    el.textContent=fmt(v);if(p<1)requestAnimationFrame(step);else el.dataset.v=String(to);})(start);}

function buildGallery(s){if(galleryBuilt)return;galleryBuilt=true;
  const g=document.getElementById('gallery');
  s.all_recipients.forEach(n=>{const d=document.createElement('div');d.className='g-item';d.id='g-'+n.toLowerCase();
    d.innerHTML='<img src="/photos/'+n.toLowerCase()+'.jpg"><div class="gn">'+n+'</div>';g.appendChild(d);});
  const l=document.getElementById('legend');
  s.all_denominations.forEach(v=>{const d=document.createElement('div');d.className='d';
    d.innerHTML='<img src="/photos/'+v+'.jpg"><span>৳ '+fmt(v)+'</span>';l.appendChild(d);});}

function setStep(i){document.querySelectorAll('.step').forEach(st=>{const k=+st.dataset.i;st.classList.toggle('done',k<i);st.classList.toggle('active',k===i);});
  document.querySelectorAll('.step-line').forEach((ln,k)=>ln.classList.toggle('done',k<i));}

function renderRing(s){const now=Date.now();
  ringSvg.classList.toggle('warning',!s.locked&&s.idle_warning_active&&now>=flashUntil);
  if(now<flashUntil){segs.forEach(g=>g.setAttribute('class','seg '+flashClass));return;}
  if(!s.locked&&s.idle_warning_active){segs.forEach(g=>g.setAttribute('class','seg'));return;}
  let lit=0;if(!s.locked&&s.hold_active)lit=Math.round(s.hold_percent*N/100);
  if(!s.locked&&now<successUntil)lit=N;
  segs.forEach((g,i)=>g.setAttribute('class','seg'+(i<lit?' lit':'')));}

function handleBanner(s){if(!s.banner_text||s.banner_timestamp===prev.bannerTs)return;prev.bannerTs=s.banner_timestamp;
  const tx=s.banner_text,ty=s.banner_type;
  if(tx.startsWith('Sent ')){successUntil=Date.now()+2800;flashRing('lit',2800);
    document.getElementById('successTxt').innerHTML=tx.replace(/^Sent (\S+) taka to (.+)$/,'<b>৳ $1</b> to <b>$2</b>');
    const ov=document.getElementById('success');ov.classList.remove('hidden');setTimeout(()=>ov.classList.add('hidden'),2800);
    document.getElementById('ybtn').classList.add('done');setTimeout(()=>document.getElementById('ybtn').classList.remove('done'),2800);return;}
  toast(tx,ty);
  if(ty==='success')flashRing('lit',450);else if(ty==='error')flashRing('red',600);else if(ty==='warning')flashRing('amber',600);else flashRing('soft',350);
  if(tx.startsWith('Balance:')||tx==='Transaction cancelled')pulse('kPink');
  else if(!tx.startsWith('Released early')&&!tx.startsWith('Select a recipient and amount')&&!tx.startsWith('Session locked'))pulse('kGreen');
  if(s.locked&&ty==='error'){const c=document.getElementById('lockCard');c.classList.remove('shake');void c.offsetWidth;c.classList.add('shake');}}

function render(s){
  document.getElementById('lockedView').classList.toggle('hidden',!s.locked);
  document.getElementById('mainView').classList.toggle('hidden',s.locked);
  document.getElementById('account').classList.toggle('hidden',s.locked);
  document.getElementById('log').classList.toggle('hidden',s.locked||!s.history||!s.history.length);
  const pill=document.getElementById('pill');pill.classList.toggle('on',!s.locked);document.getElementById('pillTxt').textContent=s.locked?'Locked':'Session active';
  document.getElementById('idle').classList.toggle('hidden',s.locked||!s.idle_warning_active);
  if(s.idle_warning_active)document.getElementById('idleNum').textContent=s.idle_seconds_left;

  if(s.locked){setStep(0);renderRing(s);return;}
  buildGallery(s);
  animateNumber(document.getElementById('bal'),s.balance);document.getElementById('bal').textContent='৳ '+fmt(s.balance);
  animateNumber(document.getElementById('amt'),s.amount);

  // recipient
  const has=!!s.recipient;
  document.getElementById('recipEmpty').classList.toggle('hidden',has);
  document.getElementById('recipPhoto').classList.toggle('hidden',!has);
  document.getElementById('recipTo').classList.toggle('hidden',!has);
  const nm=document.getElementById('recipName');
  if(has){nm.textContent=s.recipient;nm.style.color='';nm.style.fontSize='';document.getElementById('recipHint').textContent='Now compose the amount with denomination tokens';
    if(s.recipient!==prev.recipient){const ph=document.getElementById('recipPhoto');ph.src='/photos/'+s.recipient.toLowerCase()+'.jpg';ph.classList.remove('pop');void ph.offsetWidth;ph.classList.add('pop');}}
  else{nm.textContent='No recipient yet';nm.style.color='var(--dim)';nm.style.fontSize='22px';document.getElementById('recipHint').textContent='Tap one of the photo cards on the green zone';}
  prev.recipient=s.recipient;
  s.all_recipients.forEach(n=>{const el=document.getElementById('g-'+n.toLowerCase());if(el)el.classList.toggle('active',s.recipient===n);});

  // tokens
  const key=s.tokens.join(',');
  if(key!==prev.tokensKey){const st=document.getElementById('stack');const prevCount=prev.tokensKey?prev.tokensKey.split(',').length:0;st.innerHTML='';
    s.tokens.forEach((v,i)=>{const c=document.createElement('div');c.className='chip'+(i>=prevCount?' pop':'');c.innerHTML='<img src="/photos/'+v+'.jpg"><div class="cl">৳ '+fmt(v)+'</div>';st.appendChild(c);});
    prev.tokensKey=key;}
  document.getElementById('amtSub').textContent=s.tokens.length?s.tokens.length+' token'+(s.tokens.length>1?'s':'')+' placed · tap the ✕ card to remove the last one':'Tap denomination tokens — each tap adds a note';

  // step + button + instruction
  const ready=has&&s.amount>0;const ybtn=document.getElementById('ybtn'),pct=document.getElementById('pct'),hand=document.getElementById('hand');
  const big=document.getElementById('instrBig'),small=document.getElementById('instrSmall');
  ybtn.classList.remove('ready','holding');pct.classList.add('hidden');hand.classList.remove('hidden');
  if(Date.now()<successUntil){setStep(3);big.textContent='Transfer complete';small.textContent='New balance announced · ready for the next transaction';}
  else if(s.hold_active){setStep(3);ybtn.classList.add('holding');pct.classList.remove('hidden');hand.classList.add('hidden');
    pct.innerHTML=s.hold_percent+'%<small>keep holding</small>';big.textContent='Keep holding…';small.textContent='Release before the ring fills to cancel';}
  else if(ready){setStep(3);ybtn.classList.add('ready');big.textContent='Hold the yellow button';small.textContent='Hold until all 12 segments light up · '+fmt(s.amount)+' taka to '+s.recipient;}
  else if(has){setStep(2);big.textContent='Add the amount';small.textContent='Tap denomination tokens on the green zone';}
  else{setStep(1);big.textContent='Choose a recipient';small.textContent='Tap a photo card on the green zone';}

  // log
  if(s.history&&s.history.length){const li=document.getElementById('logItems');li.innerHTML='';
    s.history.forEach(h=>{const d=document.createElement('div');d.className='it';d.innerHTML='<em>'+h.timestamp+'</em><b>৳ '+fmt(h.amount)+'</b> → '+h.recipient+' · bal '+fmt(h.balance_after);li.appendChild(d);});}
  renderRing(s);
}

async function tick(){try{const r=await fetch('/api/state',{cache:'no-store'});const s=await r.json();handleBanner(s);render(s);}catch(e){}}
tick();setInterval(tick,200);
</script>
</body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)