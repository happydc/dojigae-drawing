"""
도지개 3D 뷰어(HTML) 생성 — three.js, 브라우저에서 회전·확대
  python dojigae_viewer.py   -> output/dojigae_3d_viewer.html
"""
import os
import json
import base64
import numpy as np
import dojigae_core as core
import dojigae_3d as d3


def _pack(V, F):
    return dict(v=base64.b64encode(V.astype("<f4").tobytes()).decode(),
                f=base64.b64encode(F.astype("<u4").tobytes()).decode())


def build_html(keys=None):
    d3.N_ST = 121
    data = {}
    for k in keys or list(core.GRADES):
        G = core.GRADES[k]
        body, m, g = d3.body_with_holes(G["f"])
        bVF = d3._from_mf(body) if body is not None else m["body"]
        data[k] = dict(name=f"{k}형 {G['name']}", body=_pack(*bVF), leather=_pack(*m["leather"]),
                       sag=round(float(-g["yc0"].min()), 1))
    P = core.PARAM
    info = dict(L=P["L"], T=P["T"], bend=P["bend_x"], R=round(P["T"] * P["edge_r_ratio"], 1),
                groove=P["groove"], leather=P["leather"], lip=P["lip_h"], lipx=P["lip_len"],
                hole=P["hole_d"], cb=P["cb_d"])
    return HTML.replace("__DATA__", json.dumps(data)).replace("__INFO__", json.dumps(info))


HTML = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>각궁도지개 3D 뷰어</title>
<style>
 :root{--bg:#f4f1ea;--ink:#2b2620;--mut:#7a7166;--acc:#1f7a5a;--card:#fffdf8}
 *{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
  font-family:"Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",system-ui,sans-serif}
 #wrap{display:flex;flex-direction:column;height:100%}
 header{padding:14px 18px 8px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
 h1{font-size:17px;margin:0 12px 0 0;font-weight:700;letter-spacing:-.2px}
 .seg{display:flex;background:#e7e1d6;border-radius:9px;padding:3px}
 .seg button{border:0;background:transparent;padding:6px 12px;border-radius:7px;font:inherit;font-size:13px;color:var(--ink);cursor:pointer}
 .seg button.on{background:var(--card);box-shadow:0 1px 2px rgba(0,0,0,.12);font-weight:700}
 label.tg{font-size:13px;color:var(--mut);display:flex;gap:5px;align-items:center;cursor:pointer}
 #view{flex:1;position:relative;min-height:320px}
 canvas{display:block;width:100%;height:100%;touch-action:none;cursor:grab}
 #info{position:absolute;left:14px;bottom:14px;background:rgba(255,253,248,.92);border-radius:10px;padding:10px 12px;
   font-size:12px;line-height:1.6;box-shadow:0 1px 4px rgba(0,0,0,.08);max-width:260px}
 #info b{font-size:13px}
 #hint{position:absolute;right:14px;bottom:14px;font-size:11px;color:var(--mut)}
 .sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:-1px}
</style></head><body><div id="wrap">
<header>
 <h1>각궁도지개 3D</h1>
 <div class="seg" id="grades"></div>
 <div class="seg" id="views">
  <button data-v="iso" class="on">입체</button><button data-v="front">정면</button><button data-v="top">위</button><button data-v="end">끝</button>
 </div>
 <label class="tg"><input type="checkbox" id="pair"> 1벌(2개)</label>
 <label class="tg"><input type="checkbox" id="spin"> 자동 회전</label>
</header>
<div id="view"><canvas id="c"></canvas>
 <div id="info"></div>
 <div id="hint">드래그: 회전 · 휠/핀치: 확대 · 우클릭/두 손가락: 이동</div>
</div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const DATA=__DATA__, INFO=__INFO__;
const cv=document.getElementById('c'), box=document.getElementById('view');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xf4f1ea);
const cam=new THREE.PerspectiveCamera(30,1,1,5000);
scene.add(new THREE.HemisphereLight(0xfff6e8,0x6b5a46,0.55));
const sun=new THREE.DirectionalLight(0xffffff,0.85); sun.position.set(200,400,300); scene.add(sun);
const fill=new THREE.DirectionalLight(0xffffff,0.35); fill.position.set(-300,-100,-200); scene.add(fill);
const grid=new THREE.GridHelper(500,25,0xcfc6b8,0xe2dbcf); grid.position.y=-50; scene.add(grid);

function b64(s,T){const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new T(u.buffer)}
function geom(p){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(b64(p.v,Float32Array),3));
 g.setIndex(new THREE.BufferAttribute(b64(p.f,Uint32Array),1));g.computeVertexNormals();return g}
// 나뭇결 텍스처
function woodTex(){const c=document.createElement('canvas');c.width=1024;c.height=128;const x=c.getContext('2d');
 x.fillStyle='#c9a06a';x.fillRect(0,0,1024,128);
 for(let i=0;i<70;i++){const y=Math.random()*128,a=.05+Math.random()*.12;x.strokeStyle=`rgba(95,60,28,${a*1.6})`;x.lineWidth=.6+Math.random()*1.6;
  x.beginPath();x.moveTo(0,y);for(let t=0;t<=1024;t+=32)x.lineTo(t,y+Math.sin(t/90+i)*3*Math.random());x.stroke()}
 const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;return t}
