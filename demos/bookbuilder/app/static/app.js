"use strict";

const el = (id) => document.getElementById(id);
const form = el("form");
const desk = el("desk");
const book = el("book");
const leafLeft = el("leafLeft");
const leafRight = el("leafRight");
const turner = el("turner");
const turnFront = el("turnFront");
const turnBack = el("turnBack");
const setup = el("setup");
const statusLine = el("status");
const errorBox = el("error");
const stats = el("stats");
const stopButton = el("stop");
const finishBox = el("finish");
const prevButton = el("prev");
const nextButton = el("next");
const toLive = el("toLive");
const whereLabel = el("whereLabel");

// The smallest the page type may get before the paper is simply too small for the words.
const FIT_FLOOR = 0.42;

const state = {
  title: "",
  model: "",
  idea: "",
  total: 0,
  pages: new Map(), // index -> {index, chapter, chapterTitle, opens, text, words, done}
  order: [], // every page index the stream started, in the order it started them
  live: 0, // the page being written. 0 before the first page
  highest: 0, // the highest page that exists
  view: 0, // the page on the right hand leaf. 0 is the title page
  following: true,
  finished: false,
};
// A read only handle, so a browser test can check the order the pages arrived in.
window.bookbuilder = state;

let source = null;
let runId = null;
let startedAt = 0;
let penAt = 0; // when the first token of the book arrived. 0 while the model is waking
let ticker = null;
let doneWords = 0;
let liveWords = 0;

// The live page is written into the DOM through these, one text node at a time.
const writer = { mounted: 0, paper: null, text: null, node: null, caret: null, hold: "", fresh: true };
let pending = "";
let frame = 0;

// ---------------------------------------------------------------- the header

// A cold endpoint can take minutes to answer. Until the first token there is nothing
// being written, and these two messages would read as if there were. Anything else the
// run has to say, a retry or a stop, is shown as it was sent.
const ROUTINE = /^(Planning the chapters|Writing page \d+)$/;
let statusText = "";
let statusStill = false;

function setStatus(text, still) {
  statusText = text || "";
  statusStill = Boolean(still);
  renderStatus();
}

function renderStatus() {
  const text = !penAt && ROUTINE.test(statusText) ? "Waking the model" : statusText;
  statusLine.hidden = !text;
  statusLine.textContent = text;
  statusLine.classList.toggle("still", statusStill);
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
  const now = performance.now();
  el("statTime").textContent = ((now - startedAt) / 1000).toFixed(1) + " s";
  const words = doneWords + liveWords;
  // Words per second is the writing speed, so its clock starts at the first token. A two
  // minute wake belongs in the elapsed time, not in the rate.
  const writing = penAt ? (now - penAt) / 1000 : 0;
  const rate = writing > 0.2 ? words / writing : 0;
  el("statRate").textContent = rate.toFixed(0);
}

// ------------------------------------------------------------ drawing a page

function paperFor(index) {
  if (index < 0) return null;
  if (index === 0) return titlePaper();

  const page = state.pages.get(index);
  const paper = document.createElement("div");
  paper.className = "paper";
  paper.dataset.page = String(index);

  const head = document.createElement("div");
  head.className = "runhead";
  head.textContent = page && page.chapterTitle ? page.chapterTitle : state.title;
  paper.appendChild(head);

  const text = document.createElement("div");
  text.className = "text";
  if (page && page.opens) {
    const opener = document.createElement("div");
    opener.className = "opener";
    const number = document.createElement("span");
    number.className = "chapter-no";
    number.textContent = "Chapter " + page.chapter;
    const name = document.createElement("span");
    name.className = "chapter-name";
    name.textContent = page.chapterTitle || "";
    opener.appendChild(number);
    opener.appendChild(name);
    text.appendChild(opener);
  }
  if (page) fillText(text, page.text);
  paper.appendChild(text);

  const folio = document.createElement("div");
  folio.className = "folio";
  folio.textContent = String(index);
  if (page && page.truncated) {
    const cut = document.createElement("span");
    cut.className = "cut";
    cut.textContent = "cut at the token limit";
    folio.appendChild(cut);
  }
  paper.appendChild(folio);
  return paper;
}

