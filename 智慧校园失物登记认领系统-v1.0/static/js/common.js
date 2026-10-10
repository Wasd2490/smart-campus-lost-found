/**
 * 智慧校园失物登记认领系统 - 公共JS模块
 * 提供：HTTP请求封装、导航栏渲染、HTML转义、状态徽章、时间格式化
 * 所有页面都引入此文件
 */

/** 统一HTTP请求封装：自动序列化JSON、带Cookie、解析错误 */
async function api(url, options = {}) {
  const opts = Object.assign({
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  }, options);
  if (opts.body && typeof opts.body !== 'string') {
    opts.body = JSON.stringify(opts.body);
  }
  const resp = await fetch(url, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok && !data.error) {
    data.error = '请求失败 (' + resp.status + ')';
  }
  return data;
}

/** 渲染顶部导航栏：根据登录状态显示不同按钮 */
async function renderNavbar() {
  const navEl = document.getElementById('navbar');
  if (!navEl) return;
  const { user } = await api('/api/me');
  let rightLinks;
  if (user) {
    const adminLink = user.role === 'admin'
      ? '<a href="/admin.html">管理后台</a>' : '';
    rightLinks = `
      <span class="user-info">${escapeHtml(user.real_name || user.username)}</span>
      <a href="/my.html">我的记录</a>
      ${adminLink}
      <a href="#" onclick="doLogout();return false;">退出</a>
    `;
  } else {
    rightLinks = `
      <a href="/login.html">登录</a>
      <a href="/register.html">注册</a>
    `;
  }
  navEl.innerHTML = `
    <div class="container inner">
      <a href="/" class="brand">
        <span class="logo">智</span>
        智慧校园失物登记认领系统
      </a>
      <div class="links">
        <a href="/">首页</a>
        <a href="/post-notice.html">捡到物品</a>
        <a href="/post-lost.html">丢失物品</a>
        ${rightLinks}
      </div>
    </div>
  `;
  window.__CURRENT_USER = user;
}

async function doLogout() {
  await api('/api/logout', { method: 'POST' });
  location.href = '/';
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function statusBadge(status) {
  const map = {
    pending: '<span class="badge pending">待审核</span>',
    approved: '<span class="badge approved">已通过</span>',
    rejected: '<span class="badge rejected">已驳回</span>',
    claimed: '<span class="badge claimed">已完成</span>',
  };
  return map[status] || status;
}

function fmtTime(s) {
  if (!s) return '';
  return String(s).replace('T', ' ').slice(0, 16);
}

const icon = {
  location: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  clock: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  search: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  camera: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
};

function compressImage(file, maxW = 800, quality = 0.75) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => {
      const img = new Image();
      img.onload = () => {
        const w = Math.min(img.width, maxW);
        const h = img.height * (w / img.width);
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function uploadImage(dataUrl) {
  const r = await api('/api/upload', { method: 'POST', body: { image: dataUrl } });
  if (r.error) throw new Error(r.error);
  return r.path;
}

document.addEventListener('DOMContentLoaded', renderNavbar);
