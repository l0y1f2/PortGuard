/* PortGuard 前端逻辑 */
'use strict';

const S = {
  view: 'overview',
  snap: null,
  services: [],
  blocked: [],
  search: '',
  filters: { proto: 'ALL', focus: 'ALL', svcRunning: true },
  timer: null,
  loadingSvc: false,
};

const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h !== undefined) e.innerHTML = h; return e; };
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
const ICON = {
  warn: '<svg viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 2.5 18a2 2 0 0 0 1.7 3h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
  ok: '<svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>',
  err: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  ban: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/></svg>',
  box: '<svg viewBox="0 0 24 24"><path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
};

const VIEWS = {
  overview: ['总览', '这台电脑上正在监听的端口、跑着的服务，一眼看清'],
  ports: ['端口', '所有处于监听状态的端口，谁在占用、是否登记过'],
  processes: ['进程', '正在监听端口的进程，可直接结束'],
  services: ['服务', 'Windows 服务清单与它们关联的端口'],
  registry: ['端口台账', '把端口分配给哪个项目记下来，冲突自动报警'],
  firewall: ['防火墙', '由 PortGuard 创建的端口封禁规则'],
};

/* ------------------------------ 网络 ------------------------------ */
async function api(path, body) {
  const opt = body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

function toast(msg, type = 'ok') {
  const t = el('div', 'toast ' + type, (type === 'ok' ? ICON.ok : ICON.err) + '<span>' + esc(msg) + '</span>');
  $('#toasts').appendChild(t);
  setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 220); }, 2600);
}

/* ------------------------------ 弹窗 ------------------------------ */
function closeModal() { $('#modal-mask').classList.remove('show'); $('#modal').classList.remove('about'); }

/* ------------------------------ 关于 ------------------------------ */
function showAbout() {
  $('#modal-title').textContent = 'PortGuard';
  const ic = $('#modal-icon');
  ic.className = 'modal-icon show';
  ic.style.background = 'var(--blue-soft)';
  ic.style.color = 'var(--blue)';
  ic.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 2 4 6v6c0 5 3.4 8.4 8 10 4.6-1.6 8-5 8-10V6l-8-4z"/><path d="M9 12l2 2 4-4"/></svg>';

  const feats = [
    ['端口速览', '一键列出本机所有监听端口（TCP/UDP），自动识别 Redis、MySQL、Nacos、Vite、Spring Boot 等技术栈'],
    ['进程治理', '查看占用端口的进程详情，一键结束（带系统关键进程保护，不会误杀）'],
    ['服务关联', '把 Windows 服务与它们监听的端口对应起来'],
    ['端口台账', '把每个端口记给哪个项目、什么用途，长期不忘'],
    ['冲突报警', '登记的端口被非预期程序占用时，首页直接标红提醒'],
    ['防火墙封禁', '一键创建 / 解除 Windows 防火墙端口规则'],
    ['端口分配助手', '智能推荐空闲端口，下次分配不再撞车'],
  ];
  const featsHtml = feats.map(([t, d]) =>
    `<div class="ab-feat"><div class="ab-dot"></div><div><b>${t}</b><span>${d}</span></div></div>`).join('');

  $('#modal-text').innerHTML = `
    <div class="ab-desc">本机端口 / 进程 / 服务管家 —— 让你清楚知道电脑上什么软件在跑、用了什么端口，再也不被端口冲突困扰。</div>
    <div class="ab-feats">${featsHtml}</div>
    <div class="ab-meta">
      <div><span class="ab-k">开发者</span><span class="ab-v">李云飞</span></div>
      <div><span class="ab-k">开源地址</span><span class="ab-v"><a href="http://github.com/l0y1f2" target="_blank" rel="noopener">github.com/l0y1f2</a></span></div>
      <div><span class="ab-k">版本</span><span class="ab-v">v1.0</span></div>
    </div>
    <div class="ab-acts">
      <button class="btn btn-ghost btn-sm" id="ab-admin">以管理员身份重启</button>
      <button class="btn btn-ghost btn-sm" id="ab-quit">退出 PortGuard</button>
    </div>`;

  $('#ab-admin').onclick = async () => {
    const r = await api('/api/relaunch-admin');
    if (r.ok) toast('正在以管理员身份重启…', 'ok');
    else toast(r.msg || '提权失败', 'err');
  };
  $('#ab-quit').onclick = async () => { await api('/api/quit'); };

  const form = $('#modal-form');
  form.innerHTML = '';
  form.className = 'modal-form';
  const acts = $('#modal-actions');
  acts.innerHTML = '';
  const close = el('button', 'btn btn-primary', '我了解了');
  close.style.flex = '1';
  close.onclick = closeModal;
  acts.append(close);
  $('#modal').classList.add('about');
  $('#modal-mask').classList.add('show');
}

function dialog({ title, text = '', icon = '', fields = null, okText = '确定', okClass = 'btn-primary', onOk }) {
  $('#modal-title').textContent = title;
  $('#modal-text').innerHTML = text;
  const ic = $('#modal-icon');
  ic.className = 'modal-icon' + (icon ? ' show ' + icon : '');
  ic.innerHTML = icon ? (icon === 'danger' ? ICON.warn : ICON.warn) : '';

  const form = $('#modal-form');
  form.innerHTML = '';
  form.className = 'modal-form' + (fields ? ' show' : '');
  if (fields) form.innerHTML = fields;

  const acts = $('#modal-actions');
  acts.innerHTML = '';
  const cancel = el('button', 'btn btn-ghost', '取消');
  cancel.onclick = closeModal;
  const ok = el('button', 'btn ' + okClass, okText);
  ok.onclick = async () => {
    ok.disabled = true;
    try { const keep = await onOk(); if (!keep) closeModal(); } finally { ok.disabled = false; }
  };
  acts.append(cancel, ok);
  $('#modal-mask').classList.add('show');
  setTimeout(() => { const f = form.querySelector('input,select,textarea'); if (f) f.focus(); }, 120);
}

