const PDFJS_BUILD = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build';
const RANGE_BYTES = 1048576;
const RENDER_SCALE = 300 / 72;
const RENDER_MAX_SIDE = 8000;
const JPEG_QUALITY = 0.9;
const RENDER_CACHE = 20;

const loadPdfjs = () => import(`${PDFJS_BUILD}/pdf.min.mjs`).then(pdfjs => {
  pdfjs.GlobalWorkerOptions.workerSrc = `${PDFJS_BUILD}/pdf.worker.min.mjs`;
  return pdfjs;
});

const createPdfjsReader = (urlOf, load = loadPdfjs) => {
  const documents = new Map();
  const images = new Map();
  let library = null;

  const documentOf = path => {
    if (!documents.has(path)) {
      library ??= load().catch(error => { library = null; throw error; });
      documents.set(path, library
        .then(pdfjs => pdfjs.getDocument({ url: urlOf(path), disableAutoFetch: true, disableStream: true, rangeChunkSize: RANGE_BYTES }).promise)
        .catch(error => { documents.delete(path); throw error; }));
    }
    return documents.get(path);
  };

  const openDoc = async path => {
    const pdf = await documentOf(path);
    // getDownloadInfo() would wait for the whole file, which auto-fetch being off never loads.
    const { contentLength } = await pdf.getMetadata();
    return { url: urlOf(path), size: contentLength, pages: Array.from({ length: pdf.numPages }) };
  };

  const render = async page => {
    const { width, height } = page.getViewport({ scale: 1 });
    const viewport = page.getViewport({ scale: Math.min(RENDER_SCALE, RENDER_MAX_SIDE / Math.max(width, height)) });
    const canvas = Object.assign(document.createElement('canvas'), { width: Math.round(viewport.width), height: Math.round(viewport.height) });
    await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
    page.cleanup();
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
  };

  const imageOf = async (path, n) => {
    const key = `${path}#${n}`;
    if (images.has(key)) return images.get(key);
    const pdf = await documentOf(path);
    const source = URL.createObjectURL(await render(await pdf.getPage(n)));
    images.set(key, source);
    if (images.size > RENDER_CACHE) {
      const [oldest, oldSource] = images.entries().next().value;
      URL.revokeObjectURL(oldSource);
      images.delete(oldest);
    }
    return source;
  };

  // The rendered image already includes the page's own rotation.
  const pageInfo = async () => ({ rotate: 0 });

  return { openDoc, imageOf, pageInfo };
};
