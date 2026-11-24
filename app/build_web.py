# Собирает app/web/index.html из concepts/prototype-A.html.
# Из прототипа берутся стили приложения, данные, экраны, звуки и движок таймера;
# доска проверки, рамки устройств и иконки не берутся.
# Запуск: python build_web.py
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'concepts', 'prototype-A.html')
OUT = os.path.join(HERE, 'web', 'index.html')

src = open(SRC, encoding='utf-8').read()


def between(text, start, end):
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


css_app = between(src, '/* app */', '</style>')
css_root = re.search(r':root\{[^}]*\}', src).group(0)
css_app = css_root + '\n' + css_app
js = src[src.index('<script>') + len('<script>'):src.rindex('</script>')]
data_screens = between(js, '/* ================= data ================= */', '/* ================= overlap check ================= */')
data_screens = re.sub(r"function phoneHTML.*\n", '', data_screens)
data_screens = re.sub(r"function coverHTML.*\n", '', data_screens)
engine = between(js, '/* ================= live app ================= */', '/* ================= board ================= */')

# движок: один экран вместо двух рамок
engine = engine.replace(
    "const phoneHost=document.getElementById('livePhoneHost'),coverHost=document.getElementById('liveCoverHost');",
    "const phoneHost=document.getElementById('host'),coverHost=phoneHost;")
r0 = engine.index('function renderPhone(){')
r1 = engine.index('function setPhase(')
engine = engine[:r0] + '/*RENDER*/\n' + engine[r1:]
engine = re.sub(r"coverHost\.addEventListener\('click'.*\n", '', engine)
engine = re.sub(r"document\.getElementById\('spd'\).*\n", '', engine)
engine = engine.replace("phoneHost.addEventListener('click',e=>{",
                        "phoneHost.addEventListener('click',e=>{\n  if(MODE==='cover'){coverTap(e);return}")
engine = engine.replace("function playAction(k){", "function playAction(k){if(MUTE)return;")
engine = engine.replace("const sig={", "const sig0={")
engine = engine.replace("let lastT=performance.now();", "const sig={interval:()=>{if(!MUTE)sig0.interval()},warn:()=>{if(!MUTE)sig0.warn()},count:()=>{if(!MUTE)sig0.count()}};\nlet lastT=performance.now();")
# тик: после долгой паузы (экран гас, складывание) прокрутить время молча
engine = engine.replace("const prev=live.left;live.left-=dt*live.speed;",
                        "if(dt>2){fastForward(dt);save();render();return}\n  const prev=live.left;live.left-=dt*live.speed;")
engine = engine.replace("if(key!==live.lastShown){live.lastShown=key;",
                        "if(key!==live.lastShown){live.lastShown=key;save();")

for must in ['/*RENDER*/', "if(MODE==='cover')", 'if(MUTE)return;', 'fastForward(dt)', 'save();render']:
    if must not in engine:
        sys.exit('не нашёл место для правки: ' + must)

