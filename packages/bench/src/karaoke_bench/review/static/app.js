// Review page for timing references. No build step and no dependencies on purpose.
"use strict";

const STATUS_LABELS = { draft: "sen revisar", ok: "ben", wrong: "mal", unsure: "dubidosa" };
const NUDGE = 0.05;
const WINDOW = 6; // seconds shown on each side of the playhead

const audio = document.getElementById("audio");
const canvas = document.getElementById("wave");
const linesEl = document.getElementById("lines");
const currentEl = document.getElementById("current");
const buttons = {
  play: document.getElementById("play"),
  speed: document.getElementById("speed"),
  source: document.getElementById("source"),
  save: document.getElementById("save"),
  approve: document.getElementById("approve"),
};

let ref = null;
let peaks = null;
let song = null;
let selectedLine = 0;
let selectedWord = null; // [line, word]
let dirty = false;
const urls = {};
let source = "mix";

async function load() {
  [ref, song, peaks] = await Promise.all(
    ["/api/reference", "/api/song", "/api/peaks"].map((u) => fetch(u).then((r) => r.json())),
  );
  document.getElementById("title").textContent = song.artist
    ? `${song.title} · ${song.artist}`
    : song.title;
  buttons.source.hidden = !song.has_vocals;
  // Blob URLs let the audio element seek without HTTP range requests.
  urls.mix = URL.createObjectURL(await (await fetch("/audio/mix")).blob());
  if (song.has_vocals) {
    urls.vocals = URL.createObjectURL(await (await fetch("/audio/vocals")).blob());
  }
  audio.src = urls.mix;
  renderLines();
  requestAnimationFrame(tick);
}

function fmt(t) {
  const m = Math.floor(t / 60);
  return `${m}:${(t - 60 * m).toFixed(2).padStart(5, "0")}`;
}

function renderLines() {
  linesEl.replaceChildren(
    ...ref.lines.map((line, i) => {
      const li = document.createElement("li");
      li.className = [line.status, line.revised ? "revised" : "", i === selectedLine ? "selected" : ""]
        .filter(Boolean)
        .join(" ");
      li.innerHTML =
        `<span class="num">${i + 1}</span><span class="start">${fmt(line.anchor ?? line.start)}</span>` +
        `<span class="state">${STATUS_LABELS[line.status]}</span><span><span class="text"></span>` +
        `<span class="note"></span></span>`;
      li.querySelector(".text").textContent = line.text;
      li.querySelector(".note").textContent = line.note ?? "";
      li.addEventListener("click", () => selectLine(i, true));
      li.querySelector(".text").addEventListener("dblclick", (e) => editText(i, e.target));
      return li;
    }),
  );
  updateSummary();
}

function updateSummary() {
  const counts = { draft: 0, ok: 0, wrong: 0, unsure: 0 };
  ref.lines.forEach((l) => counts[l.status]++);
  document.getElementById("summary").textContent =
    `${ref.lines.length} liñas: ${counts.ok} ben, ${counts.wrong} mal, ${counts.unsure} dubidosas, ` +
    `${counts.draft} sen revisar` + (ref.approved ? " · validada ✔" : "");
  buttons.approve.disabled = counts.draft > 0 || counts.wrong > 0 || ref.approved;
  buttons.save.classList.toggle("dirty", dirty);
  buttons.save.textContent = dirty ? "Gardar *" : "Gardar";
}

function selectLine(i, play) {
  selectedLine = i;
  selectedWord = null;
  [...linesEl.children].forEach((li, k) => li.classList.toggle("selected", k === i));
  if (play) {
    const line = ref.lines[i];
    audio.currentTime = Math.max(0, (line.anchor ?? line.start) - 1);
    audio.play();
  }
}

function lineAt(t) {
  let found = 0;
  ref.lines.forEach((line, i) => {
    if ((line.anchor ?? line.start) - 0.3 <= t) found = i;
  });
  return found;
}

function renderCurrent(t, index) {
  const line = ref.lines[index];
  currentEl.replaceChildren(
    ...line.words.map((word, w) => {
      const span = document.createElement("span");
      span.className = "word";
      if (word.start <= t) span.classList.add("sung");
      if (selectedWord && selectedWord[0] === index && selectedWord[1] === w) {
        span.classList.add("selected");
      }
      span.textContent = word.text + " ";
      span.addEventListener("click", () => {
        selectedWord = [index, w];
        selectedLine = index;
      });
      return span;
    }),
  );
  if (!line.words.length) currentEl.textContent = line.text;
}

