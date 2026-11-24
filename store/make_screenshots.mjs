// Скриншоты для Google Play из собранного приложения (app/web/index.html).
// Нужен запущенный сервер на http://localhost:8765 (папка app/web) и Chrome.
// Запуск: node store/make_screenshots.mjs [lang]   (по умолчанию en) → store/screenshots/
import { spawn } from 'child_process';
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const HERE = dirname(fileURLToPath(import.meta.url));
const LANG = process.argv[2] || 'en';
const OUT = join(HERE, LANG === 'en' ? 'screenshots' : 'screenshots-' + LANG);
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9341;
const URL = 'http://localhost:8765/index.html';
mkdirSync(OUT, { recursive: true });

// кадры: имя, размер окна в CSS-пикселях (×3 = итог), скрипт состояния
const PN = { en: ['Sparring', 'Bag work'], ru: ['Спарринг', 'Мешок'], es: ['Sparring', 'Saco'], zh: ['实战', '沙袋'] }[LANG] || ['Sparring', 'Bag work'];
const PHONE = [361, 720], COVER = [360, 347];
const base = `localStorage.clear();for(const k in cfg)delete cfg[k];Object.assign(cfg,clone(DEF));cfg.lang='${LANG}';live.cover='idle';`;
const run = (phase, left, dur, extra = '') =>
  `startWorkout();live.phase='${phase}';live.idx=4;live.dur=${dur};live.left=${left};live.paused=false;live.speed=0;${extra}render();`;
const SHOTS = [
  ['1-menu', PHONE, `live.screen='menu';render();`],
  ['2-round', PHONE, run('round', 134.4, 180)],
  ['3-fill', PHONE, `cfg.fill='screen';` + run('round', 3.4, 9)],
  ['4-rest', PHONE, run('rest', 41.4, 60)],
  ['5-theme', PHONE, `live.screen='theme';render();`],
  ['6-presets', PHONE, `PRE[0]={round:180,rest:60,rounds:12,prep:10,name:null,full:null};PRE[1]={round:120,rest:30,rounds:6,prep:10,name:'${PN[0]}',full:{fill:'screen'}};PRE[2]={round:60,rest:20,rounds:10,prep:5,name:'${PN[1]}',full:null};PRE[3]={round:30,rest:15,rounds:8,prep:5,name:null,full:null};PRE[4]=null;live.screen='presets';render();`],
  ['7-sounds', PHONE, `live.screen='sounds';render();`],
  ['8-cover', COVER, run('round', 134.4, 180)],
];

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, '--no-first-run',
  '--user-data-dir=' + join(process.env.TEMP || HERE, 'bt_shots_profile'), 'about:blank'], { stdio: 'ignore' });
const sleep = t => new Promise(r => setTimeout(r, t));
let ws;
for (let i = 0; i < 40 && !ws; i++) {
  await sleep(250);
  try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); ws = l.find(x => x.type === 'page')?.webSocketDebuggerUrl } catch (e) { }
}
if (!ws) { console.error('Chrome не ответил'); chrome.kill(); process.exit(1) }
const s = new WebSocket(ws); await new Promise(r => s.onopen = r);
let id = 0; const wait = {};
s.onmessage = m => { const d = JSON.parse(m.data); if (wait[d.id]) { wait[d.id](d); delete wait[d.id] } };
const call = (method, params = {}) => new Promise(r => { const i = ++id; wait[i] = r; s.send(JSON.stringify({ id: i, method, params })) });
const ev = async e => { const r = await call('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails)); return r };

await call('Page.enable');
for (const [name, [w, h], state] of SHOTS) {
  await call('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 3, mobile: true });
  await call('Page.navigate', { url: URL }); await sleep(1500);
  await ev(`(async()=>{await document.fonts.ready;${base}layout();${state};await new Promise(r=>setTimeout(r,400));return MODE})()`);
  await sleep(300);
  const r = await call('Page.captureScreenshot', { format: 'png' });
  writeFileSync(join(OUT, name + '.png'), Buffer.from(r.result.data, 'base64'));
  console.log('OK', name);
}
await ev(`localStorage.clear()`);
s.close(); chrome.kill();
