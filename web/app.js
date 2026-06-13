"use strict";

const pct = (x) => `${Math.round(x * 100)}%`;
const pct1 = (x) => `${(x * 100).toFixed(1)}%`;
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ---- 탭 전환 ----
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.dataset.tab;
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.hidden = p.id !== `tab-${target}`;
    });
  });
});

function setStatus(el, msg, kind = "error") {
  el.className = `status ${kind === "info" ? "info" : ""}`;
  el.textContent = msg;
  el.hidden = false;
}

// 모호 국가명 → 후보 메시지 공통 처리
function describeError(data) {
  const det = data.detail;
  if (det && det.candidates && det.candidates.length) {
    return `'${det.query}' 을(를) 찾지 못했습니다. 혹시: ${det.candidates.map((c) => c.name).join(", ")}?`;
  }
  if (det && det.query) return `'${det.query}' 을(를) 찾지 못했습니다.`;
  if (det && det.detail) return det.detail;
  return typeof det === "string" ? det : "요청에 실패했습니다.";
}

// ---- 국가 자동완성 ----
async function loadTeams() {
  try {
    const res = await fetch("/api/teams");
    if (!res.ok) return;
    const teams = await res.json();
    document.getElementById("teams").innerHTML =
      teams.map((t) => `<option value="${esc(t.name)}">`).join("");
  } catch (_) { /* 자동완성 실패 무시 */ }
}

// ---- 경기 예측 ----
const matchForm = document.getElementById("predict-form");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const submitBtn = document.getElementById("submit-btn");

function renderMatch(d) {
  const a = d.teams.a.name, b = d.teams.b.name, w = d.winner;
  const winnerLine = w.key
    ? `🏆 <strong>${esc(w.name)}</strong> 승리 예상 (${pct(w.confidence)})`
    : `🤝 무승부 가능성이 가장 높습니다 (${pct(w.confidence)})`;
  const scorerList = (arr) =>
    arr.length
      ? arr.map((s) => `<li><span>${esc(s.name)}</span><span class="pct">${pct(s.p)}</span></li>`).join("")
      : `<li class="pct">정보 없음</li>`;
  const warnings = d.meta.warnings || [];
  const warnHtml = warnings.length ? `<div class="warn">⚠ ${warnings.map(esc).join(" · ")}</div>` : "";

  resultEl.innerHTML = `
    <div class="winner-line">${winnerLine}</div>
    <div class="scoreline"><span class="pa">${d.scoreline.a}</span> : <span class="pb">${d.scoreline.b}</span></div>
    <div class="score-prob">${esc(a)} ${d.scoreline.a} - ${d.scoreline.b} ${esc(b)} · 최빈 스코어 (${pct(d.scoreline.prob)})</div>
    <div class="wdl-bar">
      <div class="seg seg-a" style="width:${d.wdl.a_win * 100}%">${pct(d.wdl.a_win)}</div>
      <div class="seg seg-d" style="width:${d.wdl.draw * 100}%">${pct(d.wdl.draw)}</div>
      <div class="seg seg-b" style="width:${d.wdl.b_win * 100}%">${pct(d.wdl.b_win)}</div>
    </div>
    <div class="wdl-legend"><span>${esc(a)} 승</span><span>무</span><span>${esc(b)} 승</span></div>
    <div class="scorers">
      <div class="col a"><h3>${esc(a)} 득점 후보</h3><ul>${scorerList(d.scorers.a)}</ul></div>
      <div class="col b"><h3>${esc(b)} 득점 후보</h3><ul>${scorerList(d.scorers.b)}</ul></div>
    </div>
    <div class="explanation">${esc(d.explanation)}</div>
    <div class="meta">엔진: ${esc(d.meta.augmenter || "-")} · λ ${d.meta.lambda ? `${d.meta.lambda.a} / ${d.meta.lambda.b}` : "-"}${warnHtml}</div>
  `;
  resultEl.hidden = false;
}

matchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const a = document.getElementById("team-a").value.trim();
  const b = document.getElementById("team-b").value.trim();
  if (!a || !b) return;
  statusEl.hidden = true; resultEl.hidden = true;
  submitBtn.disabled = true; submitBtn.textContent = "예측 중…";
  try {
    const res = await fetch(`/api/predict?team_a=${encodeURIComponent(a)}&team_b=${encodeURIComponent(b)}`);
    const data = await res.json();
    if (!res.ok) { setStatus(statusEl, describeError(data)); return; }
    renderMatch(data);
  } catch (_) {
    setStatus(statusEl, "서버에 연결할 수 없습니다.");
  } finally {
    submitBtn.disabled = false; submitBtn.textContent = "예측하기";
  }
});

// ---- 토너먼트 ----
const tForm = document.getElementById("tournament-form");
const tStatusEl = document.getElementById("t-status");
const tResultEl = document.getElementById("t-result");
const tBtn = document.getElementById("tournament-btn");

function renderTournament(list) {
  const max = Math.max(...list.map((x) => x.prob), 0.0001);
  const medals = ["🥇", "🥈", "🥉"];
  const rows = list
    .map((x, i) => `
      <li class="champ-row">
        <span class="champ-rank">${medals[i] || i + 1}</span>
        <span class="champ-name">${esc(x.name)}</span>
        <span class="champ-bar"><span class="champ-fill" style="width:${(x.prob / max) * 100}%"></span></span>
        <span class="champ-pct">${pct1(x.prob)}</span>
      </li>`)
    .join("");
  tResultEl.innerHTML = `<h3 class="champ-title">우승 확률</h3><ul class="champ-list">${rows}</ul>`;
  tResultEl.hidden = false;
}

tForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const raw = document.getElementById("tournament-teams").value.trim();
  const names = raw.split(",").map((s) => s.trim()).filter(Boolean);
  tStatusEl.hidden = true; tResultEl.hidden = true;

  const n = names.length;
  if (n < 2 || (n & (n - 1)) !== 0) {
    setStatus(tStatusEl, `참가국 수는 2의 거듭제곱이어야 합니다 (2·4·8·16·32). 현재 ${n}개.`);
    return;
  }
  tBtn.disabled = true; tBtn.textContent = "계산 중…";
  try {
    const res = await fetch(`/api/tournament?teams=${encodeURIComponent(names.join(","))}`);
    const data = await res.json();
    if (!res.ok) { setStatus(tStatusEl, describeError(data)); return; }
    renderTournament(data);
  } catch (_) {
    setStatus(tStatusEl, "서버에 연결할 수 없습니다.");
  } finally {
    tBtn.disabled = false; tBtn.textContent = "우승 예측";
  }
});

loadTeams();
