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
    const wait = state.last + DELAY_MS - Date.now();
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

  window.pdf = { enqueue, status, profile, view, close, exportProfiles, openDoc, pageInfo, segment, unpredict, state };
  return 'pdf probe ready';
})();
