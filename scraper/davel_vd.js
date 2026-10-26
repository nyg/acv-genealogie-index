(() => {
  const DELAY_MS = 1500;

  const state = (window.__acv ??= { records: {}, queue: [], running: false, log: [], errors: [] });

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  const fetchTreeChildren = async slug => {
    const response = await fetch(`/${slug}/informationobject/fullWidthTreeView?firstLoad=false`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!response.ok) throw new Error(`tree ${slug}: HTTP ${response.status}`);
    const { nodes } = await response.json();
    return nodes.map(node => ({
      id: node.id,
      slug: node.a_attr.href.replace(/^\//, ''),
      text: node.text,
      type: node.type,
      hasChildren: node.children === true || Array.isArray(node.children),
    }));
  };

  const BLOCK_TAGS = new Set(['P', 'DIV', 'LI', 'UL', 'OL', 'H1', 'H2', 'H3', 'H4', 'TR', 'SECTION']);

  const textWithLineBreaks = node => {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent.replace(/\s+/g, ' ');
    if (node.nodeType !== Node.ELEMENT_NODE) return '';
    if (node.tagName === 'BR') return '\n';
    const inner = [...node.childNodes].map(textWithLineBreaks).join('');
    return BLOCK_TAGS.has(node.tagName) ? `\n${inner}\n` : inner;
  };

  const fieldValue = field => {
    const clone = field.cloneNode(true);
    clone.querySelector('h3')?.remove();
    return textWithLineBreaks(clone).split('\n').map(line => line.trim()).filter(Boolean).join('\n');
  };

  const fetchDescription = async slug => {
    const response = await fetch(`/${slug}`);
    if (!response.ok) throw new Error(`page ${slug}: HTTP ${response.status}`);
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const fields = {};
    for (const field of doc.querySelectorAll('.field')) {
      const label = field.querySelector('h3')?.textContent.trim();
      const value = fieldValue(field);
      if (label && value && !fields[label]?.includes(value)) fields[label] = fields[label] ? `${fields[label]}\n${value}` : value;
    }
    const pdfUrls = [...new Set([...doc.querySelectorAll('a[href*="/uploads/"]')]
      .map(a => a.getAttribute('href'))
      .filter(href => /\.pdf$/i.test(href)))];
    return { heading: doc.querySelector('h1')?.textContent.trim(), fields, pdfUrls };
  };

  const scrapeSubtree = async (rootSlug, parentSlug = null) => {
    const pending = [{ slug: rootSlug, parentSlug, node: null }];
    while (pending.length) {
      const { slug, parentSlug: parent, node } = pending.shift();
      if (state.records[slug]?.description) continue;
      const description = await fetchDescription(slug);
      await sleep(DELAY_MS);
      const record = { slug, parentSlug: parent, ...node, description, children: [] };
      if (!node || node.hasChildren) {
        const children = await fetchTreeChildren(slug);
        await sleep(DELAY_MS);
        record.children = children.map(child => child.slug);
        pending.push(...children.map(child => ({ slug: child.slug, parentSlug: slug, node: child })));
      }
      state.records[slug] = record;
      state.log.push(`${new Date().toISOString()} ${slug}`);
    }
  };

  const listChildren = async slug => fetchTreeChildren(slug);

  const run = async () => {
    if (state.running) return;
    state.running = true;
    try {
      while (state.queue.length) {
        const slug = state.queue[0];
        try {
          await scrapeSubtree(slug);
        } catch (error) {
          state.errors.push(`${slug}: ${error.message}`);
        }
        state.queue.shift();
      }
    } finally {
      state.running = false;
    }
  };

  const enqueue = (...slugs) => {
    state.queue.push(...slugs);
    run();
    return state.queue.length;
  };

  const IRRELEVANT_FIELDS = new Set([
    'Nom du producteur', 'Dépôt', 'Type de support', 'Type MIME', 'Téléversé',
    'Identifiant(s) alternatif(s)', 'Existence et lieu de conservation des copies',
  ]);

  const compact = ({ slug, parentSlug, id, type, children, description }) => ({
    slug, parentSlug, id, type, children,
    fields: Object.fromEntries(Object.entries(description.fields).filter(([label]) => !IRRELEVANT_FIELDS.has(label))),
    pdfUrls: description.pdfUrls,
  });

  const take = rootSlug => Object.values(state.records)
    .filter(record => record.slug === rootSlug || isInSubtree(record.slug, rootSlug))
    .map(compact);

  const isInSubtree = (slug, rootSlug) => {
    let current = state.records[slug];
    while (current) {
      if (current.parentSlug === rootSlug) return true;
      current = state.records[current.parentSlug];
    }
    return false;
  };

  const UPLOADS_PREFIX = 'https://davel-vd.ch/uploads/r/null/';

  const exportRecord = record => ({
    slug: record.slug,
    parent: record.parentSlug,
    type: record.type,
    children: record.children.length ? record.children : undefined,
    f: record.fields,
    pdf: record.pdfUrls[0]?.replace(UPLOADS_PREFIX, ''),
  });

  // Oversized on purpose: the browser tool writes results above its size limit to a file instead of the conversation.
  const padForFile = text => `${text}\n/*PAD*/${' x'.repeat(60000)}`;

  const exportSeries = (...rootSlugs) => padForFile(JSON.stringify(Object.fromEntries(
    rootSlugs.map(slug => [slug, take(slug).map(exportRecord)]),
  )));

  const status = () => ({
    running: state.running,
    queue: state.queue,
    records: Object.keys(state.records).length,
    errors: state.errors,
    last: state.log.slice(-3),
  });

  window.acv = { enqueue, take, exportSeries, status, listChildren, state };
  return 'acv scraper ready';
})();