function titlePaper() {
  const paper = document.createElement("div");
  paper.className = "paper title-page";
  paper.dataset.page = "0";
  const wrap = document.createElement("div");
  wrap.className = "title-block";
  const name = document.createElement("h2");
  name.textContent = state.title || "Untitled";
  wrap.appendChild(name);
  const rule = document.createElement("div");
  rule.className = "rule";
  wrap.appendChild(rule);
  if (state.idea) {
    const idea = document.createElement("p");
    idea.className = "title-idea";
    idea.textContent = state.idea;
    wrap.appendChild(idea);
  }
  const imprint = document.createElement("p");
  imprint.className = "imprint";
  imprint.textContent = state.total
    ? state.total + " pages, written by " + state.model
    : "Written by " + state.model;
  wrap.appendChild(imprint);
  paper.appendChild(wrap);
  return paper;
}

// Split the raw page text into paragraphs. Used for a page that is already written.
function fillText(textEl, raw) {
  const blocks = String(raw || "").split(/\n{2,}/);
  blocks.forEach((block) => {
    const clean = block.replace(/\n/g, " ").trim();
    if (!clean) return;
    const para = document.createElement("p");
    para.textContent = clean;
    textEl.appendChild(para);
  });
}

function paint(container, index) {
  container.textContent = "";
  const paper = paperFor(index);
  container.classList.toggle("empty", !paper);
  if (paper) {
    container.appendChild(paper);
    refit();
  }
}

// A printed page never clips, so the type is sized to the longest page the book has.
// The size is set on the whole book, because two facing pages printed at different sizes
// do not read as one book, and it only ever goes down within a run.
let fit = 1;

function setFit(value) {
  fit = Math.max(FIT_FLOOR, Math.min(1, value));
  book.style.setProperty("--fit", String(fit));
}

// How much taller than its paper a page's text is. 1 or less means it fits.
function spill(paper) {
  const text = paper.querySelector(".text");
  if (!text || !text.clientHeight) return 1;
  return text.scrollHeight / text.clientHeight;
}

function papersOnShow() {
  return [leafLeft, leafRight]
    .map((leaf) => leaf.querySelector(".paper"))
    .filter((paper) => paper && paper.offsetParent !== null);
}

// Halving the type quarters the height it needs, because the lines get shorter and more
// words fit on each one, so one square root lands within a percent and the loop is a
// safety net rather than a search.
function refit() {
  for (let pass = 0; pass < 6; pass += 1) {
    const worst = papersOnShow().reduce((most, paper) => Math.max(most, spill(paper)), 1);
    if (worst <= 1.002) break;
    const next = fit * Math.sqrt(1 / worst) * 0.995;
    if (next >= fit - 0.0005) break;
    setFit(next);
  }
  papersOnShow().forEach((paper) => paper.classList.toggle("more", spill(paper) > 1.002));
}

// ------------------------------------------------------- writing on the page

function mountLive() {
  unmount();
  const page = state.pages.get(state.live);
  if (!page || page.done || state.view !== state.live) return;
  // Draw everything that has arrived so far, so the pen carries on from the real end of
  // the page however the reader got here.
  paint(leafRight, state.live);
  const paper = leafRight.querySelector(".paper");
  if (!paper) return;
  paper.classList.add("writing");
  writer.paper = paper;
  writer.text = paper.querySelector(".text");
  writer.caret = document.createElement("span");
  writer.caret.className = "caret";
  const last = writer.text.querySelector("p:last-of-type");
  if (last) {
    writer.node = last.lastChild && last.lastChild.nodeType === 3 ? last.lastChild : last.appendChild(document.createTextNode(""));
    last.appendChild(writer.caret);
    writer.fresh = false;
  } else {
    newParagraph();
  }
  writer.mounted = state.live;
  writer.hold = "";
  pending = "";
  scrollToPen();
}

function unmount() {
  if (writer.caret && writer.caret.parentNode) writer.caret.parentNode.removeChild(writer.caret);
  if (writer.paper) writer.paper.classList.remove("writing");
  writer.mounted = 0;
  writer.paper = null;
  writer.text = null;
  writer.node = null;
  writer.caret = null;
  writer.hold = "";
  pending = "";
}

