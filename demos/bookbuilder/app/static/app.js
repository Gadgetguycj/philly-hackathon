"use strict";

const el = (id) => document.getElementById(id);
const form = el("form");
const reader = el("reader");
const statusLine = el("status");
const errorBox = el("error");
const stats = el("stats");
const stopButton = el("stop");
const finishBox = el("finish");

let source = null;
let runId = null;
let startedAt = 0;
let ticker = null;
let totalPages = 0;
let doneWords = 0;
let liveWords = 0;
let current = null;
let currentText = "";
let finished = false;

function setStatus(text, still) {
  statusLine.hidden = !text;
  statusLine.textContent = text || "";
  statusLine.classList.toggle("still", Boolean(still));
}

function showError(message, raw) {
  errorBox.hidden = false;
  errorBox.textContent = "";
  const line = document.createElement("div");
  line.textContent = message;
  errorBox.appendChild(line);
  if (raw) {
    const block = document.createElement("pre");
    block.textContent = raw;
    errorBox.appendChild(block);
  }
}

function countWords(text) {
  let count = 0;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === " " || ch === "\n" || ch === "\t") count += 1;
  }
  return count;
}

function paintStats() {
  const seconds = (performance.now() - startedAt) / 1000;
  el("statTime").textContent = seconds.toFixed(1) + " s";
  const words = doneWords + liveWords;
  const rate = seconds > 0.2 ? words / seconds : 0;
  el("statRate").textContent = rate.toFixed(0) + " words per second";
}

function atBottom() {
  return window.innerHeight + window.scrollY >= document.body.offsetHeight - 220;
}

function follow(wasAtBottom) {
  if (wasAtBottom) window.scrollTo(0, document.body.scrollHeight);
}

async function build(event) {
  event.preventDefault();
  const idea = el("idea").value.trim();
  if (!idea) return;
  el("build").disabled = true;
  errorBox.hidden = true;
  finishBox.hidden = true;
  reader.textContent = "";
  el("outlineList").textContent = "";
  el("outlineBox").hidden = true;
  doneWords = 0;
  liveWords = 0;
  current = null;
  currentText = "";
  finished = false;
  setStatus("Asking the model for an outline");

  let payload;
  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idea: idea,
        title: el("title").value.trim(),
        pages: Number(el("pages").value),
      }),
    });
    payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The server refused the request.");
  } catch (error) {
    el("build").disabled = false;
    setStatus("", true);
    showError(String(error.message || error));
    return;
  }

  runId = payload.run_id;
  totalPages = payload.pages;
  startedAt = performance.now();
  stats.hidden = false;
  stopButton.hidden = false;
  el("statPages").textContent = "0 of " + totalPages + " pages";
  paintStats();
  ticker = setInterval(paintStats, 100);
  listen();
}