const wood=new THREE.MeshStandardMaterial({color:0xffffff,map:woodTex(),roughness:.62,metalness:0});
const suede=new THREE.MeshStandardMaterial({color:0x1d7a52,roughness:.95,metalness:0});
// 위치 기반 UV(나뭇결이 길이 방향으로)
function addUV(g){const p=g.attributes.position,uv=new Float32Array(p.count*2);
 for(let i=0;i<p.count;i++){uv[2*i]=p.getX(i)/180;uv[2*i+1]=(p.getY(i)+p.getZ(i)*0.6)/60}
 g.setAttribute('uv',new THREE.BufferAttribute(uv,2))}

const root=new THREE.Group(); scene.add(root);
let cur=null;
function show(k){
 root.clear();
 const d=DATA[k], gb=geom(d.body), gl=geom(d.leather); addUV(gb);
 const one=new THREE.Group(); one.add(new THREE.Mesh(gb,wood)); one.add(new THREE.Mesh(gl,suede));
 one.position.set(-INFO.L/2,40,0); root.add(one);
 if(document.getElementById('pair').checked){const two=one.clone();two.position.z=INFO.T+12;one.position.z=-(INFO.T+12)/2;two.position.z=(INFO.T+12)/2;root.add(two)}
 cur=k;
 document.querySelectorAll('#grades button').forEach(b=>b.classList.toggle('on',b.dataset.k===k));
 document.getElementById('info').innerHTML=`<b>${d.name}</b><br>
 길이 ${INFO.L} · 너비 ${INFO.T} · 처짐 ${d.sag} mm<br>꺾임점: 왼쪽 끝에서 ${INFO.bend} mm<br>
 오목면 모서리 R${INFO.R} · 끈 감기 턱 h${INFO.lip} (끝에서 ${INFO.lipx})<br>
 <span class="sw" style="background:#1d7a52"></span>볼록면 C홈 ${INFO.groove} + 스웨이드 t${INFO.leather}<br>
 끈구멍 Ø${INFO.hole} · 매듭 보어 Ø${INFO.cb} (가죽 아래)`;
}
const gs=document.getElementById('grades');
Object.keys(DATA).forEach(k=>{const b=document.createElement('button');b.textContent=DATA[k].name;b.dataset.k=k;b.onclick=()=>show(k);gs.appendChild(b)});
document.getElementById('pair').onchange=()=>show(cur);

// 궤도 카메라
let th=-0.75, ph=0.3, dist=700, tgt=new THREE.Vector3(0,0,0);
const views={iso:[-0.75,0.3],front:[0,0.0],top:[0,1.5],end:[-1.5707,0.1]};
function place(){ph=Math.max(-1.55,Math.min(1.55,ph));
 cam.position.set(tgt.x+dist*Math.cos(ph)*Math.sin(th),tgt.y+dist*Math.sin(ph),tgt.z+dist*Math.cos(ph)*Math.cos(th));cam.lookAt(tgt)}
document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>{[th,ph]=views[b.dataset.v];tgt.set(0,0,0);
 document.querySelectorAll('#views button').forEach(x=>x.classList.toggle('on',x===b));place()});
const pts=new Map(); let last=null, pan=false;
cv.addEventListener('contextmenu',e=>e.preventDefault());
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.clientX,e.clientY]);pan=e.button===2||e.shiftKey;cv.style.cursor='grabbing'});
cv.addEventListener('pointerup',e=>{pts.delete(e.pointerId);last=null;cv.style.cursor='grab'});
cv.addEventListener('pointercancel',e=>{pts.delete(e.pointerId);last=null});
cv.addEventListener('pointermove',e=>{if(!pts.has(e.pointerId))return;const p=pts.get(e.pointerId),dx=e.clientX-p[0],dy=e.clientY-p[1];pts.set(e.pointerId,[e.clientX,e.clientY]);
 if(pts.size===2){const a=[...pts.values()],dd=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);if(last)dist*=last/dd;last=dd;doPan(dx/2,dy/2)}
 else if(pan)doPan(dx,dy); else{th-=dx*0.008;ph+=dy*0.008}
 dist=Math.max(150,Math.min(2500,dist));place()});
function doPan(dx,dy){const s=dist/900,r=new THREE.Vector3().setFromMatrixColumn(cam.matrix,0),u=new THREE.Vector3().setFromMatrixColumn(cam.matrix,1);
 tgt.addScaledVector(r,-dx*s).addScaledVector(u,dy*s)}
cv.addEventListener('wheel',e=>{e.preventDefault();dist*=Math.exp(e.deltaY*0.001);dist=Math.max(150,Math.min(2500,dist));place()},{passive:false});

function resize(){const w=box.clientWidth,h=box.clientHeight;renderer.setSize(w,h,false);cam.aspect=w/h;cam.updateProjectionMatrix()}
addEventListener('resize',resize);
function loop(){if(document.getElementById('spin').checked){th+=0.004;place()}renderer.render(scene,cam);requestAnimationFrame(loop)}
show(Object.keys(DATA)[Math.min(1,Object.keys(DATA).length-1)]);resize();place();loop();
</script></body></html>
"""

if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    fn = os.path.join("output", "dojigae_3d_viewer.html")
    with open(fn, "w", encoding="utf-8") as fp:
        fp.write(build_html())
    print(fn, os.path.getsize(fn) // 1024, "KB")
