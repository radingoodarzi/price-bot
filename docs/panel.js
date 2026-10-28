// Refuse to run inside someone else's frame (clickjacking).
if (window.top !== window.self) { document.documentElement.innerHTML = ''; throw new Error('framed'); }
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const DAYS = [["6","شنبه"],["7","یکشنبه"],["1","دوشنبه"],["2","سه‌شنبه"],["3","چهارشنبه"],["4","پنجشنبه"],["5","جمعه"]];
const STATUS_FA = { posted: "پست شد", error: "خطا", skipped: "رد شد" };
const WORKFLOW = "price-bot.yml";

let cfg = null, state = {}, catalog = [], shas = {}, repo = "", token = "", dirty = false;

function toast(text, kind = "ok") {
  const m = $("msg"); m.textContent = text; m.className = "msg " + kind; m.style.display = "block";
  clearTimeout(toast.t); toast.t = setTimeout(() => (m.style.display = "none"), kind === "err" ? 9000 : 3500);
}
function store(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }
function recall(k) { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } }

async function gh(path, opts = {}) {
  const r = await fetch("https://api.github.com/repos/" + repo + path, {
    ...opts,
    headers: { Accept: "application/vnd.github+json", Authorization: "Bearer " + token, "X-GitHub-Api-Version": "2022-11-28",
      ...(opts.body ? { "Content-Type": "application/json" } : {}) },
    cache: "no-store",
  });
  if (!r.ok) {
    let d = ""; try { d = (await r.json()).message; } catch (e) {}
    const hint = r.status === 401 ? "توکن اشتباه یا منقضی است" : r.status === 403 ? "دسترسی توکن کافی نیست" : r.status === 404 ? "مخزن یا فایل پیدا نشد" : "";
    throw new Error((hint || "خطای GitHub") + " (" + r.status + ")" + (d && !hint ? ": " + d : ""));
  }
  return r.status === 204 ? null : r.json();
}
const b64dec = (b) => new TextDecoder().decode(Uint8Array.from(atob(b.replace(/\n/g, "")), (c) => c.charCodeAt(0)));
const b64enc = (s) => { const u = new TextEncoder().encode(s); let bin = ""; u.forEach((c) => (bin += String.fromCharCode(c))); return btoa(bin); };

async function readFile(name, optional) {
  try {
    const f = await gh("/contents/" + name + "?ref=" + encodeURIComponent(await branch()) + "&t=" + Date.now());
    shas[name] = f.sha; return JSON.parse(b64dec(f.content));
  } catch (e) { if (optional) return null; throw e; }
}
let _branch = "";
async function branch() { if (!_branch) _branch = (await gh("")).default_branch; return _branch; }

async function loadAll() {
  cfg = await readFile("config.json");
  state = (await readFile("state.json", true)) || {};
  catalog = (await readFile("catalog.json", true)) || [];
  render(); dirty = false;
}

function render() {
  renderStats(); renderItems(); renderTimes(); renderDays(); renderCaption(); renderLog();
  $("enabled").checked = cfg.enabled !== false;
}function renderStats() {
  const st = state.last_status || "none";
  const next = nextSlots();
  const lastPost = state.last_post_at ? fmtDate(state.last_post_at) : "—";
  $("stats").innerHTML =
    stat("آخرین پست", lastPost) +
    stat("آخرین اجرا", state.last_run_at ? fmtDate(state.last_run_at) + ' <span class="pill ' + esc(st) + '">' + esc(STATUS_FA[st] || "—") + "</span>" : "—") +
    stat("نوبت بعدی", next) +
    stat("ردیف‌های قالب", (cfg.slots || []).length + " ردیف");
}
const stat = (a, b) => '<div class="stat"><span>' + a + "</span><b>" + b + "</b></div>";
function fmtDate(iso) { try { return new Date(iso).toLocaleString("fa-IR", { timeZone: "Asia/Tehran", dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; } }
function nextSlots() {
  const times = (cfg.schedule?.times || []).slice().sort(); if (!times.length) return "ساعتی تنظیم نشده";
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Tehran" }));
  const hm = String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0");
  const n = times.find((t) => t > hm);
  return n ? "امروز " + n.replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]) : "فردا " + times[0].replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);
}