/* ------------------------------ 操作 ------------------------------ */
function killProcess(pid, pname, risk, ports) {
  if (risk === 'protected') {
    dialog({
      title: '这个进程不能结束', icon: 'danger',
      text: `<b>${esc(pname)}</b> 是 Windows 关键进程，结束它会导致系统崩溃或强制重启，已阻止该操作。`,
      okText: '我明白了', okClass: 'btn-ghost', onOk: () => { },
    });
    return;
  }
  const extra = risk === 'risky'
    ? `<div style="margin-top:10px;padding:9px 11px;border-radius:8px;background:var(--orange-soft);color:#8a5300;font-size:12px;text-align:left">
         ⚠️ <b>${esc(pname)}</b> 属于系统级进程，结束后可能导致部分 Windows 功能异常（通常可自动恢复或重启后恢复）。</div>` : '';
  dialog({
    title: '确认结束该进程？', icon: 'danger',
    text: `即将强制结束 <b>${esc(pname)}</b>（PID ${pid}）${ports && ports.length ? '，它正在监听端口 <b>' + ports.join('、') + '</b>' : ''}。
           未保存的数据会丢失。${extra}`,
    fields: `<label class="switch-wrap" style="justify-content:flex-start"><input type="checkbox" id="kill-tree"><span class="switch"></span><span class="switch-label">同时结束它启动的子进程</span></label>`,
    okText: '结束进程', okClass: 'btn-danger',
    onOk: async () => {
      const tree = $('#kill-tree') && $('#kill-tree').checked;
      const r = await api('/api/kill', { pid, force: true, tree });
      toast(r.msg, r.ok ? 'ok' : 'err');
      if (r.ok) setTimeout(refresh, 400);
    },
  });
}

function blockPort(port, proto) {
  dialog({
    title: `封禁 ${proto} 端口 ${port}`, icon: 'warn',
    text: '将创建 Windows 防火墙阻止规则。占用该端口的程序仍在运行，但网络请求会被拦截。',
    fields: `<div class="field"><label>方向</label>
        <select id="fw-dir"><option value="in">仅入站（外部访问被拦截）</option>
        <option value="both">双向（入站 + 出站）</option><option value="out">仅出站</option></select></div>
      <div class="field-hint">规则名以 PortGuard_Block 开头，可在「防火墙」页一键解封。</div>`,
    okText: '确认封禁', okClass: 'btn-danger',
    onOk: async () => {
      const r = await api('/api/block', { port, proto, direction: $('#fw-dir').value });
      toast(r.msg, r.ok ? 'ok' : 'err');
      if (r.ok) { loadBlocked(); }
    },
  });
}

async function unblockPort(port, proto) {
  const r = await api('/api/unblock', { port, proto });
  toast(r.msg, r.ok ? 'ok' : 'err');
  loadBlocked();
}

function regDialog(entry, preset) {
  const e = entry || {};
  const p = preset || {};
  dialog({
    title: entry ? '编辑端口登记' : '登记端口用途',
    text: entry ? '' : '记下这个端口是给哪个项目用的，下次就不会忘、也不会撞车。',
    fields: `
      <div class="field-row">
        <div class="field"><label>端口 *</label><input id="r-port" type="number" min="1" max="65535" value="${e.port || p.port || ''}"></div>
        <div class="field"><label>端口段结束（可选）</label><input id="r-end" type="number" min="1" max="65535" value="${e.port_end || ''}" placeholder="如 3010"></div>
        <div class="field" style="flex:0 0 90px"><label>协议</label><select id="r-proto">
          ${['ANY', 'TCP', 'UDP'].map(x => `<option ${((e.proto || p.proto || 'ANY') === x) ? 'selected' : ''}>${x}</option>`).join('')}
        </select></div>
      </div>
      <div class="field"><label>项目 / 系统名称 *</label><input id="r-project" value="${esc(e.project || '')}" placeholder="如：订单中心后端"></div>
      <div class="field"><label>用途说明</label><input id="r-purpose" value="${esc(e.purpose || p.purpose || '')}" placeholder="如：Spring Boot 主服务 / 本地调试网关"></div>
      <div class="field-row">
        <div class="field"><label>期望进程（用于冲突检测）</label><input id="r-expect" value="${esc(e.expect || p.expect || '')}" placeholder="如 java.exe"></div>
        <div class="field"><label>负责人</label><input id="r-owner" value="${esc(e.owner || '')}" placeholder="如 我 / 张三"></div>
      </div>
      <div class="field"><label>标签（逗号分隔）</label><input id="r-tags" value="${esc((e.tags || []).join(','))}" placeholder="后端,内网,生产同构"></div>
      <div class="field"><label>备注</label><textarea id="r-note" placeholder="启动命令、配置文件位置、依赖关系…">${esc(e.note || '')}</textarea></div>`,
    okText: entry ? '保存修改' : '登记',
    onOk: async () => {
      const body = {
        id: e.id, port: $('#r-port').value, port_end: $('#r-end').value, proto: $('#r-proto').value,
        project: $('#r-project').value, purpose: $('#r-purpose').value, expect: $('#r-expect').value,
        owner: $('#r-owner').value, tags: $('#r-tags').value, note: $('#r-note').value,
      };
      const r = await api('/api/registry/save', body);
      toast(r.msg, r.ok ? 'ok' : 'err');
      if (r.ok) refresh(); else return true;
    },
  });
}

