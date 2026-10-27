// ==UserScript==
// @name         Registres vaudois : aperçu des PDF
// @namespace    https://nyg.github.io/acv-genealogie-index/
// @version      1.0.0
// @description  Affiche une page d'un PDF de davel-vd.ch sans télécharger le fichier entier.
// @match        https://davel-vd.ch/*
// @match        https://nyg.github.io/acv-genealogie-index/*
// @run-at       document-start
// @grant        none
// @downloadURL  https://nyg.github.io/acv-genealogie-index/apercu.user.js
// @updateURL    https://nyg.github.io/acv-genealogie-index/apercu.user.js
// ==/UserScript==

(() => {
  const SITE_HOST = 'nyg.github.io';
  const CHALLENGE_PATH = '/js_challenge.html';
  const PENDING_KEY = 'acv-apercu';
  const ZOOM_KEY = 'acv-apercu-zoom';
  const ZOOMS = [0, 1, 1.5, 2, 3, 4];
  const PREFETCH_DELAY_MS = 1500;
  const NAVIGATION_DELAY_MS = 150;
  const STAGE_PADDING = 8;

  const hashParams = () => new URLSearchParams(location.hash.slice(1));
  const whenReady = callback => document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', callback, { once: true }) : callback();
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

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
    .count { color: #aaa; }
    .status { color: #bbb; }
    .status.error { color: #ff8a80; }
    .stage { flex: 1; min-height: 0; overflow: auto; display: flex; padding: ${STAGE_PADDING}px; box-sizing: border-box; }
    .frame { position: relative; flex: none; margin: auto; }
    img { position: absolute; left: 50%; top: 50%; max-width: none; background: #fff; cursor: zoom-in; }
    .zoomed img { cursor: zoom-out; }
  `;

  const createViewer = () => {
    if (!window.pdf) {
      /*__PDF_READER__*/
    }
    const reader = window.pdf;
    reader.state.delay = 0;

    const host = document.createElement('acv-apercu');
    host.style.cssText = 'all: initial; position: fixed; inset: 0; z-index: 2147483647';
    const root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>${STYLE}</style>
      <div class="viewer">
        <div class="bar">
          <span class="title"></span>
          <button class="prev" title="Page précédente (←)">‹</button>
          <label>PDF p. <input class="page" inputmode="numeric" autocomplete="off"></label>
          <span class="count"></span>
          <button class="next" title="Page suivante (→)">›</button>
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
        <div class="stage"><div class="frame"><img alt=""></div></div>
      </div>`;
    const $ = selector => root.querySelector(selector);
    const [stage, frame, image, pageInput] = ['.stage', '.frame', 'img', '.page'].map($);

    let path = null;
    let title = '';
    let opening = null;
    let doc = null;
    let current = 0;
    let natural = null;
    let pageRotation = 0;
    let rotation = 0;
    let originalTitle = null;
    let zoom = 0;
    try {
      const saved = +localStorage.getItem(ZOOM_KEY);
      if (ZOOMS.includes(saved)) zoom = saved;
    } catch {}

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
      try { localStorage.setItem(ZOOM_KEY, zoom); } catch {}
      layout();
      stage.scrollLeft = point.x * stage.scrollWidth - stage.clientWidth * focus.x;
      stage.scrollTop = point.y * stage.scrollHeight - stage.clientHeight * focus.y;
    };
    const stepZoom = step => setZoom(ZOOMS[Math.min(Math.max(ZOOMS.indexOf(zoom) + step, 0), ZOOMS.length - 1)]);
    const rotate = () => { rotation = (rotation + 90) % 360; layout(); };

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

    const open = async (newPath, n, newTitle) => {
      whenReady(() => {
        if (host.isConnected) return;
        document.body.append(host);
        document.documentElement.style.overflow = 'hidden';
      });
      title = newTitle || 'PDF';
      $('.title').textContent = title;
      if (newPath !== path || !opening) {
        path = newPath;
        doc = null;
        opening = reader.openDoc(path).catch(error => { opening = null; throw error; });
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
      show(n);
    };

    const close = () => {
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
      Escape: close,
    };
    addEventListener('keydown', event => {
      const action = keys[event.key];
      if (!host.isConnected || !action || event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.composedPath()[0] === pageInput && event.key !== 'Escape') return;
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
    $('.prev').addEventListener('click', () => show(current - 1));
    $('.next').addEventListener('click', () => show(current + 1));
    $('.zoom-out').addEventListener('click', () => stepZoom(-1));
    $('.fit').addEventListener('click', () => setZoom(0));
    $('.zoom-in').addEventListener('click', () => stepZoom(1));
    $('.rotate').addEventListener('click', rotate);
    $('.close').addEventListener('click', close);
    $('.retry').addEventListener('click', () => location.reload());
    addEventListener('resize', layout);
    return { open };
  };

  let viewer = null;
  const start = () => {
    const params = hashParams();
    if (!params.has('apercu') || !params.get('pdf')) return;
    viewer ??= createViewer();
    viewer.open(params.get('pdf'), Math.round(+params.get('page')) || 1, params.get('titre'));
  };
  addEventListener('hashchange', start);
  start();
})();