function drawWave(t) {
  const ctx = canvas.getContext("2d");
  const width = (canvas.width = canvas.clientWidth * devicePixelRatio);
  const height = (canvas.height = 120 * devicePixelRatio);
  const x = (s) => ((s - (t - WINDOW)) / (2 * WINDOW)) * width;
  ctx.clearRect(0, 0, width, height);
  ref.lines.forEach((line, li) => {
    line.words.forEach((word, wi) => {
      if (word.end < t - WINDOW || word.start > t + WINDOW) return;
      const chosen = selectedWord && selectedWord[0] === li && selectedWord[1] === wi;
      ctx.fillStyle = chosen ? "rgba(110,168,254,.35)" : "rgba(242,177,52,.18)";
      ctx.fillRect(x(word.start), 0, Math.max(2, x(word.end) - x(word.start)), height);
      ctx.fillStyle = "#e8e6e3";
      ctx.font = `${12 * devicePixelRatio}px system-ui`;
      ctx.fillText(word.text, x(word.start) + 3, 14 * devicePixelRatio);
    });
    if (line.anchor != null) {
      ctx.fillStyle = "#6ea8fe";
      ctx.fillRect(x(line.anchor), 0, 2 * devicePixelRatio, height);
    }
  });
  ctx.fillStyle = "#9aa0a6";
  const mid = height / 2;
  for (let px = 0; px < width; px += devicePixelRatio) {
    const i = Math.floor((t - WINDOW + (px / width) * 2 * WINDOW) * peaks.rate);
    if (i < 0 || i >= peaks.min.length) continue;
    ctx.fillRect(px, mid - peaks.max[i] * mid, devicePixelRatio, (peaks.max[i] - peaks.min[i]) * mid || 1);
  }
  ctx.fillStyle = "#f2b134";
  ctx.fillRect(width / 2 - devicePixelRatio, 0, 2 * devicePixelRatio, height);
}

function tick() {
  const t = audio.currentTime;
  const index = lineAt(t);
  document.getElementById("time").textContent = fmt(t);
  [...linesEl.children].forEach((li, k) => li.classList.toggle("playing", k === index));
  renderCurrent(t, selectedWord ? selectedWord[0] : index);
  drawWave(t);
  buttons.play.textContent = audio.paused ? "▶ Reproducir" : "⏸ Parar";
  requestAnimationFrame(tick);
}

function changed(i) {
  dirty = true;
  ref.approved = false;
  renderLines();
  selectLine(i, false);
}

function setStatus(i, status) {
  const line = ref.lines[i];
  line.status = status;
  if (status === "wrong") {
    const note = prompt("Que falla nesta liña?", line.note ?? "");
    line.note = note || null;
  } else if (status === "ok") {
    line.revised = false;
  }
  changed(i);
}

function editText(i, el) {
  el.contentEditable = "true";
  el.focus();
  el.addEventListener(
    "blur",
    () => {
      el.contentEditable = "false";
      const text = el.textContent.trim();
      if (text && text !== ref.lines[i].text) {
        ref.lines[i].text = text;
        ref.lines[i].status = "wrong";
        ref.lines[i].note = (ref.lines[i].note ? ref.lines[i].note + " · " : "") + "texto corrixido";
        changed(i);
      }
    },
    { once: true },
  );
}

function nudge(delta, end) {
  if (!selectedWord) return;
  const [li, wi] = selectedWord;
  const word = ref.lines[li].words[wi];
  if (end) word.end = Math.max(word.start, +(word.end + delta).toFixed(3));
  else word.start = Math.min(word.end, Math.max(0, +(word.start + delta).toFixed(3)));
  const line = ref.lines[li];
  line.start = Math.min(...line.words.map((w) => w.start));
  line.end = Math.max(...line.words.map((w) => w.end));
  changed(li);
  selectedWord = [li, wi];
}

async function save() {
  const response = await fetch("/api/reference", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ref),
  });
  if (response.ok) {
    dirty = false;
    updateSummary();
  } else {
    alert("Non se puido gardar:\n" + (await response.text()));
  }
}

buttons.play.addEventListener("click", () => (audio.paused ? audio.play() : audio.pause()));
buttons.speed.addEventListener("click", toggleSpeed);
buttons.source.addEventListener("click", toggleSource);
buttons.save.addEventListener("click", save);
buttons.approve.addEventListener("click", () => {
  ref.approved = true;
  dirty = true;
  save();
});
canvas.addEventListener("click", (e) => {
  const rect = canvas.getBoundingClientRect();
  audio.currentTime = Math.max(0, audio.currentTime + ((e.clientX - rect.left) / rect.width - 0.5) * 2 * WINDOW);
});

function toggleSpeed() {
  audio.playbackRate = audio.playbackRate === 1 ? 0.75 : 1;
  buttons.speed.textContent = `Velocidade ${audio.playbackRate === 1 ? "1" : "0,75"}×`;
}

function toggleSource() {
  if (!urls.vocals) return;
  const t = audio.currentTime;
  const playing = !audio.paused;
  source = source === "mix" ? "vocals" : "mix";
  audio.src = urls[source];
  audio.currentTime = t;
  if (playing) audio.play();
  buttons.source.textContent = `Escoitando: ${source === "mix" ? "mestura" : "só a voz"}`;
}

document.addEventListener("keydown", (e) => {
  if (e.target.isContentEditable) return;
  if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    save();
  } else if (e.key === " ") {
    e.preventDefault();
    audio.paused ? audio.play() : audio.pause();
  } else if (e.key === "1") setStatus(selectedLine, "ok");
  else if (e.key === "2") setStatus(selectedLine, "wrong");
  else if (e.key === "3") setStatus(selectedLine, "unsure");
  else if (e.key === "a" || e.key === "A") {
    // An anchor means "this line starts here": the line gets realigned from that point.
    ref.lines[selectedLine].anchor = +audio.currentTime.toFixed(3);
    ref.lines[selectedLine].status = "wrong";
    changed(selectedLine);
  } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    e.preventDefault();
    nudge(e.key === "ArrowLeft" ? -NUDGE : NUDGE, e.shiftKey);
  } else if (e.key === "v" || e.key === "V") toggleSpeed();
  else if (e.key === "m" || e.key === "M") toggleSource();
});

window.addEventListener("beforeunload", (e) => {
  if (dirty) e.preventDefault();
});

load();