function newParagraph() {
  const para = document.createElement("p");
  writer.node = para.appendChild(document.createTextNode(""));
  para.appendChild(writer.caret);
  writer.text.appendChild(para);
  writer.fresh = true;
}

// Tokens arrive many times a second. They pile up here and land once a frame.
function queue(text) {
  pending += text;
  if (!frame) frame = requestAnimationFrame(flush);
}

function flush() {
  frame = 0;
  const chunk = pending;
  pending = "";
  if (!chunk || !writer.node) return;
  ink(chunk);
  // The page being written is measured too, so the type settles into the size the book
  // needs instead of the page hiding its first lines behind a scroll. Once the type is as
  // small as it may get, the page scrolls to keep the pen in view, and it is measured
  // again the moment it is finished.
  refit();
  scrollToPen();
}

function ink(chunk) {
  let text = writer.hold + chunk;
  writer.hold = "";
  const tail = text.match(/\n+$/);
  if (tail) {
    writer.hold = tail[0];
    text = text.slice(0, text.length - tail[0].length);
  }
  if (!text) return;
  const parts = text.split(/\n{2,}/);
  for (let i = 0; i < parts.length; i += 1) {
    if (i > 0) newParagraph();
    let part = parts[i].replace(/\n/g, " ");
    if (writer.fresh) {
      part = part.replace(/^\s+/, "");
      if (part) writer.fresh = false;
    }
    if (part) writer.node.appendData(part);
  }
}

function scrollToPen() {
  if (!writer.text) return;
  const over = writer.text.scrollHeight - writer.text.clientHeight;
  if (over > 0) writer.text.scrollTop = over;
}

// ------------------------------------------------------------- the page turn

let turning = null;
let turnTimer = 0;

function turnMs() {
  const value = parseFloat(getComputedStyle(book).getPropertyValue("--turn-ms"));
  return Number.isFinite(value) ? value : 620;
}

// The writer can finish later pages first, and they arrive in a burst once the page in
// front of them is done. The book riffles through them one at a time rather than jumping,
// and the further behind it is the faster it turns.
function catchUpMs(gap) {
  if (gap >= 6) return 150;
  if (gap >= 4) return 230;
  if (gap >= 2) return 380;
  return 0;
}

// While the book is following, it turns one page at a time towards the page being written.
function chase() {
  if (!state.following || turning) return;
  if (state.live > state.view) goTo(state.view + 1, true);
}

// auto is a turn the stream asked for. A turn the reader asked for also decides whether
// the book keeps following the page being written.
function goTo(index, auto) {
  if (turning) settle();
  const target = Math.max(0, Math.min(index, state.highest));
  if (!auto) state.following = target === state.live;
  if (target === state.view) {
    afterView();
    return;
  }
  const forward = target > state.view;
  unmount();
  const quick = auto ? catchUpMs(state.live - state.view) : 0;
  if (quick) book.style.setProperty("--turn-ms", quick + "ms");
  else book.style.removeProperty("--turn-ms");

  // Put the leaf where it lifts off from and show it, so the page it carries is measured
  // against the same paper it will be read on, and only then set it moving.
  turner.classList.toggle("at-right", forward);
  turner.classList.toggle("at-left", !forward);
  turner.hidden = false;
  // The leaf that turns carries the page it is taking off the pile, on both of its faces.
  const leaving = forward ? state.view : state.view - 1;
  paint(turnFront, leaving);
  paint(turnBack, leaving);
  // The side the leaf lifts off is repainted now, the side it lands on at the end.
  if (forward) paint(leafRight, target);
  else paint(leafLeft, target - 1);

  void turner.offsetWidth;
  book.classList.add(forward ? "turn-fwd" : "turn-back");
  turning = { target: target };
  turner.addEventListener("animationend", onTurnEnd);
  turnTimer = window.setTimeout(settle, turnMs() + 500);
}

// The sheen on each face animates too, and animationend bubbles, so only the leaf counts.
function onTurnEnd(event) {
  if (event.target !== turner) return;
  settle();
}

