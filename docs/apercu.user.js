// ==UserScript==
// @name         Registres vaudois : aperçu des PDF
// @namespace    https://nyg.github.io/acv-genealogie-index/
// @version      1.1.0
// @description  Affiche une page d'un PDF de davel-vd.ch sans télécharger le fichier entier, avec le sommaire des registres indexés.
// @match        https://davel-vd.ch/*
// @match        https://nyg.github.io/acv-genealogie-index/*
// @run-at       document-start
// @grant        none
// @downloadURL  https://nyg.github.io/acv-genealogie-index/apercu.user.js
// @updateURL    https://nyg.github.io/acv-genealogie-index/apercu.user.js
// ==/UserScript==

(() => {
  const SITE_HOST = 'nyg.github.io';
  const PAGE_MAP_URL = 'https://nyg.github.io/acv-genealogie-index/pdf-pages.json';
  const UPLOADS_PATH = '/uploads/r/null/';
  const CHALLENGE_PATH = '/js_challenge.html';
  const PENDING_KEY = 'acv-apercu';
  const ZOOM_KEY = 'acv-apercu-zoom';
  const TOC_KEY = 'acv-apercu-sommaire';
  const ZOOMS = [0, 1, 1.5, 2, 3, 4];
  const PREFETCH_DELAY_MS = 1500;
  const NAVIGATION_DELAY_MS = 150;
  const STAGE_PADDING = 8;

  const hashParams = () => new URLSearchParams(location.hash.slice(1));
  const whenReady = callback => document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', callback, { once: true }) : callback();
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const stored = (key, fallback) => { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } };
  const store = (key, value) => { try { localStorage.setItem(key, value); } catch {} };

  if (location.hostname === SITE_HOST) {
    const announce = () => {
      document.documentElement.dataset.acvApercu = '';
      document.dispatchEvent(new Event('acv-apercu'));
    };
    if (document.documentElement) announce(); else whenReady(announce);
    return;
  }

  if (location.pathname === CHALLENGE_PATH) {
    if (hashParams().has('apercu')) sessionStorage.setItem(PENDING_KEY, JSON.stringify({ path: new URLSearchParams(location.search).get('redirect') ?? '/', hash: location.hash }));
    return;
  }

  const pending = JSON.parse(sessionStorage.getItem(PENDING_KEY));
  sessionStorage.removeItem(PENDING_KEY);
  if (pending && !location.hash && pending.path === location.pathname + location.search) history.replaceState(null, '', pending.hash);

  const STYLE = `
    .viewer { position: fixed; inset: 0; display: flex; flex-direction: column; background: #1e1e1e; color: #eee; color-scheme: dark; font: 14px/1.4 system-ui, sans-serif; }
    .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; padding: 6px 10px; background: #111; border-bottom: 1px solid #333; }
    .title { font-weight: 600; margin-right: 4px; }
    .tools { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-left: auto; }
    button, .full { font: inherit; color: inherit; background: #2c2c2c; border: 1px solid #484848; border-radius: 4px; padding: 2px 10px; cursor: pointer; text-decoration: none; }
    button:hover, .full:hover { background: #3c3c3c; }
    button:disabled { opacity: 0.4; cursor: default; }
    input { font: inherit; width: 4em; text-align: right; color: inherit; background: #000; border: 1px solid #484848; border-radius: 4px; padding: 2px 6px; }
    .count, .also { color: #aaa; }
    .also { display: inline-flex; align-items: center; gap: 4px; }
    .where { color: #9fd9b9; }
    .status { color: #bbb; }
    .status.error { color: #ff8a80; }
    .main { flex: 1; min-height: 0; display: flex; }
    .toc { width: min(300px, 70vw); flex: none; overflow: auto; background: #161616; border-right: 1px solid #333; }
    .toc ol { list-style: none; margin: 0; padding: 6px 0; }
    .toc button { display: grid; gap: 2px; width: 100%; text-align: left; background: none; border: 0; border-left: 3px solid transparent; border-radius: 0; padding: 6px 10px; }
    .toc button:hover { background: #262626; }
    .toc .current button { border-left-color: #4cc48b; background: #202a25; }
    .toc .content { font-weight: 600; }
    .toc .range, .toc .note { color: #aaa; font-size: 12px; }
    .stage { flex: 1; min-width: 0; overflow: auto; display: flex; padding: ${STAGE_PADDING}px; box-sizing: border-box; }
    .frame { position: relative; flex: none; margin: auto; }
    img { position: absolute; left: 50%; top: 50%; max-width: none; background: #fff; cursor: zoom-in; }
    .zoomed img { cursor: zoom-out; }
  `;

  const createViewer = () => {
    if (!window.pdf) {
      (() => {
  const DELAY_MS = 1500;
  const UPLOADS_PREFIX = 'https://davel-vd.ch/uploads/r/null/';
  const TAIL_BYTES = 262144;
  const CHUNK_BYTES = 4096;
  const STRIP_MAX_HEIGHT = 300;
  const IMAGE_CACHE = 40;

  const state = (window.__pdf ??= { docs: {}, profiles: {}, queue: [], running: false, errors: [], requests: 0, last: 0, images: new Map() });

  // Timers of a hidden tab fire about once a minute; a worker's timers keep their pace.
  const timer = new Worker(URL.createObjectURL(new Blob(['onmessage = e => setTimeout(() => postMessage(e.data.id), e.data.ms)'], { type: 'text/javascript' })));
  const waiting = new Map();
  let sequence = 0;
  timer.onmessage = event => { waiting.get(event.data)(); waiting.delete(event.data); };
  const sleep = ms => new Promise(resolve => { const id = ++sequence; waiting.set(id, resolve); timer.postMessage({ id, ms }); });

  const pace = async () => {
    const wait = state.last + (state.delay ?? DELAY_MS) - Date.now();
    if (wait > 0) await sleep(wait);
    state.last = Date.now();
    state.requests++;
  };

  const fetchRange = async (url, range) => {
    await pace();
    const response = await fetch(url, { headers: { Range: `bytes=${range}` } });
    if (response.status !== 206) throw new Error(`${url}: HTTP ${response.status} for range ${range}`);
    return new Uint8Array(await response.arrayBuffer());
  };

  const latin = bytes => new TextDecoder('latin1').decode(bytes);
  const refs = text => (text.match(/\d+\s+\d+\s+R/g) || []).map(ref => +ref.split(/\s/)[0]);
  const ref = (text, key) => +(new RegExp(`/${key}\\s+(\\d+)\\s+\\d+\\s+R`).exec(text) || [])[1] || null;
  const number = (text, key) => +(new RegExp(`/${key}\\s+(-?\\d+)`).exec(text) || [])[1] || 0;
  const pdfUrl = path => path.startsWith('http') ? path : UPLOADS_PREFIX + path;

  const inflate = async bytes => new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer());

  const unpredict = (data, dict) => {
    const predictor = number(dict, 'Predictor');
    if (predictor < 10) return data;
    const columns = number(dict, 'Columns') || 1;
    const rows = data.length / (columns + 1);
    const out = new Uint8Array(rows * columns);
    for (let row = 0; row < rows; row++) {
      const filter = data[row * (columns + 1)];
      for (let col = 0; col < columns; col++) {
        const raw = data[row * (columns + 1) + 1 + col];
        const left = col ? out[row * columns + col - 1] : 0;
        const up = row ? out[(row - 1) * columns + col] : 0;
        const upLeft = row && col ? out[(row - 1) * columns + col - 1] : 0;
        const paeth = () => {
          const p = left + up - upLeft;
          const [a, b, c] = [Math.abs(p - left), Math.abs(p - up), Math.abs(p - upLeft)];
          return a <= b && a <= c ? left : b <= c ? up : upLeft;
        };
        const base = [0, left, up, (left + up) >> 1, filter === 4 ? paeth() : 0][filter];
        out[row * columns + col] = (raw + base) & 0xff;
      }
    }
    return out;
  };

  const openDoc = async path => {
    const url = pdfUrl(path);
    if (state.docs[url]) return state.docs[url];
    await pace();
    const size = +(await fetch(url, { method: 'HEAD' })).headers.get('content-length');
    const tail = await fetchRange(url, `-${Math.min(size, TAIL_BYTES)}`);
    const tailStart = size - tail.length;

    const bytesAt = async (offset, length) => offset >= tailStart
      ? tail.slice(offset - tailStart, offset - tailStart + length)
      : fetchRange(url, `${offset}-${Math.min(size, offset + length) - 1}`);

    const streamObjectAt = async offset => {
      let bytes = await bytesAt(offset, CHUNK_BYTES);
      const header = /^\s*(\d+)\s+\d+\s+obj\s*<<([^]*?)>>\s*stream\r?\n/.exec(latin(bytes.slice(0, CHUNK_BYTES)));
      if (!header) throw new Error(`${url}: no stream object at ${offset}`);
      const length = ref(header[2], 'Length') ? +(/^\s*(\d+)/.exec(await object(ref(header[2], 'Length')))[1]) : number(header[2], 'Length');
      if (header[0].length + length > bytes.length) bytes = await bytesAt(offset, header[0].length + length);
      let data = bytes.slice(header[0].length, header[0].length + length);
      if (/FlateDecode/.test(header[2])) data = unpredict(await inflate(data), header[2]);
      return { id: +header[1], dict: header[2], data };
    };

    const entries = {};
    let trailer = '';
    const readXref = async offset => {
      const head = await bytesAt(offset, 4);
      if (latin(head) === 'xref') {
        const text = latin(await bytesAt(offset, offset >= tailStart ? size - offset : 1048576));
        const [table, rest] = text.split('trailer');
        for (const section of table.matchAll(/(\d+)\s+(\d+)\s*\r?\n((?:\d{10} \d{5} [nf]\s*)+)/g)) {
          section[3].trim().split(/\s*\r?\n\s*|\s{2,}/).forEach((line, index) => {
            const [entryOffset, , kind] = line.trim().split(' ');
            entries[+section[1] + index] ??= kind === 'n' ? { type: 1, offset: +entryOffset } : { type: 0 };
          });
        }
        const dict = /<<([^]*?)>>\s*startxref/.exec(rest)?.[1] ?? rest;
        trailer ||= dict;
        return number(dict, 'Prev') || null;
      }
      const stream = await streamObjectAt(offset);
      const widths = /\/W\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s*\]/.exec(stream.dict).slice(1).map(Number);
      const index = /\/Index\s*\[([^\]]*)\]/.exec(stream.dict)?.[1].trim().split(/\s+/).map(Number) ?? [0, number(stream.dict, 'Size')];
      const read = (position, width) => { let value = 0; for (let i = 0; i < width; i++) value = value * 256 + stream.data[position + i]; return value; };
      let position = 0;
      for (let s = 0; s < index.length; s += 2) {
        for (let k = 0; k < index[s + 1]; k++) {
          const type = widths[0] ? read(position, widths[0]) : 1;
          const second = read(position + widths[0], widths[1]);
          const third = read(position + widths[0] + widths[1], widths[2]);
          entries[index[s] + k] ??= type === 1 ? { type, offset: second } : type === 2 ? { type, stream: second, index: third } : { type: 0 };
          position += widths[0] + widths[1] + widths[2];
        }
      }
      trailer ||= stream.dict;
      return number(stream.dict, 'Prev') || null;
    };

    let xref = +/startxref\s+(\d+)/.exec(latin(tail.slice(-1024)))[1];
    const seen = new Set();
    while (xref !== null && !seen.has(xref)) {
      seen.add(xref);
      xref = await readXref(xref);
    }

    const offsets = Object.values(entries).filter(entry => entry.type === 1).map(entry => entry.offset).sort((a, b) => a - b).concat([size]);
    const objectSize = id => { const offset = entries[id].offset; return offsets[offsets.indexOf(offset) + 1] - offset; };

    const cache = {};
    const objectStreams = {};
    async function object(id) {
      if (id in cache) return cache[id];
      const entry = entries[id];
      if (!entry || entry.type === 0) return (cache[id] = '');
      if (entry.type === 2) {
        if (!objectStreams[entry.stream]) {
          const stream = await streamObjectAt(entries[entry.stream].offset);
          const first = number(stream.dict, 'First');
          const all = latin(stream.data);
          const pairs = all.slice(0, first).trim().split(/\s+/).map(Number);
          const bodies = {};
          for (let i = 0; i < pairs.length; i += 2) bodies[pairs[i]] = all.slice(first + pairs[i + 1], i + 2 < pairs.length ? first + pairs[i + 3] : undefined);
          objectStreams[entry.stream] = bodies;
        }
        return (cache[id] = objectStreams[entry.stream][id]);
      }
      const bytes = await bytesAt(entry.offset, CHUNK_BYTES);
      return (cache[id] = /^\s*\d+\s+\d+\s+obj([^]*?)(?:stream|endobj)/.exec(latin(bytes))[1]);
    }
    const cheap = id => entries[id]?.type === 2 || entries[id]?.offset >= tailStart;

    const root = await object(ref(trailer, 'Root'));
    const info = ref(trailer, 'Info') ? await object(ref(trailer, 'Info')) : '';
    const pagesRoot = await object(ref(root, 'Pages'));
    const pages = [];
    const walk = async (node, id) => {
      const kids = refs(/\/Kids\s*\[([^\]]*)\]/.exec(node)?.[1] ?? '');
      if (!/\/Type\s*\/Pages\b/.test(node)) pages.push(id);
      else if (number(node, 'Count') === kids.length) pages.push(...kids);
      else for (const kid of kids) await walk(await object(kid), kid);
    };
    await walk(pagesRoot, ref(root, 'Pages'));

    const doc = {
      url, size, pages, object, objectSize, cheap,
      offsetOf: id => entries[id].offset,
      producer: /\/Producer\s*\(([^)]*)\)/.exec(info)?.[1] ?? '',
      created: /\/CreationDate\s*\(D:(\d{8})/.exec(info)?.[1] ?? '',
      defaultBox: /\/MediaBox\s*\[([^\]]*)\]/.exec(pagesRoot)?.[1] ?? '',
    };
    return (state.docs[url] = doc);
  };

  const pageInfo = async (doc, n) => {
    const page = await doc.object(doc.pages[n - 1]);
    const box = (/\/MediaBox\s*\[([^\]]*)\]/.exec(page)?.[1] ?? doc.defaultBox).trim().split(/\s+/).map(Number);
    const resources = ref(page, 'Resources') ? await doc.object(ref(page, 'Resources')) : page;
    const xobjects = /\/XObject\s*<<([^>]*)>>/.exec(resources)?.[1] ?? (ref(resources, 'XObject') ? await doc.object(ref(resources, 'XObject')) : '');
    const image = refs(xobjects).sort((a, b) => doc.objectSize(b) - doc.objectSize(a))[0];
    const contents = refs(/\/Contents\s*\[([^\]]*)\]/.exec(page)?.[1] ?? /\/Contents\s+(\d+\s+\d+\s+R)/.exec(page)?.[1] ?? '');
    return {
      n,
      w: Math.round(box[2] - box[0]),
      h: Math.round(box[3] - box[1]),
      rotate: number(page, 'Rotate'),
      image,
      text: Math.max(0, ...contents.map(doc.objectSize)) > 400,
    };
  };

  const similar = (a, b) => !a.strip && !b.strip && Math.abs(a.w - b.w) / a.w < 0.12 && Math.abs(a.h - b.h) / a.h < 0.04;

  const segment = infos => {
    const segments = [];
    for (const info of infos) {
      const current = segments.at(-1);
      if (info.h <= STRIP_MAX_HEIGHT) { segments.push({ strip: true, from: info.n, to: info.n }); continue; }
      if (current && similar(current, info)) {
        current.to = info.n;
        current.count++;
        current.w += (info.w - current.w) / current.count;
        current.h += (info.h - current.h) / current.count;
      } else segments.push({ from: info.n, to: info.n, w: info.w, h: info.h, count: 1 });
    }
    // Absorbs inserted slips and recto/verso alternations: a run of up to 3 pages between two similar runs.
    for (let k = 1; k < segments.length - 1; k++) {
      const [before, middle, after] = segments.slice(k - 1, k + 2);
      if (!middle.strip && middle.to - middle.from < 3 && similar(before, after)) {
        before.to = after.to;
        segments.splice(k, 2);
        k--;
      }
    }
    for (let k = 1; k < segments.length; k++) {
      if (similar(segments[k - 1], segments[k])) {
        segments[k - 1].to = segments[k].to;
        segments.splice(k--, 1);
      }
    }
    return segments;
  };

  const profile = async (path, { full = false } = {}) => {
    const doc = await openDoc(path);
    const result = { pdf: doc.url.replace(UPLOADS_PREFIX, ''), size: doc.size, pages: doc.pages.length, producer: doc.producer, created: doc.created };
    if (!full && !doc.cheap(doc.pages[0])) return { ...result, layout: 'skipped: page objects are spread through the file (profile(path, { full: true }) costs one request per page)' };
    const infos = [];
    for (let n = 1; n <= doc.pages.length; n++) infos.push(await pageInfo(doc, n));
    return {
      ...result,
      text: infos.some(info => info.text),
      strips: infos.filter(info => info.h <= STRIP_MAX_HEIGHT).map(info => info.n),
      segments: segment(infos).filter(s => !s.strip).map(s => [s.from, s.to, Math.round(s.w), Math.round(s.h)]),
    };
  };

  const run = async () => {
    if (state.running) return;
    state.running = true;
    try {
      while (state.queue.length) {
        const [key, path, options] = state.queue[0];
        try {
          state.profiles[key] = await profile(path, options);
        } catch (error) {
          state.errors.push(`${key}: ${error.message}`);
        }
        state.queue.shift();
      }
    } finally {
      state.running = false;
    }
  };

  const enqueue = (registers, options = {}) => {
    for (const [key, path] of Object.entries(registers)) if (!state.profiles[key]) state.queue.push([key, path, options]);
    run();
    return state.queue.length;
  };

  const imageOf = async (path, n) => {
    const doc = await openDoc(path);
    const key = `${doc.url}#${n}`;
    if (state.images.has(key)) return state.images.get(key);
    const { image } = await pageInfo(doc, n);
    const offset = doc.offsetOf(image);
    const bytes = await fetchRange(doc.url, `${offset}-${offset + doc.objectSize(image) - 1}`);
    const text = latin(bytes.slice(0, 2048));
    const header = /stream\r?\n/.exec(text);
    const dict = text.slice(0, header.index);
    const start = header.index + header[0].length;
    const data = bytes.slice(start, ref(dict, 'Length') ? bytes.length : start + number(dict, 'Length'));
    const type = /DCTDecode/.test(dict) ? 'image/jpeg' : /JPXDecode/.test(dict) ? 'image/jp2' : null;
    if (!type) throw new Error(`page ${n}: image format not displayable (${dict.replace(/\s+/g, ' ').slice(0, 120)})`);
    const blob = URL.createObjectURL(new Blob([data], { type }));
    state.images.set(key, blob);
    if (state.images.size > IMAGE_CACHE) {
      const [oldest, oldBlob] = state.images.entries().next().value;
      URL.revokeObjectURL(oldBlob);
      state.images.delete(oldest);
    }
    return blob;
  };

  const overlay = () => {
    const box = document.getElementById('pdf-view') ?? document.body.appendChild(Object.assign(document.createElement('div'), { id: 'pdf-view' }));
    box.innerHTML = '';
    return box;
  };

  const label = (context, n) => {
    context.fillStyle = '#000';
    context.fillRect(0, 0, 64, 24);
    context.fillStyle = '#ff0';
    context.font = 'bold 18px sans-serif';
    context.fillText(String(n), 6, 18);
  };

  const view = async (path, pages, { band = null, from = 0, left = 0, right = 1, rotate = false } = {}) => {
    const images = [];
    for (const n of pages) {
      const image = new Image();
      image.src = await imageOf(path, n);
      await image.decode();
      images.push([n, image]);
    }
    const box = overlay();
    box.style.cssText = `position:fixed;inset:0;z-index:99999;background:#222;display:${band ? 'flex;flex-direction:column;gap:3px' : `grid;grid-template-columns:repeat(${pages.length},1fr);gap:4px`};overflow:hidden`;
    for (const [n, image] of images) {
      const canvas = document.createElement('canvas');
      const sourceTop = image.naturalHeight * from;
      const sourceHeight = band ? image.naturalHeight * band : image.naturalHeight;
      const sourceLeft = image.naturalWidth * left;
      const sourceWidth = image.naturalWidth * (right - left);
      canvas.width = band ? innerWidth : sourceWidth / 4;
      canvas.height = Math.round(canvas.width * sourceHeight / sourceWidth);
      const context = canvas.getContext('2d');
      if (rotate) { context.translate(canvas.width, canvas.height); context.rotate(Math.PI); }
      context.drawImage(image, rotate ? image.naturalWidth - sourceLeft - sourceWidth : sourceLeft, rotate ? image.naturalHeight - sourceTop - sourceHeight : sourceTop, sourceWidth, sourceHeight, 0, 0, canvas.width, canvas.height);
      context.setTransform(1, 0, 0, 1, 0, 0);
      label(context, n);
      canvas.style.cssText = band ? 'width:100%;flex:none' : 'max-width:100%;max-height:calc(100vh - 8px);margin:auto';
      box.appendChild(canvas);
    }
    return { pages, requests: state.requests };
  };

  const close = () => { document.getElementById('pdf-view')?.remove(); return 'closed'; };

  // Oversized on purpose: the browser tool writes results above its size limit to a file instead of the conversation.
  const padForFile = text => `${text}\n/*PAD*/${' x'.repeat(60000)}`;

  const exportProfiles = (...keys) => padForFile(JSON.stringify(Object.fromEntries(
    (keys.length ? keys : Object.keys(state.profiles)).filter(key => state.profiles[key]).map(key => [key, state.profiles[key]]),
  )));

  const status = () => ({
    running: state.running,
    queue: state.queue.map(([key]) => key),
    done: Object.keys(state.profiles),
    errors: state.errors,
    requests: state.requests,
  });

  window.pdf = { enqueue, status, profile, view, close, exportProfiles, openDoc, pageInfo, imageOf, segment, unpredict, state };
  return 'pdf probe ready';
})();
    }
    const reader = window.pdf;
    reader.state.delay = 0;

    const ROMAN = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
