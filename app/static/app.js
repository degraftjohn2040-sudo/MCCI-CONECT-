'use strict';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);
let session = null;
let page = 'overview';
const offsets = { members: 0, attendance: 0, announcements: 0, audit: 0 };
const admins = ['owner', 'admin', 'super_admin'];
const readers = [...admins, 'pastor'];

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (session && options.method && options.method !== 'GET') headers['X-CSRF-Token'] = session.csrf_token;
  const response = await fetch(path, { ...options, headers, credentials: 'same-origin', cache: 'no-store' });
  if (!response.ok) {
    let message = 'Something went wrong. Please try again.';
    try { const data = await response.json(); if (typeof data.detail === 'string') message = data.detail; } catch (_) { /* Keep a safe default. */ }
    if (response.status === 401 && session) showLogin('Your session ended. Please sign in again.');
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function showLogin(message = '') {
  session = null;
  $('#app-view').hidden = true;
  $('#login-view').hidden = false;
  $$('form').forEach((form) => form.reset());
  $$('.form-message').forEach((el) => { el.textContent = ''; });
  $('#account-email').textContent = '';
  $('#login-error').textContent = message;
  // Do not leave sensitive record text in the DOM after logout or expiry.
  for (const name of Object.keys(offsets)) { $(`#${name}-list`).replaceChildren(); offsets[name] = 0; }
}
function showApp(data) {
  session = data;
  $('#login-view').hidden = true;
  $('#app-view').hidden = false;
  $('#account-email').textContent = data.email;
  $$('[data-access]').forEach((element) => {
    element.hidden = element.dataset.access === 'admin' ? !admins.includes(data.role) : !readers.includes(data.role);
  });
  $('#today').textContent = new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'short', day: 'numeric' }).format(new Date());
  navigate('overview');
}
async function navigate(name) {
  if (!['overview', 'members', 'attendance', 'announcements', 'audit'].includes(name)) return;
  if ((name === 'members' || name === 'attendance') && !readers.includes(session.role)) return;
  if (name === 'audit' && !admins.includes(session.role)) return;
  page = name;
  $$('.page').forEach((el) => { el.hidden = el.id !== `page-${name}`; });
  $$('.nav-item').forEach((el) => {
    const active = el.dataset.page === name;
    el.classList.toggle('active', active);
    if (active) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current');
  });
  $('#breadcrumb').textContent = name.toUpperCase();
  $('#global-error').hidden = true;
  if (name !== 'overview') await load(name);
}
function text(tag, value, className = '') {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}
function renderItem(name, item) {
  const row = document.createElement('article');
  row.className = 'list-item';
  if (name === 'members') {
    const avatar = text('div', item.name.slice(0, 1).toUpperCase(), 'avatar');
    const info = document.createElement('div');
    info.append(text('h3', item.name), text('p', [item.email, item.phone].filter(Boolean).join(' · ') || 'No contact details'));
    row.append(avatar, info);
  } else if (name === 'announcements') {
    const info = document.createElement('div');
    info.append(text('h3', item.title), text('p', item.body, 'pre-wrap'), text('small', `${item.created_at} UTC`));
    row.append(info);
  } else if (name === 'attendance') {
    const info = document.createElement('div');
    info.append(text('h3', item.event_name), text('p', item.event_date));
    row.append(info, text('span', `${item.headcount} attended`, 'count-pill'));
  } else {
    const info = document.createElement('div');
    info.append(text('h3', item.action), text('p', `Actor: ${item.actor_id ?? 'system'} · Record: ${item.resource_id ?? '—'}`), text('small', `${item.created_at} UTC`));
    row.append(info);
  }
  return row;
}
async function load(name) {
  const list = $(`#${name}-list`);
  const pagination = $(`#${name}-pagination`);
  list.replaceChildren(text('p', 'Loading…', 'empty'));
  pagination.replaceChildren();
  try {
    const result = await api(`/api/${name}?limit=25&offset=${offsets[name]}`);
    if (!session || page !== name) return;
    list.replaceChildren();
    if (!result.items.length) list.append(text('p', 'Nothing here yet. Records will appear here when added.', 'empty'));
    result.items.forEach((item) => list.append(renderItem(name, item)));
    if (offsets[name] > 0) {
      const previous = text('button', '← Previous');
      previous.addEventListener('click', () => { offsets[name] -= 25; load(name); });
      pagination.append(previous);
    }
    if (result.has_more) {
      const next = text('button', 'Next →');
      next.addEventListener('click', () => { offsets[name] += 25; load(name); });
      pagination.append(next);
    }
  } catch (error) { if (session && page === name) list.replaceChildren(text('p', error.message, 'empty error')); }
}
$('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button');
  button.disabled = true;
  $('#login-error').textContent = '';
  try {
    const values = Object.fromEntries(new FormData(form));
    const data = await api('/api/session', { method: 'POST', headers: { 'X-Requested-With': 'MCCI-CONNECT' }, body: JSON.stringify(values) });
    form.reset();
    showApp(data);
  } catch (error) { $('#login-error').textContent = error.message; }
  finally { button.disabled = false; }
});
$('#logout').addEventListener('click', async () => {
  try { await api('/api/session', { method: 'DELETE' }); showLogin(); }
  catch (error) { if (session) { $('#global-error').textContent = `Could not sign out: ${error.message}`; $('#global-error').hidden = false; } }
});
$$('[data-page]').forEach((button) => button.addEventListener('click', () => navigate(button.dataset.page)));
$$('[data-go]').forEach((button) => button.addEventListener('click', () => navigate(button.dataset.go)));
['members', 'attendance', 'announcements'].forEach((name) => {
  $(`#${name}-form`).addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button');
    const message = form.querySelector('.form-message');
    const values = Object.fromEntries(new FormData(form));
    if (name === 'attendance') values.headcount = Number(values.headcount);
    button.disabled = true;
    message.textContent = 'Saving…';
    try {
      await api(`/api/${name}`, { method: 'POST', body: JSON.stringify(values) });
      form.reset(); offsets[name] = 0; message.textContent = 'Saved successfully.'; await load(name);
    } catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  });
});
api('/api/session').then(showApp).catch(() => showLogin());