function settle() {
  if (!turning) return;
  const target = turning.target;
  turning = null;
  window.clearTimeout(turnTimer);
  turner.removeEventListener("animationend", onTurnEnd);
  turner.hidden = true;
  book.classList.remove("turn-fwd", "turn-back");
  state.view = target;
  paint(leafLeft, target - 1);
  paint(leafRight, target);
  afterView();
  chase();
}

function afterView() {
  // While the book is following there is nothing to jump back to, even mid catch up.
  toLive.hidden = state.live === 0 || state.following;
  prevButton.disabled = state.view <= 0;
  nextButton.disabled = state.view >= state.highest;
  const total = state.total || state.highest;
  whereLabel.textContent = state.view === 0
    ? "Title page" + (total ? " of " + total + " pages" : "")
    : "Page " + state.view + (total ? " of " + total : "");
  const page = state.pages.get(state.view);
  if (state.view === state.live && page && !page.done) mountLive();
}

// ------------------------------------------------------------------ the run

async function build(event) {
  event.preventDefault();
  const idea = el("idea").value.trim();
  if (!idea) return;
  el("build").disabled = true;
  errorBox.hidden = true;
  finishBox.hidden = true;
  el("outlineList").textContent = "";
  el("outlineBox").hidden = true;
  state.title = "";
  state.idea = idea;
  state.total = 0;
  state.pages = new Map();
  state.order = [];
  state.live = 0;
  state.highest = 0;
  state.view = 0;
  state.following = true;
  state.finished = false;
  doneWords = 0;
  liveWords = 0;
  penAt = 0;
  setFit(1);
  unmount();
  setStatus("Waking the model");

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
  state.total = payload.pages;
  state.title = el("title").value.trim();
  startedAt = performance.now();
  stats.hidden = false;
  stopButton.hidden = false;
  setup.hidden = true;
  desk.hidden = false;
  el("statPages").textContent = "0 of " + state.total;
  paintStats();
  paint(leafLeft, -1);
  paint(leafRight, 0);
  afterView();
  ticker = window.setInterval(paintStats, 100);
  listen();
}

function listen() {
  source = new EventSource("/api/runs/" + runId + "/events");

  source.addEventListener("status", (event) => {
    setStatus(JSON.parse(event.data).message);
  });

  source.addEventListener("outline", (event) => {
    const data = JSON.parse(event.data);
    state.title = data.title;
    state.total = data.pages;
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
    el("outlineSummary").textContent =
      "Outline: " + data.chapters.length + " chapters, " + data.pages + " pages";
    el("outlineBox").hidden = false;
    el("statPages").textContent = "0 of " + state.total;
    if (state.view === 0) paint(leafRight, 0);
    afterView();
  });

  source.addEventListener("page_start", (event) => {
    const data = JSON.parse(event.data);
    const before = state.pages.get(data.index - 1);
    state.pages.set(data.index, {
      index: data.index,
      chapter: data.chapter,
      chapterTitle: data.chapter_title || "",
      opens: !before || before.chapter !== data.chapter,
      text: "",
      words: 0,
      done: false,
    });
    state.order.push(data.index);
    state.total = data.total || state.total;
    state.live = data.index;
    state.highest = Math.max(state.highest, data.index);
    liveWords = 0;
    // The reader who has flipped back keeps their place. The book only turns on its own
    // while it is following the page being written.
    afterView();
    chase();
  });

  source.addEventListener("delta", (event) => {
    const data = JSON.parse(event.data);
    const page = state.pages.get(data.index);
    if (!page) return;
    if (!penAt) {
      penAt = performance.now();
      renderStatus();
    }
    page.text += data.text;
    page.words += countWords(data.text);
    if (data.index === state.live) liveWords = page.words;
    if (data.index === writer.mounted) queue(data.text);
  });

  source.addEventListener("page_done", (event) => {
    const data = JSON.parse(event.data);
    const page = state.pages.get(data.index);
    if (page) {
      page.done = true;
      page.words = data.words;
      page.seconds = data.elapsed_ms / 1000;
      page.truncated = data.truncated;
    }
    if (data.index === writer.mounted) {
      flush();
      unmount();
    }
    // A finished page is drawn again from its first line and measured, so the type comes
    // down to the size that holds the longest page in the book and nothing stays hidden.
    if (page && state.view === data.index) paint(leafRight, data.index);
    doneWords = data.total_words;
    liveWords = 0;
    el("statPages").textContent = data.index + " of " + data.total;
    paintStats();
  });

  source.addEventListener("page_dropped", (event) => {
    const data = JSON.parse(event.data);
    state.pages.delete(data.index);
    state.order = state.order.filter((index) => index !== data.index);
    if (data.index === writer.mounted) unmount();
    state.highest = Math.max(0, data.index - 1);
    state.live = state.highest;
    if (state.view >= data.index) {
      state.view = state.highest;
      paint(leafLeft, state.view - 1);
      paint(leafRight, state.view);
    }
    liveWords = 0;
    afterView();
  });

  // The stream names its own failure event "failed" because EventSource already uses
  // "error" for a dropped connection.
  source.addEventListener("failed", (event) => {
    const data = JSON.parse(event.data);
    showError(data.message, data.raw);
    setStatus("", true);
  });

  source.addEventListener("done", (event) => {
    state.finished = true;
    const data = JSON.parse(event.data);
    close();
    if (writer.mounted) {
      flush();
      unmount();
      paint(leafRight, state.view);
    }
    doneWords = data.words;
    liveWords = 0;
    paintStats();
    el("statPages").textContent = data.pages + " of " + data.pages_requested;
    setStatus("", true);
    statusLine.hidden = true;
    if (!state.highest) {
      desk.hidden = true;
      setup.hidden = false;
    }
    afterView();
    chase();

    finishBox.hidden = false;
    finishBox.textContent = "";
    const heading = document.createElement("h2");
    const pages = data.pages + (data.pages === 1 ? " page" : " pages");
    heading.textContent = data.stopped ? "Stopped after " + pages : "Done. " + pages + ".";
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
    if (setup.hidden) {
      const again = document.createElement("button");
      again.type = "button";
      again.className = "again";
      again.textContent = "Build another book";
      again.addEventListener("click", () => {
        setup.hidden = false;
        setup.scrollIntoView({ behavior: "smooth", block: "center" });
        el("idea").focus();
      });
      finishBox.appendChild(again);
    }
  });

  source.onerror = () => {
    if (state.finished) return;
    setStatus("The connection dropped. Picking the stream back up.");
  };
}

