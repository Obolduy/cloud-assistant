const BACKEND = window.BACKEND || 'http://127.0.0.1:8000';

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const md = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^[-*] /gm, '• ');
const log = $('log');
let sessionId = null;
let busy = false;

function addMsg(cls, text, extra) {
  const div = document.createElement('div');
  div.className = `msg ${cls}`;
  if (cls === 'bot') div.innerHTML = md(text);
  else div.textContent = text;
  if (extra) {
    const src = document.createElement('span');
    src.className = 'src';
    src.textContent = extra;
    div.appendChild(src);
  }
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function openSession() {
  const r = await fetch(`${BACKEND}/api/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: $('user').value }),
  });
  const data = await r.json();
  if (!r.ok) { addMsg('sys', `не удалось открыть сессию: ${data.detail || r.status}`); return; }
  sessionId = data.session_id;
  $('session-state').textContent = `сессия ${sessionId}`;
  $('session-sub').textContent = `${data.name} · ${data.role}`;
  $('text').disabled = false;
  $('send').disabled = false;
  const tools = data.visible_tools || [];
  $('tools').innerHTML = `<b>Видимые инструменты (${tools.length})</b>` + tools.map(t => `<div class="t">${esc(t)}</div>`).join('');
  addMsg('sys', `сессия открыта для ${data.name} (${data.role})`);
}

function handleEvent(ev) {
  if (ev.type === 'plan') {
    const dropped = ev.dropped?.length ? ` · отброшено: ${ev.dropped.join('; ')}` : '';
    addMsg('sys', `план: ${ev.agents.join(' → ')}${dropped}`);
  } else if (ev.type === 'reply') {
    addMsg('bot', ev.text, ev.sources?.length ? `источники: ${ev.sources.join(', ')}` : null);
  } else if (ev.type === 'error') {
    addMsg('sys', `ошибка хода: ${ev.detail}`);
  }
}

async function send(text) {
  addMsg('user', text);
  busy = true; $('send').disabled = true;
  try {
    const r = await fetch(`${BACKEND}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const line = buf.slice(0, idx).split('\n').find(l => l.startsWith('data: '));
        buf = buf.slice(idx + 2);
        if (line) handleEvent(JSON.parse(line.slice(6)));
      }
    }
  } catch (e) {
    addMsg('sys', `сеть: ${e}`);
  } finally {
    busy = false; $('send').disabled = false;
  }
}

$('form').onsubmit = e => {
  e.preventDefault();
  if (busy || !sessionId) return;
  const text = $('text').value.trim();
  if (!text) return;
  $('text').value = '';
  send(text);
};
$('user').onchange = () => { sessionId = null; log.innerHTML = ''; openSession(); };
openSession();
