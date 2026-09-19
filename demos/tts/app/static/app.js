"use strict";

const el = (id) => document.getElementById(id);
const textBox = el("text");
const counter = el("counter");
const voicesBox = el("voices");
const speakButton = el("speak");
const output = el("output");
const progress = el("progress");
const firstAudioLine = el("first-audio");
const stopButton = el("stop");
const player = el("player");
const download = el("download");
const errorBox = el("error");
const previewPlayer = el("preview-player");
const cloneNote = el("clone-note");
const cloneControls = el("clone-controls");
const cloneClear = el("clone-clear");
const cloneStatus = el("clone-status");
const clipInput = el("clip");

let maxWords = 2000;
let selectedVoice = "lucy";
let cloneId = "";
let audioContext = null;
let scheduleAt = 0;
let decodeChain = Promise.resolve();
let playing = [];
let running = false;

function countWords(value) {
  const trimmed = value.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

function updateCounter() {
  const words = countWords(textBox.value);
  counter.textContent = `${words} of ${maxWords} words`;
  counter.classList.toggle("over", words > maxWords);
}

function showError(message) {
  output.classList.remove("hidden");
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearOutput() {
  errorBox.classList.add("hidden");
  errorBox.textContent = "";
  download.classList.add("hidden");
  player.classList.add("hidden");
  player.removeAttribute("src");
  firstAudioLine.classList.add("hidden");
  stopButton.classList.add("hidden");
  progress.textContent = "";
}

function stopPlayback() {
  playing.forEach((source) => {
    try {
      source.stop();
    } catch (ignored) {
      /* already finished */
    }
  });
  playing = [];
  scheduleAt = 0;
  stopButton.classList.add("hidden");
}

function queueChunk(url) {
  decodeChain = decodeChain
    .then(async () => {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Chunk ${url} came back as ${response.status}.`);
      }
      const bytes = await response.arrayBuffer();
      const buffer = await audioContext.decodeAudioData(bytes);
      const source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContext.destination);
      const now = audioContext.currentTime;
      if (scheduleAt < now + 0.06) {
        scheduleAt = now + 0.06;
      }
      source.start(scheduleAt);
      scheduleAt += buffer.duration;
      playing.push(source);
      source.onended = () => {
        playing = playing.filter((item) => item !== source);
      };
      stopButton.classList.remove("hidden");
    })
    .catch((error) => showError(error.message));
}

async function readStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf("\n\n");
    while (split >= 0) {
      const frame = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const line = frame.split("\n").find((part) => part.startsWith("data: "));
      if (line) {
        onEvent(JSON.parse(line.slice(6)));
      }
      split = buffer.indexOf("\n\n");
    }
  }
}

async function speak() {
  if (running) {
    return;
  }
  const text = textBox.value.trim();
  if (!text) {
    showError("Type or paste some text first.");
    return;
  }
  running = true;
  speakButton.disabled = true;
  speakButton.textContent = "Speaking";
  clearOutput();
  stopPlayback();
  output.classList.remove("hidden");
  progress.textContent = "Sending the first chunk to RunPod.";
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  await audioContext.resume();
  decodeChain = Promise.resolve();
  const started = performance.now();
  let total = 0;
  let finished = 0;
  try {
    const response = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice: selectedVoice, clone_id: cloneId }),
    });
    if (!response.ok) {
      let detail = `The server answered ${response.status}.`;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch (ignored) {
        /* keep the status line */
      }
      throw new Error(detail);
    }
    await readStream(response, (event) => {
      if (event.type === "start") {
        total = event.chunks;
        progress.textContent = `0 of ${total} chunks`;
      } else if (event.type === "chunk") {
        finished += 1;
        progress.textContent = `${finished} of ${total} chunks`;
        if (finished === 1) {
          const seconds = ((performance.now() - started) / 1000).toFixed(1);
          firstAudioLine.textContent = `First audio started after ${seconds} seconds.`;
          firstAudioLine.classList.remove("hidden");
        }
        queueChunk(event.url);
      } else if (event.type === "done") {
        progress.textContent = `${event.chunks} of ${event.chunks} chunks, ${event.seconds} seconds of audio`;
        player.src = event.url;
        player.classList.remove("hidden");
        download.href = event.url;
        download.classList.remove("hidden");
      } else if (event.type === "error") {
        showError(event.message);
      }
    });
  } catch (error) {
    showError(error.message);
  } finally {
    running = false;
    speakButton.disabled = false;
    speakButton.textContent = "Speak";
  }
}

async function preview(voice, button) {
  const label = button.textContent;
  button.dataset.busy = "true";
  button.textContent = "...";
  try {
    const response = await fetch(`/p/${voice}.wav`);
    if (!response.ok) {
      let detail = `The preview answered ${response.status}.`;
      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch (ignored) {
        /* keep the status line */
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    previewPlayer.src = URL.createObjectURL(blob);
    await previewPlayer.play();
    errorBox.classList.add("hidden");
  } catch (error) {
    showError(error.message);
  } finally {
    delete button.dataset.busy;
    button.textContent = label;
  }
}

function selectVoice(voice) {
  selectedVoice = voice;
  voicesBox.querySelectorAll(".voice").forEach((card) => {
    card.dataset.selected = card.dataset.voice === voice ? "true" : "false";
  });
}

function buildVoices(list, initial) {
  voicesBox.textContent = "";
  list.forEach((voice) => {
    const card = document.createElement("div");
    card.className = "voice";
    card.dataset.voice = voice;
    card.dataset.selected = voice === initial ? "true" : "false";
    const pick = document.createElement("button");
    pick.type = "button";
    pick.className = "pick";
    pick.textContent = voice;
    pick.addEventListener("click", () => selectVoice(voice));
    const play = document.createElement("button");
    play.type = "button";
    play.className = "play";
    play.textContent = "Play";
    play.addEventListener("click", () => preview(voice, play));
    card.append(pick, play);
    voicesBox.append(card);
  });
  selectedVoice = initial;
}

async function uploadClip(file) {
  cloneStatus.classList.remove("hidden");
  cloneStatus.textContent = "Uploading the clip.";
  const form = new FormData();
  form.append("clip", file);
  try {
    const response = await fetch("/api/clone", { method: "POST", body: form });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(body.detail || `The upload answered ${response.status}.`);
    }
    cloneId = body.clone_id;
    cloneStatus.textContent = `Using your clip, ${body.seconds} seconds long. Preset voices are ignored until you clear it.`;
    cloneClear.classList.remove("hidden");
  } catch (error) {
    cloneId = "";
    cloneStatus.classList.add("hidden");
    showError(error.message);
  }
}

async function load() {
  const response = await fetch("/api/voices");
  const config = await response.json();
  maxWords = config.max_words;
  buildVoices(config.voices, config.default);
  updateCounter();
  if (config.cloning_enabled) {
    cloneNote.textContent = `Upload a clip of up to ${config.clone_max_seconds} seconds and 5 MB as ${config.clone_extensions.join(", ")}. It replaces the preset voice.`;
    cloneControls.classList.remove("hidden");
  } else {
    cloneNote.textContent =
      "Voice cloning is off on this server because PUBLIC_BASE_URL is not set. RunPod has to fetch the clip over the internet, so the app needs to know its own public address.";
  }
}

textBox.addEventListener("input", updateCounter);
el("clear").addEventListener("click", () => {
  textBox.value = "";
  updateCounter();
  textBox.focus();
});
speakButton.addEventListener("click", speak);
stopButton.addEventListener("click", stopPlayback);
cloneClear.addEventListener("click", () => {
  cloneId = "";
  clipInput.value = "";
  cloneStatus.classList.add("hidden");
  cloneClear.classList.add("hidden");
});
clipInput.addEventListener("change", () => {
  if (clipInput.files && clipInput.files[0]) {
    uploadClip(clipInput.files[0]);
  }
});

load().catch((error) => showError(`The page could not load its settings: ${error.message}`));
