"use strict";

const form = document.getElementById("predict-form");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const submitBtn = document.getElementById("submit-btn");

const pct = (x) => `${Math.round(x * 100)}%`;
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// 국가 자동완성 목록 로드
async function loadTeams() {
  try {
    const res = await fetch("/api/teams");
    if (!res.ok) return;
    const teams = await res.json();
    const dl = document.getElementById("teams");
    dl.innerHTML = teams.map((t) => `<option value="${esc(t.name)}">`).join("");
  } catch (_) {
    /* 자동완성은 선택 기능 — 실패해도 무시 */
  }
}

function showStatus(msg, kind = "error") {
  statusEl.className = `status ${kind === "info" ? "info" : ""}`;
  statusEl.textContent = msg;
  statusEl.hidden = false;
}

function renderResult(d) {
  const a = d.teams.a.name;
  const b = d.teams.b.name;
  const w = d.winner;
  const winnerLine = w.key
    ? `🏆 <strong>${esc(w.name)}</strong> 승리 예상 (${pct(w.confidence)})`
    : `🤝 무승부 가능성이 가장 높습니다 (${pct(w.confidence)})`;

  const scorerList = (arr) =>
    arr.length
      ? arr.map((s) => `<li><span>${esc(s.name)}</span><span class="pct">${pct(s.p)}</span></li>`).join("")
      : `<li class="pct">정보 없음</li>`;

  const warnings = (d.meta.warnings || []);
  const warnHtml = warnings.length
    ? `<div class="warn">⚠ ${warnings.map(esc).join(" · ")}</div>`
    : "";

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
    <div class="meta">
      엔진: ${esc(d.meta.augmenter || "-")} · λ ${d.meta.lambda ? `${d.meta.lambda.a} / ${d.meta.lambda.b}` : "-"}
      ${warnHtml}
    </div>
  `;
  resultEl.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const a = document.getElementById("team-a").value.trim();
  const b = document.getElementById("team-b").value.trim();
  if (!a || !b) return;

  statusEl.hidden = true;
  resultEl.hidden = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "예측 중…";

  try {
    const res = await fetch(`/api/predict?team_a=${encodeURIComponent(a)}&team_b=${encodeURIComponent(b)}`);
    const data = await res.json();
    if (!res.ok) {
      const det = data.detail;
      if (det && det.candidates && det.candidates.length) {
        const names = det.candidates.map((c) => c.name).join(", ");
        showStatus(`'${det.query}' 을(를) 찾지 못했습니다. 혹시: ${names}?`);
      } else {
        showStatus(typeof det === "string" ? det : "예측에 실패했습니다.");
      }
      return;
    }
    renderResult(data);
  } catch (_) {
    showStatus("서버에 연결할 수 없습니다.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "예측하기";
  }
});

loadTeams();