function listen() {
  source = new EventSource("/api/runs/" + runId + "/events");
  source.addEventListener("status", (event) => {
    const data = JSON.parse(event.data);
    setStatus(data.message);
  });
  source.addEventListener("outline", (event) => {
    const data = JSON.parse(event.data);
    el("bookTitle").textContent = data.title;
    document.title = data.title + " | Bookbuilder";
    const list = el("outlineList");
    list.textContent = "";
    data.chapters.forEach((chapter) => {
      const item = document.createElement("li");
      const name = document.createElement("b");
      name.textContent = chapter.title;
      item.appendChild(name);
      item.appendChild(
        document.createTextNode(
          " (pages " + chapter.first_page + " to " + chapter.last_page + "). " + chapter.summary
        )
      );
      list.appendChild(item);
    });
    el("outlineSummary").textContent = "Outline: " + data.chapters.length + " chapters, " + data.pages + " pages";
    el("outlineBox").hidden = false;
    totalPages = data.pages;
  });
  source.addEventListener("page_start", (event) => {
    const data = JSON.parse(event.data);
    const wasAtBottom = atBottom();
    if (data.chapter_title && !document.getElementById("c" + data.chapter)) {
      const heading = document.createElement("h2");
      heading.className = "chapter";
      heading.id = "c" + data.chapter;
      heading.textContent = data.chapter + ". " + data.chapter_title;
      reader.appendChild(heading);
    }
    const article = document.createElement("article");
    article.className = "page live";
    article.id = "p" + data.index;
    const label = document.createElement("div");
    label.className = "page-no";
    label.textContent = "Page " + data.index;
    const body = document.createElement("p");
    body.className = "body";
    article.appendChild(label);
    article.appendChild(body);
    reader.appendChild(article);
    current = body;
    currentText = "";
    liveWords = 0;
    follow(wasAtBottom);
  });
  source.addEventListener("delta", (event) => {
    const data = JSON.parse(event.data);
    if (!current) return;
    const wasAtBottom = atBottom();
    currentText += data.text;
    current.textContent = currentText;
    liveWords = countWords(currentText);
    follow(wasAtBottom);
  });
  source.addEventListener("page_done", (event) => {
    const data = JSON.parse(event.data);
    const article = document.getElementById("p" + data.index);
    if (article) {
      article.classList.remove("live");
      const label = article.querySelector(".page-no");
      const seconds = (data.elapsed_ms / 1000).toFixed(1);
      label.textContent = "Page " + data.index + " of " + data.total;
      const facts = document.createElement("span");
      facts.className = "truncated";
      facts.textContent = data.words + " words in " + seconds + " s" + (data.truncated ? ", cut at the token limit" : "");
      label.appendChild(facts);
    }
    doneWords = data.total_words;
    liveWords = 0;
    current = null;
    el("statPages").textContent = data.index + " of " + data.total + " pages";
    paintStats();
  });
  source.addEventListener("page_dropped", (event) => {
    const data = JSON.parse(event.data);
    const article = document.getElementById("p" + data.index);
    if (article) article.remove();
    current = null;
    liveWords = 0;
  });
  // The stream names its own failure event "failed" because EventSource already uses
  // "error" for a dropped connection.
  source.addEventListener("failed", (event) => {
    const data = JSON.parse(event.data);
    showError(data.message, data.raw);
    setStatus("", true);
  });
  source.addEventListener("done", (event) => {
    finished = true;
    const data = JSON.parse(event.data);
    close();
    doneWords = data.words;
    liveWords = 0;
    paintStats();
    el("statPages").textContent = data.pages + " of " + data.pages_requested + " pages";
    setStatus("", true);
    statusLine.hidden = true;
    finishBox.hidden = false;
    finishBox.textContent = "";
    const heading = document.createElement("h2");
    heading.textContent = data.stopped ? "Stopped after " + data.pages + " pages" : "Done. " + data.pages + " pages.";
    finishBox.appendChild(heading);
    const facts = document.createElement("p");
    facts.className = "facts";
    facts.textContent =
      data.words + " words in " + data.seconds + " seconds, " + data.words_per_second + " words per second.";
    finishBox.appendChild(facts);
    if (data.url) {
      const link = document.createElement("a");
      link.className = "share";
      link.href = data.url;
      link.textContent = window.location.origin + data.url;
      finishBox.appendChild(link);
      const note = document.createElement("p");
      note.className = "facts";
      note.textContent = "That address is the book. Share it.";
      finishBox.appendChild(note);
    }
  });
  source.onerror = () => {
    if (finished) return;
    setStatus("The connection dropped. Picking the stream back up.");
  };
}

function close() {
  if (source) source.close();
  source = null;
  if (ticker) clearInterval(ticker);
  ticker = null;
  stopButton.hidden = true;
  el("build").disabled = false;
}

stopButton.addEventListener("click", async () => {
  stopButton.disabled = true;
  setStatus("Stopping. The pages that finished are kept.");
  try {
    await fetch("/api/runs/" + runId + "/stop", { method: "POST" });
  } catch (error) {
    showError("Could not reach the server to stop the run.");
  }
  stopButton.disabled = false;
});

form.addEventListener("submit", build);

fetch("/api/config")
  .then((response) => response.json())
  .then((data) => {
    const select = el("pages");
    data.page_choices.forEach((count) => {
      const option = document.createElement("option");
      option.value = String(count);
      option.textContent = String(count);
      option.selected = count === data.default_pages;
      select.appendChild(option);
    });
    el("modelLine").textContent = "Model: " + data.model;
    el("keyWarning").hidden = data.runpod_key_set;
  })
  .catch(() => {
    showError("The page could not read its own settings from the server.");
  });
