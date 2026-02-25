const API = 'http://127.0.0.1:8000/api';
let sessionId = null;

const messagesEl = document.getElementById('messages');
const stateBoxEl = document.getElementById('stateBox');
const questionEl = document.getElementById('question');

function addUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'msg user';
  div.textContent = `你：${text}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderState(state) {
  stateBoxEl.innerHTML = `
    <div>登录状态：${state.logged_in ? '已登录' : '未登录'}</div>
    <div>用户：${state.username || '无'}</div>
    <div>可选单位：${(state.units || []).join(', ') || '无'}</div>
    <div>已选单位：${state.selected_unit || '无'}</div>
    <div>待续答问题：${state.pending_question || '无'}</div>
  `;
}

function drawChartInto(canvas, kind, payload) {
  if (!kind) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (kind === 'bar') {
    const value = payload.value || 0;
    ctx.fillStyle = '#ff6b6b';
    const w = Math.min(520, value * 30);
    ctx.fillRect(40, 120, w, 40);
    ctx.fillStyle = '#111';
    ctx.font = '16px sans-serif';
    ctx.fillText(`${payload.label}: ${value}`, 40, 100);
  } else if (kind === 'gauge_like') {
    const value = payload.value || 0;
    ctx.fillStyle = '#4dabf7';
    ctx.fillRect(40, 120, Math.min(520, value * 5), 30);
    ctx.fillStyle = '#111';
    ctx.font = '16px sans-serif';
    ctx.fillText(`在线率 ${value}%`, 40, 100);
  } else if (kind === 'floor_plan') {
    ctx.strokeRect(60, 50, 520, 170);
    ctx.strokeRect(80, 70, 140, 70);
    ctx.strokeRect(250, 70, 290, 70);
    ctx.strokeRect(80, 150, 460, 50);
    ctx.fillText('控制室', 110, 110);
    ctx.fillText('办公区', 360, 110);
    ctx.fillText('仓储区', 290, 180);
  }
}

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function ensureSession() {
  if (sessionId) return;
  const res = await post('/session', {});
  sessionId = res.session_id;
}

function createLoginForm(ui) {
  const box = document.createElement('div');
  box.className = 'inline-widget';
  box.innerHTML = `
    <div class="widget-title">请登录后继续业务查询</div>
    <input id="inline-username" placeholder="登录用户名" />
    <input id="inline-password" type="password" placeholder="用户密码" />
    <button id="inline-login-btn">${ui.submit_label || '登录'}</button>
  `;
  box.querySelector('#inline-login-btn').onclick = async () => {
    await ensureSession();
    const username = box.querySelector('#inline-username').value;
    const password = box.querySelector('#inline-password').value;
    const res = await post('/login', { session_id: sessionId, username, password });
    renderAssistantResponse(res);
  };
  return box;
}

function createUnitForm(extra) {
  const box = document.createElement('div');
  box.className = 'inline-widget';
  const options = (extra.units || []).map((u) => `<option value="${u}">${u}</option>`).join('');
  const submitLabel = (extra.ui || {}).submit_label || '确认单位';
  box.innerHTML = `
    <div class="widget-title">请选择单位后继续</div>
    <select id="inline-unit-select">${options}</select>
    <button id="inline-unit-btn">${submitLabel}</button>
  `;
  box.querySelector('#inline-unit-btn').onclick = async () => {
    await ensureSession();
    const unit = box.querySelector('#inline-unit-select').value;
    const res = await post('/select-unit', { session_id: sessionId, unit });
    renderAssistantResponse(res);
  };
  return box;
}

function renderAssistantResponse(res) {
  renderState(res.state);
  const extra = res.extra || {};

  const msg = document.createElement('div');
  msg.className = 'msg assistant';

  const text = document.createElement('div');
  text.className = 'assistant-text';
  text.textContent = `助手：${res.content}`;
  msg.appendChild(text);

  if (res.ui_action === 'show_login') {
    msg.appendChild(createLoginForm(extra.ui || {}));
  }

  if (res.ui_action === 'show_unit') {
    msg.appendChild(createUnitForm(extra));
  }

  if (res.ui_action === 'render_result' && extra.chart_type) {
    const canvas = document.createElement('canvas');
    canvas.className = 'inline-chart';
    canvas.width = 640;
    canvas.height = 260;
    msg.appendChild(canvas);
    drawChartInto(canvas, extra.chart_type, extra.chart_payload || {});
  }

  messagesEl.appendChild(msg);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendQuestion() {
  const q = questionEl.value.trim();
  if (!q) return;
  questionEl.value = '';
  addUserMessage(q);
  await ensureSession();
  const res = await post('/chat', { session_id: sessionId, question: q });
  renderAssistantResponse(res);
}

document.getElementById('sendBtn').onclick = sendQuestion;