function regDelete(entry) {
  dialog({
    title: '删除这条登记？', icon: 'danger',
    text: `端口 <b>${entry.port}</b>（${esc(entry.project)}）的登记信息将被删除，不影响正在运行的程序。`,
    okText: '删除', okClass: 'btn-danger',
    onOk: async () => { const r = await api('/api/registry/delete', { id: entry.id }); toast(r.msg, r.ok ? 'ok' : 'err'); if (r.ok) refresh(); },
  });
}

/* ------------------------------ 详情抽屉 ------------------------------ */
function closeDrawer() { $('#drawer').classList.remove('show'); $('#drawer-mask').classList.remove('show'); }

async function showDetail(pid, fallbackName) {
  $('#drawer-title').textContent = fallbackName || ('PID ' + pid);
  $('#drawer-sub').textContent = 'PID ' + pid;
  $('#drawer-body').innerHTML = '<div class="loading">读取中…</div>';
  $('#drawer').classList.add('show');
  $('#drawer-mask').classList.add('show');

  let d;
  try { d = await api('/api/process?pid=' + pid); } catch (err) { d = { error: String(err) }; }
  if (d.error) { $('#drawer-body').innerHTML = `<div class="empty">${esc(d.error)}</div>`; return; }

  $('#drawer-title').textContent = d.name || ('PID ' + pid);
  $('#drawer-sub').textContent = `PID ${pid}${d.stack ? ' · ' + d.stack : ''}${d.user ? ' · ' + d.user : ''}`;

  const kv = (title, rows) => `<div class="kv"><div class="kv-title">${title}</div>${rows.map(([k, v]) =>
    `<div class="kv-row"><div class="kv-k">${k}</div><div class="kv-v">${v}</div></div>`).join('')}</div>`;

  let html = kv('基本信息', [
    ['状态', esc(d.status || '-')],
    ['已运行', esc(d.uptime || '-')],
    ['内存', d.mem_mb + ' MB'],
    ['CPU', d.cpu + ' %'],
    ['线程', d.threads],
    ['用户', esc(d.user || '-')],
    ['父进程', d.parent ? `${esc(d.parent.name)} <span class="dim">(PID ${d.parent.pid})</span>` : '-'],
  ]);

  if (d.services && d.services.length)
    html += kv('承载的 Windows 服务', [['服务', d.services.map(s => `<span class="tag teal">${esc(s)}</span>`).join(' ')]]);

  html += `<div class="kv"><div class="kv-title">程序路径</div><div class="copy-box">${esc(d.exe || '（无法读取）')}</div></div>`;
  html += `<div class="kv"><div class="kv-title">启动命令</div><div class="copy-box">${esc(d.cmdline || '（无法读取）')}</div></div>`;
  if (d.cwd) html += `<div class="kv"><div class="kv-title">工作目录</div><div class="copy-box">${esc(d.cwd)}</div></div>`;

  if (d.connections && d.connections.length) {
    const rows = d.connections.slice(0, 60).map(c =>
      `<div class="kv-row"><div class="kv-k">${esc(c.proto)} ${c.status === 'LISTEN' ? '<span class="tag green" style="margin-left:4px">监听</span>' : ''}</div>
       <div class="kv-v mono">${esc(c.local)}${c.remote ? ' → ' + esc(c.remote) : ''} <span class="dim">${c.status !== 'LISTEN' ? esc(c.status) : ''}</span></div></div>`).join('');
    html += `<div class="kv"><div class="kv-title">网络连接（${d.connections.length}）</div>${rows}</div>`;
  }

  if (d.children && d.children.length)
    html += kv('子进程（' + d.children.length + '）', [['列表', d.children.map(c => `<span class="tag">${esc(c.name)} ${c.pid}</span>`).join(' ')]]);

  if (d.open_files && d.open_files.length)
    html += `<div class="kv"><div class="kv-title">打开的文件（前 ${d.open_files.length} 个）</div><div class="copy-box">${d.open_files.map(esc).join('<br>')}</div></div>`;

  html += `<div style="display:flex;gap:8px;margin-top:18px">
      <button class="btn btn-outline" style="flex:1;justify-content:center" onclick="navigator.clipboard.writeText(${JSON.stringify(JSON.stringify({ pid: d.pid, name: d.name, exe: d.exe, cmdline: d.cmdline }))}).then(()=>window.__toast('已复制进程信息'))">复制信息</button>
      <button class="btn btn-danger" style="flex:1;justify-content:center" onclick="window.__kill(${pid},${JSON.stringify(d.name || '')},'${d.risk}',[])">结束进程</button>
    </div>`;
  $('#drawer-body').innerHTML = html;
}

/* ------------------------------ 渲染：总览 ------------------------------ */
function statCard(cls, label, value, hint, go) {
  const s = el('div', 'stat ' + cls, `<div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-hint">${hint}</div>`);
  if (go) s.onclick = () => switchView(go);
  return s;
}

