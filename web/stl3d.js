// 3D 프린트용 STL 만들기 (브라우저, manifold-3d WASM)
// 파이썬(dojigae_3d.export_stl)과 같은 결과: _model / _print / (베드 초과 시) _print_A, _print_B
let W = null;

export async function initManifold(url) {
  if (W) return W;
  const Module = (await import(url)).default;
  W = await Module();
  W.setup();
  return W;
}

function toManifold(v, f) {
  const { Manifold, Mesh } = W;
  const mesh = new Mesh({ numProp: 3, vertProperties: new Float32Array(v), triVerts: new Uint32Array(f) });
  mesh.merge();
  return new Manifold(mesh);
}

function cylAlong([p, a, len, d], seg = 48) {
  // 원기둥(+Z 축) → 축 a 방향, 시작점 p
  const n = Math.hypot(a[0], a[1], a[2]); a = a.map(x => x / n);
  let u = Math.abs(a[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  let w = [a[1] * u[2] - a[2] * u[1], a[2] * u[0] - a[0] * u[2], a[0] * u[1] - a[1] * u[0]];
  const wn = Math.hypot(...w); w = w.map(x => x / wn);
  u = [w[1] * a[2] - w[2] * a[1], w[2] * a[0] - w[0] * a[2], w[0] * a[1] - w[1] * a[0]];
  const M = [w[0], w[1], w[2], 0, u[0], u[1], u[2], 0, a[0], a[1], a[2], 0, p[0], p[1], p[2], 1];  // column-major
  return W.Manifold.cylinder(len, d / 2, d / 2, seg).transform(M);
}

function meshArrays(m) {
  const g = m.getMesh();
  const np = g.numProp, vp = g.vertProperties, n = vp.length / np;
  const v = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { v[3 * i] = vp[np * i]; v[3 * i + 1] = vp[np * i + 1]; v[3 * i + 2] = vp[np * i + 2]; }
  return { v, f: g.triVerts };
}

function layFlat(v) {
  const mn = [Infinity, Infinity, Infinity];
  for (let i = 0; i < v.length; i++) mn[i % 3] = Math.min(mn[i % 3], v[i]);
  const o = new Float32Array(v.length);
  for (let i = 0; i < v.length; i++) o[i] = v[i] - mn[i % 3];
  return o;
}

function extentX(v) {
  let a = Infinity, b = -Infinity;
  for (let i = 0; i < v.length; i += 3) { a = Math.min(a, v[i]); b = Math.max(b, v[i]); }
  return b - a;
}

export function stlBinary(parts) {
  // parts: [{v: Float32Array|Array, f: Uint32Array|Array}]  (여러 셸을 한 파일에)
  let nt = 0; for (const p of parts) nt += p.f.length / 3;
  const buf = new ArrayBuffer(84 + nt * 50), dv = new DataView(buf);
  const hdr = 'dojigae'; for (let i = 0; i < hdr.length; i++) dv.setUint8(i, hdr.charCodeAt(i));
  dv.setUint32(80, nt, true);
  let o = 84;
  for (const { v, f } of parts) {
    for (let t = 0; t < f.length; t += 3) {
      const a = f[t] * 3, b = f[t + 1] * 3, c = f[t + 2] * 3;
      const ux = v[b] - v[a], uy = v[b + 1] - v[a + 1], uz = v[b + 2] - v[a + 2];
      const wx = v[c] - v[a], wy = v[c + 1] - v[a + 1], wz = v[c + 2] - v[a + 2];
      let nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
      const ln = Math.hypot(nx, ny, nz) || 1; nx /= ln; ny /= ln; nz /= ln;
      for (const q of [nx, ny, nz]) { dv.setFloat32(o, q, true); o += 4; }
      for (const k of [a, b, c]) for (let j = 0; j < 3; j++) { dv.setFloat32(o, v[k + j], true); o += 4; }
      dv.setUint16(o, 0, true); o += 2;
    }
  }
  return new Uint8Array(buf);
}

export function makeStl(job, bed) {
  // 반환: [{name, data(Uint8Array)}]
  let body = toManifold(job.body.v, job.body.f);
  for (const c of job.cuts) body = body.subtract(cylAlong(c));
  const B = meshArrays(body);
  const out = [];
  out.push({ name: job.base + '_model.stl', data: stlBinary([B, { v: job.leather.v, f: job.leather.f }]) });
  out.push({ name: job.base + '_print.stl', data: stlBinary([{ v: layFlat(B.v), f: B.f }]) });
  if (extentX(B.v) > bed) {
    let b = body;
    for (const c of job.pins) b = b.subtract(cylAlong(c, 32));
    const [right, left] = b.splitByPlane([1, 0, 0], job.xs);
    for (const [tag, part] of [['_print_A.stl', left], ['_print_B.stl', right]]) {
      const M = meshArrays(part);
      out.push({ name: job.base + tag, data: stlBinary([{ v: layFlat(M.v), f: M.f }]) });
    }
  }
  return out;
}
