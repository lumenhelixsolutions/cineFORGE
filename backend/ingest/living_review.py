"""Generate living-panels review payloads and HTML from lookBOOK choreography."""

from __future__ import annotations

import html
import json
from typing import Any


def _normalize_panels(panels: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if panels is None:
        return []
    if isinstance(panels, list):
        raw = panels
    else:
        raw = panels.get("panels", [])
    assets: list[dict[str, Any]] = []
    for panel in raw:
        if not isinstance(panel, dict):
            continue
        assets.append(
            {
                "panel_index": panel.get("panel_index", len(assets)),
                "bbox": panel.get("bbox", {}),
                "image": panel.get("image") or panel.get("image_path"),
            }
        )
    return assets


def _normalize_shots(shot_graph: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if shot_graph is None:
        return []
    if isinstance(shot_graph, list):
        return [s for s in shot_graph if isinstance(s, dict)]
    shots = shot_graph.get("shots", [])
    return [s for s in shots if isinstance(s, dict)]


def extract_lookbook_review_data(treatment_json: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return review payload fields when treatment contains lookBOOK choreography."""
    if not treatment_json or not isinstance(treatment_json, dict):
        return None
    choreography = treatment_json.get("choreography")
    if not isinstance(choreography, dict):
        return None
    lines = choreography.get("lines")
    if not isinstance(lines, list) or not lines:
        return None
    return {
        "title": treatment_json.get("title") or "lookBOOK import",
        "choreography": choreography,
        "panels": _normalize_panels(treatment_json.get("panels")),
        "shots": _normalize_shots(treatment_json.get("shot_graph")),
    }


def build_review_payload(
    treatment_json: dict[str, Any] | None,
    *,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Build JSON review payload; marks availability for clients."""
    data = extract_lookbook_review_data(treatment_json)
    if not data:
        return {
            "available": False,
            "message": "No lookBOOK choreography found. Import a shot graph with choreography to enable Living review.",
        }
    title = project_name or data.get("title") or "lookBOOK import"
    return {
        "available": True,
        "title": title,
        "choreography": data["choreography"],
        "panels": data["panels"],
        "shots": data["shots"],
    }


def _empty_review_html(message: str, title: str = "Living Panels") -> str:
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #000;
      color: rgba(255,255,255,.55);
      font-family: system-ui, sans-serif;
      padding: 24px;
      text-align: center;
    }}
    .badge {{
      color: #1ae0cf;
      text-transform: uppercase;
      letter-spacing: .18em;
      font-size: 11px;
      font-weight: 700;
      margin-bottom: 12px;
    }}
    p {{ max-width: 360px; line-height: 1.5; font-size: 14px; }}
  </style>
</head>
<body>
  <div>
    <div class="badge">lookBOOK · living panels</div>
    <p>{safe_message}</p>
  </div>
</body>
</html>"""


def build_review_html(
    treatment_json: dict[str, Any] | None,
    *,
    project_name: str | None = None,
) -> str:
    """Render self-contained living-panels HTML for iframe embedding."""
    payload = build_review_payload(treatment_json, project_name=project_name)
    if not payload.get("available"):
        return _empty_review_html(str(payload.get("message", "Living review unavailable.")))

    title = html.escape(str(payload.get("title") or "lookBOOK import"))
    payload_json = json.dumps(
        {
            "choreography": payload["choreography"],
            "panels": payload["panels"],
            "shots": payload["shots"],
        },
        ensure_ascii=False,
    )
    payload_json = payload_json.replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} · Living Panels</title>
  <style>
    :root {{
      --bg: #070a10;
      --ink: #fdf6d8;
      --accent: #1ae0cf;
      --gold: #e8c36a;
      --panel-border: rgba(255,255,255,.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(ellipse at 20% 0%, #121824 0%, var(--bg) 55%);
      color: var(--ink);
      font-family: system-ui, sans-serif;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--panel-border);
    }}
    .badge {{
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: .18em;
      font-size: 11px;
      font-weight: 800;
    }}
    h1 {{ margin: 4px 0 0; font-size: 1.25rem; font-weight: 600; }}
    main {{ display: grid; grid-template-columns: 1fr 280px; gap: 16px; padding: 16px 20px 28px; }}
    @media (max-width: 900px) {{ main {{ grid-template-columns: 1fr; }} }}
    #stage-wrap {{
      position: relative;
      overflow: hidden;
      border-radius: 18px;
      border: 1px solid var(--panel-border);
      background: #0c1018;
      min-height: 360px;
    }}
    #stage {{
      display: flex;
      gap: 10px;
      padding: 14px;
      transition: transform .6s cubic-bezier(.2,.8,.2,1);
      will-change: transform;
    }}
    .panel-card {{
      flex: 0 0 auto;
      width: min(220px, 42vw);
      border-radius: 12px;
      border: 2px solid transparent;
      overflow: hidden;
      opacity: .45;
      transform: scale(.94);
      transition: opacity .35s, transform .35s, border-color .35s, box-shadow .35s;
    }}
    .panel-card.active {{
      opacity: 1;
      transform: scale(1);
      border-color: var(--gold);
      box-shadow: 0 0 28px rgba(232,195,106,.25);
    }}
    .panel-card img {{
      display: block;
      width: 100%;
      height: auto;
      background: #111;
    }}
    .panel-placeholder {{
      aspect-ratio: 3/4;
      display: grid;
      place-items: center;
      background: linear-gradient(145deg,#151b28,#0a0e16);
      color: rgba(255,255,255,.35);
      font-size: 12px;
    }}
    #bubble {{
      margin-top: 14px;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid var(--panel-border);
      background: rgba(255,255,255,.04);
      min-height: 72px;
      line-height: 1.5;
    }}
    #speaker {{ font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--gold); margin-bottom: 6px; }}
    #line-text .word {{ opacity: .55; transition: opacity .12s, color .12s; }}
    #line-text .word.spoken {{ opacity: 1; color: var(--accent); }}
    aside {{
      border-radius: 18px;
      border: 1px solid var(--panel-border);
      background: rgba(255,255,255,.03);
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    button {{
      border: 1px solid var(--panel-border);
      background: rgba(0,0,0,.25);
      color: var(--ink);
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
    }}
    button:hover {{ border-color: var(--accent); }}
    button:disabled {{ opacity: .4; cursor: default; }}
    #timeline {{ display: flex; flex-direction: column; gap: 6px; max-height: 280px; overflow: auto; }}
    .tl-item {{
      font-size: 12px;
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px solid transparent;
      cursor: pointer;
      opacity: .7;
    }}
    .tl-item:hover, .tl-item.active {{ opacity: 1; border-color: var(--panel-border); background: rgba(255,255,255,.04); }}
    .tl-item .meta {{ font-size: 10px; opacity: .5; margin-top: 2px; }}
    #camera-tag {{ font-size: 11px; opacity: .55; font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
  <header>
    <div>
      <div class="badge">lookBOOK · living panels</div>
      <h1>{title}</h1>
    </div>
    <div id="camera-tag">camera: static</div>
  </header>
  <main>
    <section>
      <div id="stage-wrap"><div id="stage"></div></div>
      <div id="bubble">
        <div id="speaker">—</div>
        <div id="line-text">Press Play to hear the page.</div>
      </div>
    </section>
    <aside>
      <div class="controls">
        <button id="btn-play" type="button">Play</button>
        <button id="btn-pause" type="button" disabled>Pause</button>
        <button id="btn-prev" type="button">Prev</button>
        <button id="btn-next" type="button">Next</button>
      </div>
      <div id="timeline"></div>
    </aside>
  </main>
  <script id="lookbook-data" type="application/json">{payload_json}</script>
  <script>
  (() => {{
    const data = JSON.parse(document.getElementById('lookbook-data').textContent);
    const lines = data.choreography.lines || [];
    const voiceCast = data.choreography.voice_cast || {{}};
    const panels = data.panels || [];
    const shots = data.shots || [];
    const stage = document.getElementById('stage');
    const timeline = document.getElementById('timeline');
    const speakerEl = document.getElementById('speaker');
    const lineTextEl = document.getElementById('line-text');
    const cameraTag = document.getElementById('camera-tag');
    const btnPlay = document.getElementById('btn-play');
    const btnPause = document.getElementById('btn-pause');
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');

    let lineIndex = 0;
    let utterance = null;
    let spokenWord = -1;

    const panelEls = new Map();
    const panelIndices = panels.length
      ? panels.map((p) => p.panel_index)
      : [...new Set(lines.map((l) => l.panel_index))];

    panelIndices.forEach((panelIndex) => {{
      const panel = panels.find((p) => p.panel_index === panelIndex) || {{ panel_index: panelIndex }};
      const card = document.createElement('div');
      card.className = 'panel-card';
      card.dataset.panelIndex = String(panelIndex);
      if (panel.image) {{
        const img = document.createElement('img');
        img.src = panel.image;
        img.alt = 'Panel ' + panelIndex;
        card.appendChild(img);
      }} else {{
        const ph = document.createElement('div');
        ph.className = 'panel-placeholder';
        ph.textContent = 'Panel ' + panelIndex;
        card.appendChild(ph);
      }}
      stage.appendChild(card);
      panelEls.set(panelIndex, card);
    }});

    function cameraForLine(line) {{
      const shot = shots.find((s) => (s.panels || []).includes(line.panel_index));
      return shot?.camera || 'static';
    }}

    function renderWords(line, highlight = -1) {{
      const words = line.words || [];
      lineTextEl.innerHTML = words.length
        ? words.map((w, i) =>
            `<span class="word${{i <= highlight ? ' spoken' : ''}}">${{w}}</span>`
          ).join(' ')
        : line.text;
    }}

    function focusPanel(panelIndex, camera) {{
      panelEls.forEach((el, idx) => el.classList.toggle('active', idx === panelIndex));
      cameraTag.textContent = 'camera: ' + (camera || 'static');
      const card = panelEls.get(panelIndex);
      if (!card) return;
      const wrap = document.getElementById('stage-wrap');
      const cx = card.offsetLeft + card.offsetWidth / 2;
      const tx = wrap.clientWidth / 2 - cx;
      const scale = String(camera || '').includes('push') || String(camera || '').includes('zoom') ? 1.08 : 1.02;
      stage.style.transform = `translateX(${{tx}}px) scale(${{scale}})`;
    }}

    function setLine(idx) {{
      lineIndex = Math.max(0, Math.min(lines.length - 1, idx));
      const line = lines[lineIndex];
      if (!line) return;
      speakerEl.textContent = line.speaker || '—';
      renderWords(line, spokenWord);
      focusPanel(line.panel_index, cameraForLine(line));
      timeline.querySelectorAll('.tl-item').forEach((el, i) => el.classList.toggle('active', i === lineIndex));
    }}

    lines.forEach((line, i) => {{
      const item = document.createElement('div');
      item.className = 'tl-item';
      const preview = (line.text || '').slice(0, 72);
      item.innerHTML = `<div>${{preview}}${{(line.text || '').length > 72 ? '…' : ''}}</div><div class="meta">${{line.speaker || '—'}} · panel ${{line.panel_index}}</div>`;
      item.addEventListener('click', () => {{ stopSpeech(); spokenWord = -1; setLine(i); }});
      timeline.appendChild(item);
    }});

    function pickVoice(speaker) {{
      const voices = speechSynthesis.getVoices();
      const hint = voiceCast[speaker] || {{}};
      const prefer = (hint.display_name || speaker || '').toLowerCase();
      return voices.find((v) => v.name.toLowerCase().includes('english')) || voices[0] || null;
    }}

    function speakCurrent() {{
      const line = lines[lineIndex];
      if (!line || !('speechSynthesis' in window)) return;
      stopSpeech();
      utterance = new SpeechSynthesisUtterance(line.text || '');
      const cast = voiceCast[line.speaker] || {{}};
      utterance.pitch = cast.pitch ?? 1;
      utterance.rate = cast.rate ?? 1;
      const voice = pickVoice(line.speaker);
      if (voice) utterance.voice = voice;
      spokenWord = -1;
      renderWords(line, spokenWord);
      utterance.onboundary = (ev) => {{
        if (ev.name !== 'word') return;
        spokenWord += 1;
        renderWords(line, spokenWord);
      }};
      utterance.onend = () => {{
        btnPlay.disabled = false;
        btnPause.disabled = true;
        if (lineIndex < lines.length - 1) {{
          spokenWord = -1;
          setLine(lineIndex + 1);
          speakCurrent();
        }}
      }};
      speechSynthesis.speak(utterance);
      btnPlay.disabled = true;
      btnPause.disabled = false;
    }}

    function stopSpeech() {{
      if ('speechSynthesis' in window) speechSynthesis.cancel();
      utterance = null;
      btnPlay.disabled = false;
      btnPause.disabled = true;
    }}

    btnPlay.addEventListener('click', () => {{ setLine(lineIndex); speakCurrent(); }});
    btnPause.addEventListener('click', stopSpeech);
    btnPrev.addEventListener('click', () => {{ stopSpeech(); spokenWord = -1; setLine(lineIndex - 1); }});
    btnNext.addEventListener('click', () => {{ stopSpeech(); spokenWord = -1; setLine(lineIndex + 1); }});

    if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = () => {{}};
    if (lines.length) setLine(0);
  }})();
  </script>
</body>
</html>"""