function renderOverview() {
  const c = $('#content');
  c.innerHTML = '';
  const st = S.snap.stats;

  const stats = el('div', 'stats');
  stats.append(
    statCard('blue', '监听端口', st.listen_total, `TCP ${st.tcp} · UDP ${st.udp}`, 'ports'),
    statCard('', '开发相关端口', st.dev_ports, '框架 / 数据库 / 容器', 'ports'),
    statCard('ok', '已登记', st.registered, '写进台账的端口分配', 'registry'),
    statCard(st.conflicts ? 'danger' : 'ok', '端口冲突', st.conflicts, st.conflicts ? '有端口被非预期程序占用' : '暂无冲突', 'registry'),
    statCard(st.warnings ? 'warn' : '', '需要留意', st.warnings, '重复监听等异常', 'ports'),
    statCard('', '对外暴露', st.public, '监听 0.0.0.0，局域网可访问', 'ports'),
  );
  c.append(stats);

  // 冲突与告警
  const issues = S.snap.issues || [];
  const card = el('div', 'card');
  card.append(el('div', 'card-head', `<h2>${ICON.warn}冲突与提醒</h2><span class="sub">${issues.length ? issues.length + ' 条' : '一切正常'}</span>`));
  if (!issues.length) {
    card.append(el('div', 'empty', ICON.ok + '没有发现端口冲突，安心开发'));
  } else {
    const body = el('div', 'card-body flush');
    issues.forEach(is => {
      const row = el('div', 'issue ' + is.level);
      row.innerHTML = `<div class="issue-ico">${ICON.warn}</div>
        <div class="issue-main"><div class="issue-title">${esc(is.title)}</div><div class="issue-detail">${esc(is.detail)}</div></div>`;
      const acts = el('div', 'acts');
      acts.style.opacity = 1;
      if (is.pid) {
        const b = el('button', 'btn btn-ghost btn-sm', '查看进程');
        b.onclick = () => showDetail(is.pid);
        acts.append(b);
      }
      row.append(acts);
      body.append(row);
    });
    card.append(body);
  }
  c.append(card);

  // 开发端口速览
  const dev = S.snap.ports.filter(p => ['dev', 'db', 'container'].includes(p.kind) || (p.reg && p.reg.project));
  const dcard = el('div', 'card');
  dcard.append(el('div', 'card-head', `<h2>${ICON.box}我的服务端口</h2><span class="sub">开发框架 / 数据库 / 容器 / 已登记项目</span>`));
  if (!dev.length) dcard.append(el('div', 'empty', '当前没有检测到开发相关服务在监听'));
  else dcard.append(buildPortTable(dev, true));
  c.append(dcard);

  // 端口分配助手
  const hcard = el('div', 'card');
  hcard.append(el('div', 'card-head', `<h2>${ICON.plus}要用新端口？让我帮你挑</h2><span class="sub">自动跳过已占用、已登记和知名端口</span>`));
  const hb = el('div', 'card-body');
  hb.innerHTML = `<div class="helper">
      <span class="dim">从</span><input type="number" id="sug-start" value="8000" min="1024" max="60000">
      <span class="dim">开始找</span>
      <button class="btn btn-outline btn-sm" id="sug-go">推荐可用端口</button>
      <span class="dim" style="font-size:12px">点击推荐结果可直接登记</span>
    </div><div class="chips" id="sug-out" style="margin-top:12px"></div>`;
  hcard.append(hb);
  c.append(hcard);

  $('#sug-go').onclick = async () => {
    const start = $('#sug-start').value || 8000;
    const r = await api('/api/suggest?start=' + start);
    const out = $('#sug-out');
    out.innerHTML = '';
    (r.ports || []).forEach(p => {
      const ch = el('button', 'chip', String(p));
      ch.onclick = () => regDialog(null, { port: p, proto: 'TCP' });
      out.append(ch);
    });
    if (!r.ports || !r.ports.length) out.innerHTML = '<span class="dim">没找到空闲端口，试试换个起始值</span>';
  };
}

/* ------------------------------ 渲染：端口表 ------------------------------ */
function scopeTag(row) {
  if (row.scope === '全网可访问') return '<span class="tag orange"><i class="tag-dot"></i>对外</span>';
  if (row.scope === '仅本机') return '<span class="tag"><i class="tag-dot"></i>本机</span>';
  return '<span class="tag blue"><i class="tag-dot"></i>网卡</span>';
}