function renderItems() {
  const box = $("items"); box.innerHTML = "";
  (cfg.slots || []).forEach((slot) => {
    const s = (slot.source ||= { type: "tgju", divisor: 10, decimals: 0 });
    const d = document.createElement("div"); d.className = "item";
    const opts = catalog.map((c) => '<option value="' + esc(c.slug) + '"' + (c.slug === s.slug ? " selected" : "") + ">" + esc(c.name) + " (" + esc(c.slug) + ")</option>").join("");
    const known = catalog.some((c) => c.slug === s.slug);
    d.innerHTML =
      '<div class="top" style="grid-template-columns:1.2fr 1fr 1.6fr .7fr .6fr">' +
      '<div><label>ردیف در عکس</label><b>' + esc(slot.label) + " <small>(" + esc(slot.unit) + ")</small></b></div>" +
      '<div><label>منبع</label><select data-k="type"><option value="tgju"' + (s.type !== "css" ? " selected" : "") + '>TGJU</option><option value="css"' + (s.type === "css" ? " selected" : "") + ">سایت دلخواه</option></select></div>" +
      '<div class="' + (s.type === "css" ? "hide" : "") + '"><label>آیتم TGJU</label><select data-k="slug">' + (known || !s.slug ? "" : '<option value="' + esc(s.slug) + '" selected>' + esc(s.slug) + "</option>") + opts + "</select></div>" +
      '<div class="' + (s.type === "css" ? "hide" : "") + '" style="display:none"></div>' +
      '<div><label>تقسیم بر</label><input type="number" data-k="divisor" value="' + esc(s.divisor ?? 1) + '" min="0.0001" step="any"></div>' +
      '<div><label>اعشار</label><input type="number" data-k="decimals" value="' + esc(s.decimals ?? 0) + '" min="0" max="4"></div>' +
      "</div>" +
      (s.type === "css"
        ? '<div class="src"><div><label>آدرس صفحه (https)</label><input type="text" dir="ltr" data-k="url" value="' + esc(s.url) + '"></div>' +
          '<div><label>سلکتور CSS عدد</label><input type="text" dir="ltr" data-k="selector" value="' + esc(s.selector) + '"></div></div>'
        : "");
    d.querySelectorAll("[data-k]").forEach((inp) => inp.addEventListener("input", () => {
      const k = inp.dataset.k; s[k] = inp.type === "number" ? Number(inp.value) : inp.value; dirty = true;
      if (k === "type") renderItems();
    }));
    box.appendChild(d);
  });
}
function renderTimes() {
  const box = $("times"); box.innerHTML = "";
  const times = (cfg.schedule.times = (cfg.schedule.times || []).slice().sort());
  times.forEach((t, i) => {
    const c = document.createElement("span"); c.className = "chip"; c.innerHTML = esc(t) + '<button title="حذف">✕</button>';
    c.querySelector("button").onclick = () => { times.splice(i, 1); dirty = true; renderTimes(); renderStats(); };
    box.appendChild(c);
  });
  if (!times.length) box.innerHTML = "<small>هیچ ساعتی تنظیم نشده؛ ربات خودکار چیزی نمی‌فرستد.</small>";
}
$("btnAddTime").onclick = () => {
  const v = $("newTime").value; if (!v) return;
  if (!cfg.schedule.times.includes(v)) cfg.schedule.times.push(v);
  dirty = true; renderTimes(); renderStats();
};
$("btnClearTimes").onclick = () => { cfg.schedule.times = []; dirty = true; renderTimes(); renderStats(); };
$("btnGen").onclick = () => {
  const toMin = (s) => { const [h, m] = s.split(":").map(Number); return h * 60 + m; };
  const a = toMin($("genFrom").value || "09:00"), b = toMin($("genTo").value || "21:00"), step = Math.max(10, Number($("genStep").value) || 60);
  if (b < a) return toast("ساعت پایان باید بعد از شروع باشد", "err");
  const out = []; for (let m = a; m <= b; m += step) out.push(String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0"));
  if (out.length > 48) return toast("بیشتر از ۴۸ پست در روز مجاز نیست", "err");
  cfg.schedule.times = out; dirty = true; renderTimes(); renderStats();
};
function renderDays() {
  const sel = new Set((cfg.schedule.days || []).map(String)); const all = !sel.size;
  $("days").innerHTML = '<label><input type="checkbox" id="dAll" ' + (all ? "checked" : "") + "> همه‌ی روزها</label>" +
    DAYS.map(([v, n]) => '<label><input type="checkbox" data-d="' + v + '" ' + (all || sel.has(v) ? "checked" : "") + (all ? " disabled" : "") + "> " + n + "</label>").join("");
  const upd = () => {
    if ($("dAll").checked) cfg.schedule.days = [];
    else cfg.schedule.days = [...document.querySelectorAll("[data-d]")].filter((x) => x.checked).map((x) => Number(x.dataset.d));
    dirty = true;
  };
  $("dAll").onchange = () => { document.querySelectorAll("[data-d]").forEach((x) => { x.disabled = $("dAll").checked; x.checked = $("dAll").checked || x.checked; }); upd(); };
  document.querySelectorAll("[data-d]").forEach((x) => (x.onchange = upd));
  $("grace").value = cfg.schedule.grace_minutes ?? 60; $("skipUnchanged").checked = cfg.schedule.skip_unchanged !== false;
}
$("grace").oninput = () => { cfg.schedule.grace_minutes = Math.min(240, Math.max(10, Number($("grace").value) || 60)); dirty = true; };
$("skipUnchanged").onchange = () => { cfg.schedule.skip_unchanged = $("skipUnchanged").checked; dirty = true; };
$("enabled").onchange = () => { cfg.enabled = $("enabled").checked; dirty = true; };

function renderCaption() { $("caption").value = cfg.caption || ""; }
$("caption").oninput = () => { cfg.caption = $("caption").value; dirty = true; };
function renderLog() {
  const rows = state.log || [];
  $("log").innerHTML = rows.length
    ? rows.map((l) => "<tr><td>" + esc(fmtDate(l.at)) + '</td><td><span class="pill ' + esc(l.status) + '">' + esc(STATUS_FA[l.status] || l.status) + "</span></td><td>" + esc(l.message) + "</td></tr>").join("")
    : '<tr><td colspan="3"><small>هنوز اجرایی ثبت نشده.</small></td></tr>';
}

function validate() {
  for (const slot of cfg.slots) {
    const s = slot.source || {};
    if (!(Number(s.divisor) > 0)) return "«تقسیم بر» باید بزرگ‌تر از صفر باشد (" + slot.label + ")";
    if (s.type === "css") {
      if (!/^https:\/\//i.test(s.url || "")) return "آدرس باید با https:// شروع شود (" + slot.label + ")";
      if (!String(s.selector || "").trim()) return "سلکتور خالی است (" + slot.label + ")";
    } else if (!s.slug) return "آیتم TGJU انتخاب نشده (" + slot.label + ")";
  }
  return "";
}$("btnSave").onclick = async () => {
  const err = validate(); if (err) return toast(err, "err");
  $("btnSave").disabled = true;
  try {
    const res = await gh("/contents/config.json", { method: "PUT", body: JSON.stringify({
      message: "panel: update settings", content: b64enc(JSON.stringify(cfg, null, 2) + "\n"), sha: shas["config.json"], branch: await branch() }) });
    shas["config.json"] = res.content.sha; dirty = false; toast("ذخیره شد. از اجرای بعدی ربات اعمال می‌شود.");
  } catch (e) { toast(e.message + " — اگر کسی همزمان تغییر داده «بارگذاری دوباره» را بزن.", "err"); }
  $("btnSave").disabled = false;
};
$("btnReload").onclick = async () => {
  if (dirty && !confirm("تغییرات ذخیره‌نشده از بین می‌رود. ادامه؟")) return;
  try { await loadAll(); toast("بارگذاری شد"); } catch (e) { toast(e.message, "err"); }
};
$("btnNow").onclick = async () => {
  if (dirty) return toast("اول تنظیمات را ذخیره کن، بعد ارسال کن", "err");
  if (!confirm("همین حالا قیمت‌ها در کانال پست شود؟")) return;
  $("btnNow").disabled = true;
  try {
    await gh("/actions/workflows/" + WORKFLOW + "/dispatches", { method: "POST", body: JSON.stringify({ ref: await branch(), inputs: { force: "true" } }) });
    toast("دستور ارسال شد. تا ۲ دقیقه دیگر در کانال است.");
  } catch (e) { toast(e.message, "err"); }
  setTimeout(() => ($("btnNow").disabled = false), 15000);
};

async function connect() {
  repo = $("repo").value.trim().replace(/^https?:\/\/github\.com\//i, "").replace(/\.git$/, "").replace(/\/$/, "");
  token = $("token").value.trim();
  if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) return toast("آدرس مخزن را به شکل username/price-bot بنویس", "err");
  if (!token) return toast("توکن را وارد کن", "err");
  $("btnConnect").disabled = true;
  try {
    _branch = ""; await loadAll();
    store("pb_repo", repo); store("pb_token", token);
    $("app").classList.remove("hide"); $("btnLogout").classList.remove("hide"); $("connect").querySelector(".grid").classList.add("hide");
    $("btnConnect").classList.add("hide"); toast("وصل شد");
  } catch (e) { toast(e.message, "err"); }
  $("btnConnect").disabled = false;
}
$("btnConnect").onclick = connect;
$("btnLogout").onclick = () => { store("pb_token", null); location.reload(); };
window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

(function init() {
  $("repo").value = recall("pb_repo");
  const m = location.hostname.match(/^([\w-]+)\.github\.io$/i), p = location.pathname.split("/")[1];
  if (!$("repo").value && m && p) $("repo").value = m[1] + "/" + p;
  const t = recall("pb_token"); if (t) { $("token").value = t; if ($("repo").value) connect(); }
})();
