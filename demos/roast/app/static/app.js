const form = document.getElementById('roast-form');
const repoInput = document.getElementById('repo-url');
const roastButton = document.getElementById('roast-button');
const fixButton = document.getElementById('fix-button');
const statusLine = document.getElementById('status');
const output = document.getElementById('output');
let lastRoast = '';

async function streamRequest(path, body) {
  output.textContent = ''; statusLine.textContent = 'Starting';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 180000);
  try {
    const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body), signal: controller.signal});
    if (!response.ok) throw new Error(await response.text());
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const messages = buffer.split('\n\n'); buffer = messages.pop();
      for (const message of messages) {
        const type = message.match(/^event: (.+)$/m)?.[1];
        const dataLine = message.match(/^data: (.+)$/m)?.[1];
        if (!type || !dataLine) continue;
        const data = JSON.parse(dataLine);
        if (type === 'status') statusLine.textContent = data;
        if (type === 'token') output.textContent += data;
        if (type === 'error') throw new Error(data);
        if (type === 'done') statusLine.textContent = 'Complete';
      }
    }
    return output.textContent;
  } finally { clearTimeout(timeout); }
}

form.addEventListener('submit', async event => {
  event.preventDefault(); roastButton.disabled = true; fixButton.hidden = true;
  try { lastRoast = await streamRequest('/api/roast', {repo_url: repoInput.value}); fixButton.hidden = !lastRoast; }
  catch (error) { statusLine.textContent = error.name === 'AbortError' ? 'The request timed out after 3 minutes.' : error.message; }
  finally { roastButton.disabled = false; }
});

fixButton.addEventListener('click', async () => {
  fixButton.disabled = true;
  try { await streamRequest('/api/fix', {repo_url: repoInput.value, roast: lastRoast}); }
  catch (error) { statusLine.textContent = error.name === 'AbortError' ? 'The request timed out after 3 minutes.' : error.message; }
  finally { fixButton.disabled = false; }
});