function buildPortTable(rows, compact) {
  const wrap = el('div', 'tbl-wrap');
  const t = el('table');
  t.innerHTML = `<thead><tr>
      <th style="width:104px">端口</th>
      <th style="width:118px">用途 / 项目</th>
      <th>占用进程</th>
      <th style="width:64px">PID</th>
      <th style="width:78px">范围</th>
      ${compact ? '' : '<th style="width:76px">内存</th><th style="width:92px">运行时长</th>'}
      <th style="width:186px"></th></tr></thead>`;
  const tb = el('tbody');

  rows.forEach(row => {
    const tr = el('tr', row.reg_status === 'hijacked' ? 'row-danger' : '');
    const regHtml = row.reg
      ? `<div><span class="tag ${row.reg_status === 'hijacked' ? 'red' : 'blue'}">${esc(row.reg.project)}</span></div>
         ${row.reg.purpose ? `<div class="sub-line ellip" style="max-width:150px">${esc(row.reg.purpose)}</div>` : ''}`
      : `<span class="dim" style="font-size:12px">${row.hint ? esc(row.hint.slice(0, 14)) : '未登记'}</span>`;

    const stackTag = row.stack ? `<span class="tag ${row.kind === 'db' ? 'purple' : row.kind === 'container' ? 'teal' : row.kind === 'system' ? '' : 'green'}">${esc(row.stack)}</span>` : '';
    const svcTag = (row.services || []).length ? `<span class="tag teal">${esc(row.services.slice(0, 2).join(','))}</span>` : '';

    tr.innerHTML = `
      <td><div class="port-cell"><span class="port-num">${row.port}</span><span class="tag">${row.proto}</span></div>
          ${row.hint && row.reg ? `<div class="sub-line">${esc(row.hint.slice(0, 16))}</div>` : ''}</td>
      <td>${regHtml}</td>
      <td><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
            <b style="font-weight:500">${esc(row.pname || '未知')}</b>${stackTag}${svcTag}
          </div>
          <div class="sub-line ellip" style="max-width:300px" title="${esc(row.exe)}">${esc(row.exe || '')}</div></td>
      <td class="mono dim">${row.pid || '-'}</td>
      <td>${scopeTag(row)}</td>
      ${compact ? '' : `<td class="mono dim nowrap">${row.mem_mb ? row.mem_mb + 'M' : '-'}</td>
      <td class="dim nowrap" style="font-size:12px">${esc(row.uptime || '-')}</td>`}
      <td></td>`;

    const acts = el('div', 'acts');
    if (!row.reg) {
      const b = el('button', 'btn btn-ghost btn-sm', '登记');
      b.onclick = e => { e.stopPropagation(); regDialog(null, { port: row.port, proto: row.proto, purpose: row.hint, expect: row.pname }); };
      acts.append(b);
    }
    const bBlock = el('button', 'btn btn-ghost btn-sm', '封禁');
    bBlock.onclick = e => { e.stopPropagation(); blockPort(row.port, row.proto); };
    const bKill = el('button', 'btn btn-danger btn-sm', '结束');
    bKill.onclick = e => { e.stopPropagation(); killProcess(row.pid, row.pname, row.risk, [row.port]); };
    if (row.pid) acts.append(bBlock, bKill); else acts.append(bBlock);
    tr.lastElementChild.append(acts);
    if (row.pid) tr.onclick = () => showDetail(row.pid, row.pname);
    tb.append(tr);
  });

  t.append(tb);
  wrap.append(t);
  return wrap;
}

function matchSearch(row) {
  const q = S.search.trim().toLowerCase();
  if (!q) return true;
  const hay = [row.port, row.proto, row.pname, row.exe, row.cmdline, row.hint,
  row.stack, (row.services || []).join(','), row.reg && row.reg.project,
  row.reg && row.reg.purpose, row.reg && (row.reg.tags || []).join(',')].join(' ').toLowerCase();
  return hay.includes(q);
}

function renderPorts() {
  const c = $('#content');
  c.innerHTML = '';
  let rows = S.snap.ports.filter(matchSearch);
  if (S.filters.proto !== 'ALL') rows = rows.filter(r => r.proto === S.filters.proto);
  if (S.filters.focus === 'DEV') rows = rows.filter(r => ['dev', 'db', 'container'].includes(r.kind) || r.reg);
  if (S.filters.focus === 'CONFLICT') rows = rows.filter(r => r.reg_status === 'hijacked' || r.multi_owner);
  if (S.filters.focus === 'UNREG') rows = rows.filter(r => !r.reg && r.port >= 1024 && r.port < 49152 && r.kind !== 'system');
  if (S.filters.focus === 'PUBLIC') rows = rows.filter(r => r.scope === '全网可访问');

  const card = el('div', 'card');
  const head = el('div', 'card-head');
  head.innerHTML = `<h2>监听端口 <span class="sub" style="margin-left:4px">${rows.length} / ${S.snap.ports.length}</span></h2>`;
  const tools = el('div', null, '');
  tools.style.cssText = 'display:flex;gap:8px;align-items:center';
  tools.innerHTML = `
    <div class="seg" id="seg-proto">${['ALL', 'TCP', 'UDP'].map(x => `<button data-v="${x}" class="${S.filters.proto === x ? 'active' : ''}">${x === 'ALL' ? '全部' : x}</button>`).join('')}</div>
    <div class="seg" id="seg-focus">${[['ALL', '全部'], ['DEV', '我的服务'], ['CONFLICT', '异常'], ['UNREG', '未登记'], ['PUBLIC', '对外暴露']]
      .map(([v, l]) => `<button data-v="${v}" class="${S.filters.focus === v ? 'active' : ''}">${l}</button>`).join('')}</div>`;
  head.append(tools);
  card.append(head);
  card.append(rows.length ? buildPortTable(rows) : el('div', 'empty', ICON.box + '没有符合条件的端口'));
  c.append(card);

  tools.querySelectorAll('#seg-proto button').forEach(b => b.onclick = () => { S.filters.proto = b.dataset.v; renderPorts(); });
  tools.querySelectorAll('#seg-focus button').forEach(b => b.onclick = () => { S.filters.focus = b.dataset.v; renderPorts(); });
}