const toRoman = number => ROMAN.reduce(([text, rest], [value, letters]) => [text + letters.repeat(Math.floor(rest / value)), rest % value], ["", number])[0];
function fromRoman(text) {
  const values = [...text.toUpperCase()].map(letter => ROMAN.find(([, letters]) => letters === letter)[0]);
  return values.reduce((sum, value, index) => sum + (value < (values[index + 1] ?? 0) ? -value : value), 0);
}

const pageSpan = ([first, last], roman = false) => {
  const [a, b] = roman ? [toRoman(first), toRoman(last)] : [first, last];
  return first === last ? `${a}` : `${a}–${b}`;
};

const within = (value, a, b) => value >= Math.min(a, b) && value <= Math.max(a, b);

function locatePage(part, page) {
  const points = [[part.pages[0], part.pdf[0]], ...part.anchors, [part.pages[1], part.pdf[1]]];
  const exact = points.find(([known]) => known === page);
  if (exact || !(part.anchors.length || part.spread)) return { pdf: exact ? exact[1] : part.pdf[0] + Math.abs(page - part.pages[0]), approx: false };
  const next = points.findIndex(([known], index) => index > 0 && within(page, points[index - 1][0], known));
  const [[fromPage, fromPdf], [toPage, toPdf]] = [points[next - 1], points[next]];
  return { pdf: Math.round(fromPdf + (page - fromPage) * (toPdf - fromPdf) / (toPage - fromPage)), approx: true };
}