app_js = r'''
/* ================= обёртка приложения ================= */
let MODE='phone',MUTE=false,SC=1;
const NATIVE=window.Native||null;
if(NATIVE){navigator.vibrate=p=>{try{NATIVE.vibrate(JSON.stringify(Array.isArray(p)?p:[p]))}catch(e){}return true}}
function keepAwake(){if(NATIVE)try{NATIVE.keepAwake(!!cfg.awake)}catch(e){}}
// Режимы по пропорции окна H/W: 'phone' — вертикаль (от 1.4), 'cover' — внешний экран (почти квадрат, Flip6 около 1.04),
// 'land' — горизонталь внутреннего экрана (меньше 0.75, Flip6 около 0.41).
// CV(): показывать раскладку внешнего экрана 286×298 — на внешнем экране и в горизонтали во время тренировки.
const CV=()=>MODE==='cover'||(MODE==='land'&&live.screen==='run');
function layout(){
  const W=innerWidth,H=innerHeight;
  const ae=document.activeElement;if(ae&&ae.tagName==='INPUT'&&MODE!=='cover')return false;
  const r=H/W,m=r>=1.4?'phone':r>=0.75?'cover':'land';
  const ch=m!==MODE;MODE=m;
  if(m==='cover'){SC=Math.min(W/286,H/298)}else if(m==='land'){SC=Math.min(W/LAND_W,H/LAND_H)}else{SC=Math.min(W/286,H/690)}
  return ch;
}
// поля окна вокруг экрана красим тем же цветом, что фон экрана (с учётом заливки фазой)
function paintBody(){const s=document.getElementById('scr');if(!s)return;
  const r=s.querySelector('.runscr'),bg=r&&getComputedStyle(r).backgroundColor;
  const fill=bg&&bg!=='rgba(0, 0, 0, 0)';
  if(fill)s.style.background=bg; // иначе по краю экрана просвечивает тёмный фон полоской
  document.body.style.background=fill?bg:getComputedStyle(s).backgroundColor}
function frame(inner,h){
  const W=innerWidth,H=innerHeight,f=F(cfg.font);
  let k=SC,w=286,hh,left,top=0;
  if(CV()){k=Math.min(W/286,H/298);hh=298;top=(H-298*k)/2}   // 286×298 по центру окна
  else if(MODE==='land'){hh=H/k;w=live.screen==='menu'?Math.min(LAND_MAXW,Math.floor(W/k)):Math.min(480,Math.floor(W/k))}
  else hh=Math.max(690,H/k);
  left=(W-w*k)/2;
  setTimeout(paintBody,0);
  return `<div id="scr" class="scr A" style="--df:${f.css}${FB};--dw:${f.w};${themeVars(cfg)}left:${left}px;top:${top}px;width:${w}px;height:${hh}px;transform:scale(${k})">${inner}</div>`;
}
// горизонталь во время тренировки: касание как на внешнем экране (пауза/продолжить)
CLICK.unshift(e=>{if(MODE==='land'&&live.screen==='run'){coverTap(e);return true}return false});
function renderPhone(){
  if(CV())return;
  const inner=MODE==='land'&&live.screen==='menu'?scrLand(cfg):screenHTML();
  const st=phoneHost.querySelector('.scroll')?.scrollTop||0;
  phoneHost.innerHTML=frame(inner);
  const sc=phoneHost.querySelector('.scroll');if(sc)sc.scrollTop=st;
}
function renderCover(){
  if(!CV())return;
  phoneHost.innerHTML=frame(coverInner());
}
function render(){renderPhone();renderCover();save();keepAwake()}
function renderAll(){render()}
function fastForward(el){
  if(live.screen!=='run'||live.paused||live.phase==='done')return;
  MUTE=true;
  try{while(el>0&&live.phase!=='done'){if(live.left>el){live.left-=el;el=0}else{el-=live.left;live.left=0;endPhase()}}}finally{MUTE=false}
}
function save(){
  try{localStorage.setItem('bt_cfg',JSON.stringify(cfg));
    localStorage.setItem('bt_live',JSON.stringify({live:{screen:live.screen,phase:live.phase,idx:live.idx,left:live.left,dur:live.dur,paused:live.paused},t:Date.now()}))}catch(e){}
}
function restore(){
  loadCfg();
  try{const s=JSON.parse(localStorage.getItem('bt_live')||'null');
    if(s&&s.live&&s.live.screen==='run'&&s.live.phase!=='done'){Object.assign(live,s.live);fastForward((Date.now()-s.t)/1000)}}catch(e){}
}
window.goBack=function(){
  if(MODE==='cover'&&live.cover==='setup'&&live.screen!=='run'){live.cover='idle';render();return true}
  if(live.screen!=='run'&&live.screen!=='menu'){const b=backOf(live.screen);if(b){live.screen=b;render();return true}}
  if(live.screen==='run'&&live.phase!=='done'&&!live.paused){live.paused=true;render();return true}
  if(live.screen==='run'){live.screen='menu';render();return true}
  return false;
};
document.addEventListener('visibilitychange',()=>{if(document.hidden)save()});
addEventListener('resize',()=>{const ch=layout();if(ch||MODE==='cover'||!document.activeElement||document.activeElement.tagName!=='INPUT')render()});
let lastWH='';
setInterval(()=>{const wh=innerWidth+'x'+innerHeight;if(wh!==lastWH){lastWH=wh;const ae=document.activeElement;if(!ae||ae.tagName!=='INPUT'){layout();render()}}},300);
restore();layout();render();
document.fonts&&document.fonts.ready.then(()=>{for(const k in MET)delete MET[k];render()});
'''

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>Dumb Boxing Timer</title>
<link rel="stylesheet" href="fonts/fonts.css">
<link rel="stylesheet" href="ph/regular/style.css">
<link rel="stylesheet" href="ph/fill/style.css">
<link rel="stylesheet" href="ph/bold/style.css">
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
html,body{{height:100%;background:#0f1012;overflow:hidden;overscroll-behavior:none}}
#host{{position:fixed;inset:0}}
#scr{{position:absolute;transform-origin:0 0;overflow:hidden}}
{css_app}
</style>
</head>
<body>
<div id="host"></div>
<script src="gongs.js"></script>
<script>
{data_screens}
{engine.replace('/*RENDER*/', '')}
{app_js}
</script>
</body>
</html>
'''
open(OUT, 'w', encoding='utf-8', newline='\n').write(html)

# Гонги Zvukipro.com не в git (условия сайта запрещают выкладывать файлы): concepts/sounds/gongs.js есть только у автора.
# Есть файл — кладём его рядом со страницей, нет — приложение собирается без гонгов.
import shutil
GONGS = os.path.join(HERE, '..', 'concepts', 'sounds', 'gongs.js')
GONGS_OUT = os.path.join(HERE, 'web', 'gongs.js')
if os.path.exists(GONGS):
    shutil.copyfile(GONGS, GONGS_OUT)
    print('gongs: yes')
else:
    if os.path.exists(GONGS_OUT):
        os.remove(GONGS_OUT)
    print('gongs: none, building without them')
print('OK', OUT, os.path.getsize(OUT) // 1024, 'KB')