/* ------------------------------ 渲染：进程 ------------------------------ */
function renderProcesses() {
  const c = $('#content');
  c.innerHTML = '';
  const q = S.search.trim().toLowerCase();
  const rows = S.snap.processes.filter(p => !q ||
    [p.name, p.exe, p.cmdline, p.stack, (p.services || []).join(','), p.listen_ports.join(',')].join(' ').toLowerCase().includes(q));

  const card = el('div', 'card');
  card.append(el('div', 'card-head', `<h2>正在监听端口的进程 <span class="sub" style="margin-left:4px">${rows.length} 个</span></h2>
    <span class="sub">系统共 ${S.snap.stats.proc_total} 个进程</span>`));

  if (!rows.length) { card.append(el('div', 'empty', '没有匹配的进程')); c.append(card); return; }

  const wrap = el('div', 'tbl-wrap');
  const t = el('table');
  t.innerHTML = `<thead><tr><th>进程</th><th style="width:64px">PID</th><th style="width:210px">监听端口</th>
    <th style="width:76px">内存</th><th style="width:60px">CPU</th><th style="width:96px">运行时长</th>
    <th style="width:88px">用户</th><th style="width:100px"></th></tr></thead>`;
  const tb = el('tbody');
  rows.forEach(p => {
    const tr = el('tr');
    const portTags = p.listen_ports.slice(0, 6).map(x => `<span class="tag blue mono">${x}</span>`).join(' ')
      + (p.listen_ports.length > 6 ? ` <span class="dim" style="font-size:11px">+${p.listen_ports.length - 6}</span>` : '');
    tr.innerHTML = `<td><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <b style="font-weight:500">${esc(p.name)}</b>
          ${p.stack ? `<span class="tag ${p.kind === 'db' ? 'purple' : p.kind === 'container' ? 'teal' : p.kind === 'system' ? '' : 'green'}">${esc(p.stack)}</span>` : ''}
          ${(p.services || []).length ? `<span class="tag teal">${esc(p.services.slice(0, 2).join(','))}</span>` : ''}</div>
        <div class="sub-line ellip" style="max-width:340px" title="${esc(p.cmdline || p.exe)}">${esc(p.exe || p.cmdline || '')}</div></td>
      <td class="mono dim">${p.pid}</td>
      <td>${portTags}</td>
      <td class="mono dim nowrap">${p.mem_mb}M</td>
      <td class="mono dim">${p.cpu}%</td>
      <td class="dim nowrap" style="font-size:12px">${esc(p.uptime || '-')}</td>
      <td class="dim ellip" style="max-width:88px">${esc(p.user || '-')}</td><td></td>`;
    const acts = el('div', 'acts');
    const bKill = el('button', 'btn btn-danger btn-sm', '结束');
    bKill.onclick = e => { e.stopPropagation(); killProcess(p.pid, p.name, p.risk, p.listen_ports); };
    acts.append(bKill);
    tr.lastElementChild.append(acts);
    tr.onclick = () => showDetail(p.pid, p.name);
    tb.append(tr);
  });
  t.append(tb);
  wrap.append(t);
  card.append(wrap);
  c.append(card);
}

/* ------------------------------ 渲染：服务 ------------------------------ */
async function renderServices() {
  const c = $('#content');
  if (!S.services.length && !S.loadingSvc) {
    c.innerHTML = '<div class="loading">正在读取 Windows 服务…</div>';
    S.loadingSvc = true;
    try { const r = await api('/api/services'); S.services = r.services || []; } catch (e) { }
    S.loadingSvc = false;
    if (S.view !== 'services') return;
  }
  c.innerHTML = '';
  const q = S.search.trim().toLowerCase();
  let rows = S.services.filter(s => !q || [s.name, s.display, s.binpath, s.description, (s.ports || []).join(',')].join(' ').toLowerCase().includes(q));
  if (S.filters.svcRunning) rows = rows.filter(s => s.status === 'running');

  const card = el('div', 'card');
  const head = el('div', 'card-head');
  head.innerHTML = `<h2>Windows 服务 <span class="sub" style="margin-left:4px">${rows.length} / ${S.services.length}</span></h2>`;
  const seg = el('div', 'seg');
  seg.innerHTML = `<button class="${S.filters.svcRunning ? 'active' : ''}" data-v="1">仅运行中</button><button class="${!S.filters.svcRunning ? 'active' : ''}" data-v="0">全部</button>`;
  seg.querySelectorAll('button').forEach(b => b.onclick = () => { S.filters.svcRunning = b.dataset.v === '1'; renderServices(); });
  head.append(seg);
  card.append(head);

  const wrap = el('div', 'tbl-wrap');
  const t = el('table');
  t.innerHTML = `<thead><tr><th>服务</th><th style="width:82px">状态</th><th style="width:86px">启动方式</th>
    <th style="width:64px">PID</th><th style="width:130px">端口</th><th>说明</th></tr></thead>`;
  const tb = el('tbody');
  rows.slice(0, 500).forEach(s => {
    const tr = el('tr');
    const stag = s.status === 'running' ? '<span class="tag green"><i class="tag-dot"></i>运行中</span>'
      : s.status === 'stopped' ? '<span class="tag"><i class="tag-dot"></i>已停止</span>'
        : `<span class="tag orange">${esc(s.status)}</span>`;
    tr.innerHTML = `<td><b style="font-weight:500">${esc(s.display || s.name)}</b>
        <div class="sub-line mono">${esc(s.name)}</div></td>
      <td>${stag}</td><td class="dim" style="font-size:12px">${esc(s.start_type || '-')}</td>
      <td class="mono dim">${s.pid || '-'}</td>
      <td>${(s.ports || []).map(p => `<span class="tag blue mono">${p}</span>`).join(' ') || '<span class="dim">-</span>'}</td>
      <td class="dim ellip" style="max-width:300px" title="${esc(s.description)}">${esc((s.description || '').slice(0, 70))}</td>`;
    if (s.pid) tr.onclick = () => showDetail(s.pid, s.display || s.name);
    tb.append(tr);
  });
  t.append(tb);
  wrap.append(t);
  card.append(rows.length ? wrap : el('div', 'empty', '没有匹配的服务'));
  c.append(card);
}