function close() {
  if (source) source.close();
  source = null;
  if (ticker) window.clearInterval(ticker);
  ticker = null;
  stopButton.hidden = true;
  el("build").disabled = false;
}

// -------------------------------------------------------------- the controls

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

// A turn the stream started may still be running, and it decides which page the reader is
// actually on, so it is finished before one page either way is worked out.
function step(delta) {
  if (turning) settle();
  goTo(state.view + delta, false);
}

prevButton.addEventListener("click", () => step(-1));
nextButton.addEventListener("click", () => step(1));
toLive.addEventListener("click", () => goTo(state.live, false));

document.addEventListener("keydown", (event) => {
  if (desk.hidden || event.metaKey || event.ctrlKey || event.altKey) return;
  const tag = document.activeElement ? document.activeElement.tagName : "";
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    step(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    step(1);
  }
});

// A window that changes size changes the paper, so the pages are measured again.
let resizeTimer = 0;
window.addEventListener("resize", () => {
  if (desk.hidden) return;
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => {
    setFit(1);
    paint(leafLeft, state.view - 1);
    paint(leafRight, state.view);
    afterView();
  }, 150);
});

let touchX = 0;
let touchY = 0;
desk.addEventListener("touchstart", (event) => {
  touchX = event.changedTouches[0].clientX;
  touchY = event.changedTouches[0].clientY;
}, { passive: true });
desk.addEventListener("touchend", (event) => {
  const dx = event.changedTouches[0].clientX - touchX;
  const dy = event.changedTouches[0].clientY - touchY;
  if (Math.abs(dx) < 45 || Math.abs(dx) < Math.abs(dy)) return;
  step(dx < 0 ? 1 : -1);
}, { passive: true });

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
    state.model = data.model;
    el("modelLine").textContent = "Model: " + data.model;
    el("keyWarning").hidden = data.runpod_key_set;
  })
  .catch(() => {
    showError("The page could not read its own settings from the server.");
  });