function pdfTargets(unit, text) {
  const value = text.trim();
  const roman = /^[ivxlcdm]+$/i.test(value);
  if (!roman && !/^\d+$/.test(value)) return null;
  const page = roman ? fromRoman(value) : +value;
  return (unit.pdfParts ?? [])
    .filter(part => part.pages && within(page, ...part.pages) && (!roman || part.roman))
    .map(part => ({ part, ...locatePage(part, page) }));
}

function registerPageAt(part, pdf) {
  if (!part.pages || !within(pdf, ...part.pdf)) return null;
  const points = [[part.pages[0], part.pdf[0]], ...part.anchors, [part.pages[1], part.pdf[1]]];
  const exact = points.find(([, known]) => known === pdf);
  if (exact) return { page: exact[0], approx: false };
  if (!(part.anchors.length || part.spread)) return { page: part.pages[0] + Math.sign(part.pages[1] - part.pages[0]) * (pdf - part.pdf[0]), approx: false };
  const next = points.findIndex(([, known], index) => index > 0 && within(pdf, points[index - 1][1], known));
  const [[fromPage, fromPdf], [toPage, toPdf]] = [points[next - 1], points[next]];
  return { page: Math.round(fromPage + (pdf - fromPdf) * (toPage - fromPage) / (toPdf - fromPdf)), approx: true };
}

    let pageMaps = null;
    const pageMapOf = pdfPath => (pageMaps ??= fetch(PAGE_MAP_URL).then(response => response.ok ? response.json() : {}).catch(() => ({})))
      .then(maps => maps[pdfPath] ?? null);

    const host = document.createElement('acv-apercu');
    host.style.cssText = 'all: initial; position: fixed; inset: 0; z-index: 2147483647';
    const root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>${STYLE}</style>
      <div class="viewer">
        <div class="bar">
          <button class="toc-toggle" title="Sommaire du registre (S)" hidden>☰</button>
          <span class="title"></span>
          <button class="prev" title="Page précédente (←)">‹</button>
          <label>PDF p. <input class="page" inputmode="numeric" autocomplete="off"></label>
          <span class="count"></span>
          <button class="next" title="Page suivante (→)">›</button>
          <label class="register" hidden>Registre p. <input class="register-page" autocomplete="off"></label>
          <span class="also"></span>
          <span class="where"></span>
          <span class="status" aria-live="polite"></span>
          <button class="retry" hidden>Réessayer</button>
          <span class="tools">
            <button class="zoom-out" title="Réduire (−)">−</button>
            <button class="fit" title="Page entière (0)">Ajuster</button>
            <button class="zoom-in" title="Agrandir (+)">+</button>
            <button class="rotate" title="Pivoter d'un quart de tour (R)">↻</button>
            <a class="full" target="_blank" rel="noopener">PDF entier</a>
            <button class="close" title="Fermer (Échap)">×</button>
          </span>
        </div>
        <div class="main">
          <nav class="toc" aria-label="Sommaire du registre" hidden><ol></ol></nav>
          <div class="stage"><div class="frame"><img alt=""></div></div>
        </div>
      </div>`;
    const $ = selector => root.querySelector(selector);
    const [stage, frame, image, pageInput, registerInput, toc] = ['.stage', '.frame', 'img', '.page', '.register-page', '.toc'].map($);

    let path = null;
    let title = '';
    let opening = null;
    let doc = null;
    let entry = null;
    let current = 0;
    let natural = null;
    let pageRotation = 0;
    let rotation = 0;
    let originalTitle = null;
    let zoom = 0;
    const savedZoom = +stored(ZOOM_KEY, 0);
    if (ZOOMS.includes(savedZoom)) zoom = savedZoom;

    const loading = new Map();
    const load = n => {
      const key = `${path}#${n}`;
      if (!loading.has(key)) loading.set(key, reader.imageOf(path, n).finally(() => loading.delete(key)));
      return loading.get(key);
    };

    const failure = error => `Échec : ${error.message.replace(/^\S+\.pdf: /, '')}`;

    const setStatus = (text, failed = false) => {
      const status = $('.status');
      status.textContent = text;
      status.classList.toggle('error', failed);
      $('.retry').hidden = !failed;
    };

    const layout = () => {
      if (!natural) return;
      const turn = (pageRotation + rotation) % 360;
      const [width, height] = turn % 180 ? [natural.height, natural.width] : [natural.width, natural.height];
      const room = { width: stage.clientWidth - 2 * STAGE_PADDING, height: stage.clientHeight - 2 * STAGE_PADDING };
      const scale = zoom ? zoom * room.width / width : Math.min(room.width / width, room.height / height);
      frame.style.width = `${width * scale}px`;
      frame.style.height = `${height * scale}px`;
      image.style.width = `${natural.width * scale}px`;
      image.style.height = `${natural.height * scale}px`;
      image.style.transform = `translate(-50%, -50%) rotate(${turn}deg)`;
      stage.classList.toggle('zoomed', zoom > 0);
    };

    const setZoom = (value, focus = { x: 0.5, y: 0.5 }) => {
      const point = {
        x: (stage.scrollLeft + stage.clientWidth * focus.x) / stage.scrollWidth,
        y: (stage.scrollTop + stage.clientHeight * focus.y) / stage.scrollHeight,
      };
      zoom = value;
      store(ZOOM_KEY, zoom);
      layout();
      stage.scrollLeft = point.x * stage.scrollWidth - stage.clientWidth * focus.x;
      stage.scrollTop = point.y * stage.scrollHeight - stage.clientHeight * focus.y;
    };
    const stepZoom = step => setZoom(ZOOMS[Math.min(Math.max(ZOOMS.indexOf(zoom) + step, 0), ZOOMS.length - 1)]);
    const rotate = () => { rotation = (rotation + 90) % 360; layout(); };

    const pageLabel = (part, page) => (part.roman ? toRoman(page) : page);

    const markPosition = () => {
      if (!entry) return;
      const items = toc.querySelectorAll('li');
      const here = entry.pdfParts.flatMap((part, index) => {
        const inside = within(current, ...part.pdf);
        items[index].classList.toggle('current', inside);
        if (!inside) return [];
        const at = registerPageAt(part, current);
        return [at ? `${part.content}, p. ${at.approx ? '≈ ' : ''}${pageLabel(part, at.page)}` : part.content];
      });
      $('.where').textContent = here.join(' · ');
    };

    const setEntry = found => {
      entry = found;
      $('.toc-toggle').hidden = !entry;
      $('.register').hidden = !entry;
      toc.hidden = !entry || stored(TOC_KEY, '1') !== '1';
      $('.where').textContent = '';
      if (!entry) return;
      registerInput.inputMode = entry.pdfParts.some(part => part.roman) ? 'text' : 'numeric';
      toc.querySelector('ol').replaceChildren(...entry.pdfParts.map(part => {
        const line = (className, text) => Object.assign(document.createElement('span'), { className, textContent: text });
        const button = document.createElement('button');
        button.append(line('content', part.content), line('range', `PDF p. ${pageSpan(part.pdf)}${part.pages ? ` · registre p. ${pageSpan(part.pages, part.roman)}` : ''}`));
        if (part.note) button.append(line('note', part.note));
        button.addEventListener('click', () => show(part.pdf[0]));
        const item = document.createElement('li');
        item.append(button);
        return item;
      }));
      markPosition();
    };

    const toggleToc = () => {
      if (!entry) return;
      toc.hidden = !toc.hidden;
      store(TOC_KEY, toc.hidden ? '0' : '1');
    };

    const prefetch = async n => {
      for (const neighbour of [n + 1, n - 1]) {
        await sleep(PREFETCH_DELAY_MS);
        if (n !== current) return;
        if (neighbour >= 1 && neighbour <= doc.pages.length) await load(neighbour).catch(() => {});
      }
    };

    const show = async n => {
      if (!doc) return;
      n = Math.min(Math.max(n, 1), doc.pages.length);
      current = n;
      pageInput.value = n;
      registerInput.value = '';
      $('.also').replaceChildren();
      markPosition();
      $('.prev').disabled = n === 1;
      $('.next').disabled = n === doc.pages.length;
      $('.full').href = `${doc.url}#page=${n}`;
      history.replaceState(null, '', `#${new URLSearchParams({ apercu: '', page: n, pdf: path, titre: title })}`);
      whenReady(() => {
        originalTitle ??= document.title;
        document.title = `${title} · PDF p. ${n}`;
      });
      setStatus('Chargement…');
      await sleep(NAVIGATION_DELAY_MS);
      if (n !== current) return;
      try {
        const source = await load(n);
        const { rotate: turn } = await reader.pageInfo(doc, n);
        const decoded = new Image();
        decoded.src = source;
        await decoded.decode();
        if (n !== current) return;
        image.src = source;
        natural = { width: decoded.naturalWidth, height: decoded.naturalHeight };
        pageRotation = turn;
        layout();
        stage.scrollTop = 0;
        setStatus('');
        prefetch(n);
      } catch (error) {
        if (n === current) setStatus(failure(error), true);
      }
    };

    const showRegisterPage = () => {
      const typed = registerInput.value;
      const targets = pdfTargets(entry, typed);
      registerInput.blur();
      if (!targets?.length) {
        $('.also').replaceChildren(targets ? 'hors des pages connues' : 'numéro de page ?');
        return;
      }
      const chosen = targets.find(target => within(current, ...target.part.pdf)) ?? targets[0];
      show(chosen.pdf);
      registerInput.value = typed;
      const others = targets.filter(target => target !== chosen).map(target => {
        const button = Object.assign(document.createElement('button'), { textContent: `${target.approx ? '≈ ' : ''}PDF p. ${target.pdf}`, title: target.part.content });
        button.addEventListener('click', () => show(target.pdf));
        return button;
      });
      if (others.length) $('.also').append('aussi', ...others);
    };

    const mount = () => {
      if (host.isConnected) return;
      document.body.append(host);
      document.documentElement.style.overflow = 'hidden';
    };

    const open = async (newPath, n, newTitle) => {
      whenReady(mount);
      title = newTitle || 'PDF';
      $('.title').textContent = title;
      if (newPath !== path || !opening) {
        path = newPath;
        doc = null;
        setEntry(null);
        opening = reader.openDoc(path).catch(error => { opening = null; throw error; });
        pageMapOf(path).then(found => path === newPath && setEntry(found));
      }
      setStatus('Ouverture du PDF…');
      try {
        const opened = await opening;
        if (path !== newPath) return;
        doc = opened;
      } catch (error) {
        if (path === newPath) setStatus(failure(error), true);
        return;
      }
      $('.count').textContent = `/ ${doc.pages.length}`;
      $('.full').textContent = `PDF entier (${Math.round(doc.size / 1048576)} Mo)`;
      show(n ?? (await pageMapOf(path))?.pdfParts[0].pdf[0] ?? 1);
    };

    const close = () => {
      if (!host.isConnected) return;
      host.remove();
      document.documentElement.style.overflow = '';
      if (originalTitle !== null) document.title = originalTitle;
      current = 0;
      history.replaceState(null, '', location.pathname + location.search);
    };

    const keys = {
      ArrowLeft: () => show(current - 1),
      ArrowRight: () => show(current + 1),
      '+': () => stepZoom(1),
      '=': () => stepZoom(1),
      '-': () => stepZoom(-1),
      0: () => setZoom(0),
      r: rotate,
      R: rotate,
      s: toggleToc,
      S: toggleToc,
      Escape: close,
    };
    addEventListener('keydown', event => {
      const action = keys[event.key];
      if (!host.isConnected || !action || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.composedPath()[0].tagName === 'INPUT' && event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      action();
    }, true);
    image.addEventListener('click', event => {
      const box = stage.getBoundingClientRect();
      setZoom(zoom ? 0 : 1, { x: (event.clientX - box.left) / stage.clientWidth, y: (event.clientY - box.top) / stage.clientHeight });
    });
    pageInput.addEventListener('change', () => {
      show(Math.round(+pageInput.value) || current);
      pageInput.blur();
    });
    registerInput.addEventListener('change', showRegisterPage);
    $('.toc-toggle').addEventListener('click', toggleToc);
    $('.prev').addEventListener('click', () => show(current - 1));
    $('.next').addEventListener('click', () => show(current + 1));
    $('.zoom-out').addEventListener('click', () => stepZoom(-1));
    $('.fit').addEventListener('click', () => setZoom(0));
    $('.zoom-in').addEventListener('click', () => stepZoom(1));
    $('.rotate').addEventListener('click', rotate);
    $('.close').addEventListener('click', close);
    $('.retry').addEventListener('click', () => location.reload());
    new ResizeObserver(layout).observe(stage);
    return { open, close };
  };

  const addBrowseButton = () => {
    const link = document.querySelector(`a[href*="${UPLOADS_PATH}"][href$=".pdf"]`);
    if (!link) return;
    const params = new URLSearchParams({ apercu: '', pdf: link.pathname.slice(UPLOADS_PATH.length), titre: document.querySelector('.referenceCode')?.textContent.trim() ?? '' });
    const button = Object.assign(document.createElement('a'), { href: `#${params}`, textContent: 'Feuilleter le PDF page par page' });
    button.style.cssText = 'display: inline-block; margin: 0 0 10px; padding: 6px 14px; border-radius: 4px; background: #127a4b; color: #fff; font-weight: 600; text-decoration: none';
    (link.closest('.digital-object-reference, .filename') ?? link).before(button);
  };

  let viewer = null;
  const start = () => {
    const params = hashParams();
    if (!params.has('apercu') || !params.get('pdf')) {
      viewer?.close();
      return;
    }
    viewer ??= createViewer();
    viewer.open(params.get('pdf'), Math.round(+params.get('page')) || null, params.get('titre'));
  };
  addEventListener('hashchange', start);
  whenReady(addBrowseButton);
  start();
})();
