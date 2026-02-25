const API = 'http://127.0.0.1:8000/api';
let sessionId = null;

const messagesEl = document.getElementById('messages');
const stateBoxEl = document.getElementById('stateBox');
const questionEl = document.getElementById('question');
const canvas = document.getElementById('chart');
let activeWidget = null;

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = `${role === 'user' ? '你' : '助手'}：${text}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addWidget(container) {
  if (activeWidget) activeWidget.remove();
  activeWidget = container;
  messagesEl.appendChild(container);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function clearWidget() {
  if (activeWidget) {
    activeWidget.remove();
    activeWidget = null;
  }
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

function drawChart(kind, payload) {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!kind) return;

  if (kind === 'bar') {
    const value = payload.value || 0;
    ctx.fillStyle = '#ff6b6b';
    const w = Math.min(560, value * 35);
    ctx.fillRect(40, 120, w, 40);
    ctx.fillStyle = '#111';
    ctx.fillText(`${payload.label}: ${value}`, 40, 105);
  } else if (kind === 'gauge_like') {
    const value = payload.value || 0;
    ctx.fillStyle = '#4dabf7';
    ctx.fillRect(40, 120, Math.min(560, value * 5.2), 30);
    ctx.fillStyle = '#111';
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

function renderLoginWidget(ui = {}) {
  const card = document.createElement('div');
  card.className = 'widget-card';
  card.innerHTML = `
    <div class="widget-title">请登录后继续业务查询</div>
    <input id="inline-username" placeholder="登录用户名" />
    <input id="inline-password" type="password" placeholder="用户密码" />
    <button id="inline-login-btn">${ui.submit_label || '登录'}</button>
  `;
  addWidget(card);
  card.querySelector('#inline-login-btn').onclick = async () => {
    await ensureSession();
    const username = card.querySelector('#inline-username').value;
    const password = card.querySelector('#inline-password').value;
    const res = await post('/login', { session_id: sessionId, username, password });
    handleResponse(res);
  };
}

function renderUnitWidget(units = [], ui = {}) {
  const card = document.createElement('div');
  card.className = 'widget-card';
  const options = units.map((u) => `<option value="${u}">${u}</option>`).join('');
  card.innerHTML = `
    <div class="widget-title">请选择单位后继续</div>
    <select id="inline-unit-select">${options}</select>
    <button id="inline-unit-btn">${ui.submit_label || '确认单位'}</button>
  `;
  addWidget(card);
  card.querySelector('#inline-unit-btn').onclick = async () => {
    await ensureSession();
    const unit = card.querySelector('#inline-unit-select').value;
    const res = await post('/select-unit', { session_id: sessionId, unit });
    handleResponse(res);
  };
}

function handleResponse(res) {
  addMessage('assistant', res.content);
  renderState(res.state);
  const extra = res.extra || {};

  if (res.ui_action === 'show_login') {
    renderLoginWidget(extra.ui || {});
  } else if (res.ui_action === 'show_unit') {
    renderUnitWidget(extra.units || [], extra.ui || {});
  } else {
    clearWidget();
  }

  drawChart(extra.chart_type, extra.chart_payload || {});
}

async function sendQuestion() {
  const q = questionEl.value.trim();
  if (!q) return;
  questionEl.value = '';
  addMessage('user', q);
  await ensureSession();
  const res = await post('/chat', { session_id: sessionId, question: q });
  handleResponse(res);
}

document.getElementById('sendBtn').onclick = sendQuestion;