/* ------------------------------ 渲染：台账 ------------------------------ */
function renderRegistry() {
  const c = $('#content');
  c.innerHTML = '';
  const q = S.search.trim().toLowerCase();
  const rows = (S.snap.registry || []).filter(e => !q ||
    [e.port, e.project, e.purpose, e.owner, e.expect, e.note, (e.tags || []).join(',')].join(' ').toLowerCase().includes(q));

  const card = el('div', 'card');
  const head = el('div', 'card-head');
  head.innerHTML = `<h2>端口台账 <span class="sub" style="margin-left:4px">${rows.length} 条登记</span></h2>`;
  const addBtn = el('button', 'btn btn-primary btn-sm', ICON.plus + '新增登记');
  addBtn.onclick = () => regDialog(null, null);
  head.append(addBtn);
  card.append(head);

  const body = el('div', 'card-body');
  if (!rows.length) {
    body.innerHTML = `<div class="empty">${ICON.box}
      <div style="font-weight:500;color:var(--text);margin-bottom:4px">还没有登记任何端口</div>
      把「3306 是订单库」「8848 是本地 Nacos」这类分配记下来，<br>下次分配新端口时会自动避开，被别的程序抢占时会报警。</div>`;
  } else {
    const grid = el('div', 'reg-grid');
    rows.forEach(e => {
      const stat = e.status === 'conflict' ? '<span class="tag red"><i class="tag-dot"></i>被抢占</span>'
        : e.status === 'occupied_ok' ? '<span class="tag green"><i class="tag-dot"></i>运行中</span>'
          : '<span class="tag"><i class="tag-dot"></i>空闲</span>';
      const card2 = el('div', 'reg-card' + (e.status === 'conflict' ? ' conflict' : ''));
      card2.innerHTML = `
        <div class="reg-top"><div class="reg-port">${e.port}${e.port_end ? '–' + e.port_end : ''}
            <span class="tag" style="vertical-align:middle;margin-left:2px">${esc(e.proto)}</span></div>${stat}</div>
        <div class="reg-project">${esc(e.project)}</div>
        ${e.purpose ? `<div class="reg-purpose">${esc(e.purpose)}</div>` : ''}
        <div class="reg-meta">
          ${e.expect ? `<span class="tag blue">期望 ${esc(e.expect)}</span>` : ''}
          ${e.owner ? `<span class="tag">${esc(e.owner)}</span>` : ''}
          ${(e.tags || []).map(t => `<span class="tag purple">${esc(t)}</span>`).join('')}
        </div>
        ${e.holder ? `<div class="sub-line" style="margin-top:8px">当前占用：<b>${esc(e.holder.pname || '未知')}</b> (PID ${e.holder.pid})</div>` : ''}
        ${e.note ? `<div class="sub-line" style="margin-top:6px">${esc(e.note)}</div>` : ''}`;
      const acts = el('div', 'reg-acts');
      const bEdit = el('button', 'btn btn-ghost btn-sm', '编辑');
      bEdit.onclick = () => regDialog(e);
      const bDel = el('button', 'btn btn-ghost btn-sm', '删除');
      bDel.onclick = () => regDelete(e);
      acts.append(bEdit, bDel);
      if (e.holder && e.holder.pid) {
        const bView = el('button', 'btn btn-outline btn-sm', '查看占用者');
        bView.onclick = () => showDetail(e.holder.pid, e.holder.pname);
        acts.append(bView);
      }
      card2.append(acts);
      grid.append(card2);
    });
    body.append(grid);
  }
  card.append(body);
  c.append(card);
}

/* ------------------------------ 渲染：防火墙 ------------------------------ */
async function loadBlocked() {
  try { const r = await api('/api/blocked'); S.blocked = r.rules || []; } catch (e) { S.blocked = []; }
  if (S.view === 'firewall') renderFirewall();
}

