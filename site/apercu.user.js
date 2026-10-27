// ==UserScript==
// @name         Registres vaudois : aperçu des PDF
// @namespace    https://nyg.github.io/acv-genealogie-index/
// @version      1.1.1
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
      /*__PDF_READER__*/
    }
    const reader = window.pdf;
    reader.state.delay = 0;

    /*__PAGE_MAP__*/

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
