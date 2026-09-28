// Локальная статика «как Cloudflare assets» (html_handling: auto-trailing-slash):
// /x.html → 307 /x, /x → x.html, /dir → 307 /dir/, /dir/ → dir/index.html, нет файла → 404.html (404).
// PORT=8080 node tools/dev-server.mjs
import http from 'node:http';
import { readFileSync, statSync, existsSync } from 'node:fs';
import { extname, join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = Number(process.env.PORT || 8080);
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json',
  '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8', '.ico': 'image/x-icon' };
const isFile = f => existsSync(f) && statSync(f).isFile();
const isDir = f => existsSync(f) && statSync(f).isDirectory();

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  const path = decodeURIComponent(url.pathname);
  const send = (status, file) => {
    res.writeHead(status, { 'content-type': TYPES[extname(file)] || 'application/octet-stream', 'cache-control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : readFileSync(file));
  };
  const go = to => { res.writeHead(307, { location: to + url.search }); res.end(); };
  const p = join(ROOT, path);
  if (path.endsWith('/index.html')) return go(path.slice(0, -'index.html'.length));
  if (path.endsWith('.html') && isFile(p)) return go(path.slice(0, -5));
  if (isFile(p)) return send(200, p);
  if (isDir(p)) return path.endsWith('/') ? (isFile(join(p, 'index.html')) ? send(200, join(p, 'index.html')) : send(404, join(ROOT, '404.html'))) : go(path + '/');
  if (isFile(p + '.html')) return send(200, p + '.html');
  send(404, join(ROOT, '404.html'));
}).listen(PORT, () => console.log('dev server :' + PORT + ' (как Cloudflare assets)'));
