// Медленная сеть для живого сайта: HTTP-прокси (CONNECT) с задержкой и общей полосой, как «Fast 3G»
// в DevTools (задержка 562 мс туда-обратно, 1,44 Мбит/с вниз, 675 кбит/с вверх). В отличие от
// эмуляции DevTools, замедляет и запросы service worker. Если задан HTTPS_PROXY — идёт через него.
// TPORT=8899 node tools/audit/throttle-proxy.mjs   → браузер: THROTTLE_PROXY=http://127.0.0.1:8899
import http from 'node:http';
import net from 'node:net';

const PORT = Number(process.env.TPORT || 8899);
const ONE_WAY = Number(process.env.ONE_WAY_MS ?? 281);
const DOWN = Number(process.env.DOWN_BPS ?? 180000), UP = Number(process.env.UP_BPS ?? 84375);
const UPSTREAM = process.env.UPSTREAM_PROXY ?? process.env.HTTPS_PROXY ?? '';

// Общая полоса: когда закончится передача очередного куска
const link = rate => { let free = 0; return n => { const now = Date.now(); free = Math.max(now, free) + (rate ? n / rate * 1000 : 0); return free - now; }; };
const downLink = link(DOWN), upLink = link(UP);

// Куски приходят по порядку, каждый — через задержку в одну сторону плюс ожидание полосы
function shaped(src, dst, lk) {
  let last = 0;
  src.on('data', chunk => {
    const now = Date.now();
    const at = Math.max(last, now + ONE_WAY + lk(chunk.length));
    last = at;
    setTimeout(() => { if (!dst.destroyed) dst.write(chunk); }, at - now);
  });
  src.on('end', () => setTimeout(() => dst.end(), Math.max(0, last - Date.now())));
  src.on('error', () => dst.destroy());
  src.on('close', () => setTimeout(() => dst.destroy(), Math.max(0, last - Date.now()) + 50));
}

function tunnel(target, cb) {
  if (!UPSTREAM) { const s = net.connect(Number(target.split(':')[1] || 443), target.split(':')[0], () => cb(null, s)); s.on('error', e => cb(e)); return; }
  const u = new URL(UPSTREAM);
  const s = net.connect(Number(u.port || 80), u.hostname, () => {
    const auth = u.username ? `Proxy-Authorization: Basic ${Buffer.from(decodeURIComponent(u.username) + ':' + decodeURIComponent(u.password)).toString('base64')}\r\n` : '';
    s.write(`CONNECT ${target} HTTP/1.1\r\nHost: ${target}\r\n${auth}\r\n`);
  });
  let buf = Buffer.alloc(0);
  const onData = d => {
    buf = Buffer.concat([buf, d]);
    const i = buf.indexOf('\r\n\r\n');
    if (i < 0) return;
    s.off('data', onData);
    const status = Number(buf.toString('latin1', 0, i).split(' ')[1]);
    if (status !== 200) { s.destroy(); cb(new Error('upstream ' + status)); return; }
    const rest = buf.subarray(i + 4);
    cb(null, s, rest);
  };
  s.on('data', onData);
  s.on('error', e => cb(e));
}

const server = http.createServer((req, res) => { res.writeHead(405); res.end('CONNECT only'); });
server.on('connect', (req, client, head) => {
  let done = false;
  tunnel(req.url, (err, up, rest) => {
    if (done) return; done = true;
    if (err) { client.end('HTTP/1.1 502 Bad Gateway\r\n\r\n'); return; }
    client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    if (head?.length) up.write(head);
    if (rest?.length) client.write(rest);
    shaped(client, up, upLink);
    shaped(up, client, downLink);
  });
  client.on('error', () => {});
});
server.listen(PORT, '127.0.0.1', () => console.log(`throttle proxy :${PORT} (${ONE_WAY * 2} мс, ${DOWN} Б/с вниз, ${UP} Б/с вверх)${UPSTREAM ? ' → ' + UPSTREAM.replace(/\/\/.*@/, '//***@') : ''}`));
