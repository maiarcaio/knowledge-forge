const text = (node, value) => { node.textContent = value; };

document.querySelector('#capture-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const input = document.querySelector('#source-url');
  const status = document.querySelector('#capture-status');
  text(status, 'Saving source…');
  const response = await fetch('/api/sources', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: input.value}) });
  const data = await response.json();
  if (!response.ok) { text(status, data.detail?.source_id ? 'Already in your library.' : 'This source could not be saved.'); return; }
  if (data.platform === 'youtube') {
    text(status, 'Checking public captions…');
    const ingested = await fetch(`/api/sources/${data.id}/ingest`, {method: 'POST'});
    const processed = await ingested.json();
    text(status, processed.status === 'ready' ? 'Saved and indexed.' : 'Saved. Public captions are unavailable; add permitted media later.');
  } else { text(status, 'Saved. Instagram transcription requires a permitted/manual ingestion path.'); }
  input.value = '';
});

document.querySelector('#search-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const results = document.querySelector('#search-results');
  results.replaceChildren();
  const q = document.querySelector('#search-query').value;
  const data = await (await fetch(`/api/search?q=${encodeURIComponent(q)}`)).json();
  for (const item of data.results) {
    const li = document.createElement('li');
    const link = document.createElement('a'); link.href = item.source_url; link.target = '_blank'; link.rel = 'noreferrer'; text(link, item.timestamp);
    const paragraph = document.createElement('p'); text(paragraph, item.text);
    li.append(link, paragraph); results.append(li);
  }
  if (!data.results.length) text(results, 'No exact transcript evidence found yet.');
});

document.querySelector('#chat-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const answer = document.querySelector('#chat-answer');
  text(answer, 'Finding evidence…');
  const question = document.querySelector('#chat-question').value;
  const response = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question})});
  const data = await response.json();
  answer.replaceChildren();
  const paragraph = document.createElement('p'); text(paragraph, data.answer); answer.append(paragraph);
  const list = document.createElement('ul');
  for (const citation of data.citations) {
    const item = document.createElement('li');
    const link = document.createElement('a'); link.href = citation.url; link.target = '_blank'; link.rel = 'noreferrer'; text(link, citation.timestamp);
    item.append(link, document.createTextNode(` ${citation.text}`)); list.append(item);
  }
  answer.append(list);
});
