(() => {
  const DELAY_MS = 1500;
  const TREE_ID = 'ctl00_cphMainArea_rtrvTree';

  const state = (window.__sa ??= { records: {}, index: {}, queue: [], running: false, log: [], errors: [] });
  state.index ??= {};

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const tree = () => $find(TREE_ID);

  const childrenOf = node => {
    const nodes = node.get_nodes();
    return Array.from({ length: nodes.get_count() }, (_, index) => nodes.getNode(index));
  };

  const expand = async node => {
    if (node.get_expandMode() === 0 || childrenOf(node).length) return childrenOf(node);
    node.expand();
    for (let attempt = 0; attempt < 120 && !childrenOf(node).length; attempt++) await sleep(250);
    return childrenOf(node);
  };

  const NAV_TITLES = {
    parent: 'For entry at previous level',
    firstChild: 'Go to the lower-level entry',
    next: 'Go to the next entry in the archive plan',
  };

  const navigation = doc => Object.fromEntries(Object.entries(NAV_TITLES).map(([key, label]) => {
    const link = [...doc.querySelectorAll('a')].find(a => a.textContent.trim() === label);
    const match = link?.getAttribute('href')?.match(/detail\.aspx\?ID=(\d+)/);
    return [key, match ? match[1] : null];
  }));

  const fetchDetail = async id => (await fetchDetailWithNavigation(id)).fields;

  const fetchDetailWithNavigation = async id => {
    const response = await fetch(`detail.aspx?ID=${id}`);
    if (!response.ok) throw new Error(`detail ${id}: HTTP ${response.status}`);
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const fields = {};
    for (const row of doc.querySelectorAll('tr')) {
      const cells = row.querySelectorAll(':scope > td');
      if (cells.length < 2) continue;
      const label = cells[0].textContent.trim().replace(/:$/, '');
      cells[1].querySelectorAll('br').forEach(br => br.replaceWith('\n'));
      const value = cells[1].textContent.replace(/[ \t]+/g, ' ').replace(/\s*\n\s*/g, '\n').trim();
      if (label && value && label.length < 60 && !fields[label]?.includes(value)) {
        fields[label] = fields[label] ? `${fields[label]}\n${value}` : value;
      }
    }
    return { fields, nav: navigation(doc), title: doc.title };
  };

  const scrapeByNavigation = async (rootId, filter) => {
    const pending = [{ id: String(rootId), parent: null }];
    while (pending.length) {
      const { id, parent } = pending.shift();
      if (state.records[id]) continue;
      const root = await fetchDetailWithNavigation(id);
      await sleep(DELAY_MS);
      const children = [];
      let childId = root.nav.firstChild;
      while (childId) {
        const child = await fetchDetailWithNavigation(childId);
        await sleep(DELAY_MS);
        if (child.nav.parent !== id) break;
        if (!filter || filter(child.title)) children.push({ id: childId, detail: child });
        childId = child.nav.next;
      }
      state.records[id] = { id, parent, text: root.title, fields: root.fields, children: children.map(child => child.id) };
      for (const child of children) {
        if (child.detail.nav.firstChild) {
          pending.push({ id: child.id, parent: id });
        } else {
          state.records[child.id] = { id: child.id, parent: id, text: child.detail.title, fields: child.detail.fields, children: [] };
        }
      }
      state.log.push(`${new Date().toISOString()} ${id} ${root.title.slice(0, 40)}`);
    }
  };

  const walkSiblings = async ({ parent, from, count, filter }) => {
    if (!state.records[parent]) {
      const detail = await fetchDetailWithNavigation(parent);
      state.records[parent] = { id: String(parent), parent: null, text: detail.title, fields: detail.fields, children: [] };
      await sleep(DELAY_MS);
    }
    let id = String(from);
    for (let step = 0; id && step < count; step++) {
      const detail = await fetchDetailWithNavigation(id);
      await sleep(DELAY_MS);
      if (detail.nav.parent !== String(parent)) break;
      if (!filter || filter(detail.title)) {
        state.records[id] = { id, parent: String(parent), text: detail.title, fields: detail.fields, children: [] };
        state.records[parent].children.push(id);
      }
      state.log.push(`${new Date().toISOString()} ${id} ${detail.title.slice(0, 40)}`);
      id = detail.nav.next;
    }
  };

  const indexChildren = async parentId => {
    const parent = await fetchDetailWithNavigation(parentId);
    await sleep(DELAY_MS);
    const children = [];
    let childId = parent.nav.firstChild;
    while (childId) {
      const child = await fetchDetailWithNavigation(childId);
      await sleep(DELAY_MS);
      if (child.nav.parent !== String(parentId)) break;
      children.push([childId, child.title]);
      state.log.push(`${new Date().toISOString()} index ${childId} ${child.title.slice(0, 40)}`);
      childId = child.nav.next;
    }
    state.index[String(parentId)] = { title: parent.title, children };
  };

  const scrapeSubtree = async (rootId, filter) => {
    const pending = [{ id: String(rootId), parent: null }];
    while (pending.length) {
      const { id, parent } = pending.shift();
      if (state.records[id]) continue;
      const node = tree().findNodeByValue(id);
      if (!node) throw new Error(`node ${id} not loaded in the archive plan`);
      const fields = await fetchDetail(id);
      await sleep(DELAY_MS);
      const children = node.get_expandMode() === 0 && !childrenOf(node).length ? [] : await expand(node);
      if (children.length) await sleep(DELAY_MS);
      const kept = children.filter(child => !filter || filter(child.get_text()));
      state.records[id] = { id, parent, text: node.get_text(), fields, children: kept.map(child => child.get_value()) };
      pending.push(...kept.map(child => ({ id: child.get_value(), parent: id })));
      state.log.push(`${new Date().toISOString()} ${id} ${node.get_text().slice(0, 40)}`);
    }
  };

  const run = async () => {
    if (state.running) return;
    state.running = true;
    try {
      while (state.queue.length) {
        const job = state.queue[0];
        try {
          if (job.mode === 'index') await indexChildren(job.id);
          else if (job.mode === 'walk') await walkSiblings(job);
          else if (job.mode === 'nav') await scrapeByNavigation(job.id, job.filter);
          else await scrapeSubtree(job.id, job.filter);
        } catch (error) {
          state.errors.push(`${job.id}: ${error.message}`);
        }
        state.queue.shift();
      }
    } finally {
      state.running = false;
    }
  };

  const enqueue = (id, filter, mode = 'nav') => {
    state.queue.push({ id: String(id), filter, mode });
    run();
    return state.queue.length;
  };

  const enqueueIndex = (...parentIds) => {
    state.queue.push(...parentIds.map(id => ({ id: String(id), mode: 'index' })));
    run();
    return state.queue.length;
  };

  const enqueueWalk = (parent, from, count, filter) => {
    state.queue.push({ id: String(from), parent: String(parent), from: String(from), count, filter, mode: 'walk' });
    run();
    return state.queue.length;
  };

  const listChildren = async id => {
    const node = tree().findNodeByValue(String(id));
    if (!node) throw new Error(`node ${id} not loaded in the archive plan`);
    return (await expand(node)).map(child => [child.get_value(), child.get_text()]);
  };

  const isInSubtree = (id, rootId) => {
    let current = state.records[id];
    while (current) {
      if (current.parent === rootId) return true;
      current = state.records[current.parent];
    }
    return false;
  };

  // Oversized on purpose: the browser tool writes results above its size limit to a file instead of the conversation.
  const padForFile = text => `${text}\n/*PAD*/${' x'.repeat(60000)}`;

  const exportIndex = (...parentIds) => padForFile(JSON.stringify(Object.fromEntries(
    parentIds.map(id => [String(id), state.index[String(id)]]).filter(([, entry]) => entry),
  )));

  const exportSubtrees = (...rootIds) => padForFile(JSON.stringify(Object.fromEntries(rootIds.map(rootId => [
    `sa-${rootId}`,
    Object.values(state.records)
      .filter(record => record.id === String(rootId) || isInSubtree(record.id, String(rootId)))
      .map(record => ({
        slug: `sa-${record.id}`,
        parent: record.id === String(rootId) ? null : `sa-${record.parent}`,
        text: record.text,
        children: record.children.length ? record.children.map(child => `sa-${child}`) : undefined,
        f: record.fields,
      })),
  ]))));

  const status = () => ({
    running: state.running,
    queue: state.queue.map(item => item.id),
    records: Object.keys(state.records).length,
    errors: state.errors,
    last: state.log.slice(-3),
  });

  window.sa = { enqueue, enqueueIndex, enqueueWalk, listChildren, exportIndex, exportSubtrees, status, state };
  return 'scopeArchiv scraper ready';
})();