function renderFirewall() {
  const c = $('#content');
  c.innerHTML = '';

  const add = el('div', 'card');
  add.append(el('div', 'card-head', `<h2>${ICON.ban}封禁一个端口</h2><span class="sub">创建 Windows 防火墙阻止规则</span>`));
  const ab = el('div', 'card-body');
  ab.innerHTML = `<div class="helper">
      <input type="number" id="fw-port" placeholder="端口号" min="1" max="65535" style="width:120px">
      <select id="fw-proto" style="padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-family:inherit;font-size:13px"><option>TCP</option><option>UDP</option></select>
      <select id="fw-dir2" style="padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-family:inherit;font-size:13px">
        <option value="in">仅入站</option><option value="both">双向</option><option value="out">仅出站</option></select>
      <button class="btn btn-danger btn-sm" id="fw-add">封禁</button>
      ${S.snap && !S.snap.admin ? '<span class="tag orange">需要管理员权限</span>' : ''}
    </div>
    <div class="field-hint" style="margin-top:9px">封禁只拦截网络流量，不会结束程序。规则统一以 PortGuard_Block 命名，方便随时解封或在防火墙里查找。</div>`;
  add.append(ab);
  c.append(add);

  const list = el('div', 'card');
  list.append(el('div', 'card-head', `<h2>已封禁的端口 <span class="sub" style="margin-left:4px">${S.blocked.length} 条</span></h2>`));
  if (!S.blocked.length) {
    list.append(el('div', 'empty', '还没有封禁任何端口'));
  } else {
    const wrap = el('div', 'tbl-wrap');
    const t = el('table');
    t.innerHTML = `<thead><tr><th style="width:110px">端口</th><th style="width:80px">协议</th><th style="width:100px">方向</th>
      <th style="width:90px">状态</th><th>规则名</th><th style="width:100px"></th></tr></thead>`;
    const tb = el('tbody');
    S.blocked.forEach(r => {
      const tr = el('tr');
      tr.style.cursor = 'default';
      tr.innerHTML = `<td><span class="port-num">${esc(r.port)}</span></td><td><span class="tag">${esc(r.proto)}</span></td>
        <td class="dim">${r.direction == 1 || r.direction === 'Inbound' ? '入站' : '出站'}</td>
        <td>${r.enabled ? '<span class="tag red"><i class="tag-dot"></i>生效中</span>' : '<span class="tag">已停用</span>'}</td>
        <td class="mono dim ellip" style="max-width:260px">${esc(r.name)}</td><td></td>`;
      const acts = el('div', 'acts');
      acts.style.opacity = 1;
      const b = el('button', 'btn btn-outline btn-sm', '解封');
      b.onclick = () => unblockPort(r.port, r.proto);
      acts.append(b);
      tr.lastElementChild.append(acts);
      tb.append(tr);
    });
    t.append(tb);
    wrap.append(t);
    list.append(wrap);
  }
  c.append(list);

  $('#fw-add').onclick = async () => {
    const port = parseInt($('#fw-port').value, 10);
    if (!port) { toast('请输入端口号', 'err'); return; }
    const r = await api('/api/block', { port, proto: $('#fw-proto').value, direction: $('#fw-dir2').value });
    toast(r.msg, r.ok ? 'ok' : 'err');
    if (r.ok) { $('#fw-port').value = ''; loadBlocked(); }
  };
}

/* ------------------------------ 调度 ------------------------------ */
function render() {
  if (!S.snap) return;
  if (S.view === 'overview') renderOverview();
  else if (S.view === 'ports') renderPorts();
  else if (S.view === 'processes') renderProcesses();
  else if (S.view === 'services') renderServices();
  else if (S.view === 'registry') renderRegistry();
  else if (S.view === 'firewall') renderFirewall();

  const st = S.snap.stats;
  $('#badge-ports').textContent = st.listen_total;
  $('#badge-procs').textContent = st.proc_with_port;
  const rb = $('#badge-reg');
  rb.textContent = st.conflicts ? st.conflicts + ' !' : st.registered;
  rb.className = 'nav-badge' + (st.conflicts ? ' alert' : '');
  $('#foot-engine').textContent = S.snap.engine === 'psutil' ? 'psutil' : 'PowerShell';
  $('#foot-admin').textContent = S.snap.admin ? '管理员 ✓' : '普通用户';
  $('#foot-time').textContent = new Date(S.snap.ts * 1000).toLocaleTimeString('zh-CN', { hour12: false });
  $('#admin-banner').hidden = !!S.snap.admin || sessionStorage.getItem('hideAdminTip') === '1';
}

function switchView(v) {
  if (!VIEWS[v]) v = 'overview';
  S.view = v;
  if (window.location.hash.slice(1) !== v) window.location.hash = v;
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  $('#view-title').textContent = VIEWS[v][0];
  $('#view-desc').textContent = VIEWS[v][1];
  if (v === 'firewall' && !S.blocked.length) loadBlocked();
  render();
}

function initViewFromHash() {
  const v = (window.location.hash || '#overview').slice(1).split('/')[0];
  return VIEWS[v] ? v : 'overview';
}

async function refresh(silent) {
  const ico = $('.ico-refresh');
  if (!silent && ico) ico.classList.add('spinning');
  try {
    S.snap = await api('/api/snapshot');
    render();
  } catch (e) {
    if (!silent) toast('读取失败：' + e.message, 'err');
  } finally {
    if (ico) setTimeout(() => ico.classList.remove('spinning'), 350);
  }
}

function setupAuto() {
  clearInterval(S.timer);
  if ($('#auto-refresh').checked) S.timer = setInterval(() => {
    if (!$('#modal-mask').classList.contains('show') && !$('#drawer').classList.contains('show')) refresh(true);
  }, 5000);
}

/* ------------------------------ 初始化 ------------------------------ */
document.querySelectorAll('.nav-item').forEach(b => b.onclick = () => switchView(b.dataset.view));
$('#btn-refresh').onclick = () => { S.services = []; refresh(); if (S.view === 'firewall') loadBlocked(); };
$('#auto-refresh').onchange = setupAuto;
window.addEventListener('hashchange', () => { switchView(initViewFromHash()); });
let searchTimer;
$('#search').oninput = e => {
  S.search = e.target.value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(render, 180);
};
$('#drawer-close').onclick = closeDrawer;
$('#drawer-mask').onclick = closeDrawer;
$('#modal-mask').onclick = e => { if (e.target.id === 'modal-mask') closeModal(); };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeDrawer(); closeModal(); }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); $('#search').focus(); }
  if (e.key === 'r' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); refresh(); }
});
$('#admin-banner').querySelector('button').onclick = () => {
  sessionStorage.setItem('hideAdminTip', '1');
  $('#admin-banner').hidden = true;
};
$('#btn-about').onclick = showAbout;

window.__kill = killProcess;
window.__toast = toast;

switchView(initViewFromHash());
refresh();
setupAuto();
