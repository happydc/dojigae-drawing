"""
도지개 3D 모델 생성 — dojigae_core의 형상(곡선, C홈, 오목면 모서리 R, 끈 감기 턱, 끈구멍·매듭 보어)을
단면 스윕 + 불리언(manifold3d)으로 만들어 STL로 저장.
  python dojigae_3d.py
    -> output/..._model.stl         : 목재 + 가죽 (보기용)
    -> output/..._print.stl         : 3D 프린트용 목재 본체(가죽 제외, 눕힌 자세, z>=0)
    -> output/..._print_A/B.stl     : 베드보다 길면 2분할 + 맞춤 핀 구멍
"""
import os
import struct
import numpy as np
import dojigae_core as core

try:
    import manifold3d as mf
except Exception:  # manifold3d 없으면 구멍 없이 출력
    mf = None

PIN_D, PIN_DEPTH = 5.3, 12.0   # 분할 맞춤 핀 구멍(Ø5 핀용)

N_ST = 241      # 길이 방향 단면 수
N_BOT = 31      # 볼록면(C홈) 분할
N_TOP = 49      # 오목면(라운드) 분할


def _convex_hit(g, C, n):
    ts = np.linspace(0, 150, 3001)
    px, py = C[0] + ts * n[0], C[1] + ts * n[1]
    j = int(np.argmax(py - np.interp(px, g["xv"], g["yv"]) <= 0))
    return np.array([px[j], py[j]])


def build_mesh(f):
    """반환: dict(body=(V,F), leather=(V,F)) — V: (n,3) mm, F: (m,3) int.
    좌표: X=길이, Y=높이(오목면 위), Z=너비(두께 방향)"""
    P = core.PARAM
    g = core.geometry(f)
    T, R, gd, lt = P["T"], P["T"] * P["edge_r_ratio"], P["groove"], P["leather"]
    idx = np.linspace(0, len(g["x"]) - 1, N_ST).astype(int)
    ub = np.linspace(0, T, N_BOT)
    ut = np.linspace(T, 0, N_TOP)
    gp = core.groove_profile(ub, T, gd)
    cp = core.crown_profile(ut, T, R)
    rings, lrings_in, lrings_out = [], [], []
    for k in idx:
        n = np.array([g["nx"][k], g["ny"][k]])          # 아래(볼록면) 방향
        C = np.array([g["xc"][k], g["yc"][k]])
        V = _convex_hit(g, C, n)
        bot = [(V - n * gp[i], ub[i] - T / 2) for i in range(N_BOT)]        # 홈은 목재 안쪽(-n)으로
        top = [(C + n * cp[i], ut[i] - T / 2) for i in range(N_TOP)]
        rings.append([(p[0], p[1], z) for p, z in bot + top])
        lrings_in.append([(p[0], p[1], z) for p, z in bot])
        lrings_out.append([(p[0] + n[0] * lt, p[1] + n[1] * lt, z) for p, z in bot])
    body = _loft(np.array(rings))
    leather = _shell(np.array(lrings_in), np.array(lrings_out))
    return dict(body=body, leather=leather)


def _loft(R, invert=False):
    ns, m, _ = R.shape
    V = R.reshape(-1, 3)
    F = []
    for i in range(ns - 1):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            c, d = a + m, b + m
            F += [(a, c, b), (b, c, d)]
    # 끝 마구리: 중심점 팬
    for i, flip in ((0, True), (ns - 1, False)):
        ctr = len(V)
        V = np.vstack([V, R[i].mean(0)])
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            F.append((ctr, a, b) if flip else (ctr, b, a))
    F = np.array(F)
    return V, (F[:, ::-1] if invert else F)


def _shell(Ri, Ro):
    """가죽: 안쪽면/바깥면 + 옆면 + 끝면을 가진 얇은 판"""
    ns, m, _ = Ri.shape
    ring = np.concatenate([Ri, Ro[:, ::-1]], axis=1)   # 안쪽 왼→오, 바깥 오→왼
    return _loft(ring, invert=True)


def write_stl(fn, V, F, name=b"dojigae"):
    tri = V[F]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1, keepdims=True); ln[ln == 0] = 1
    nrm = nrm / ln
    with open(fn, "wb") as fp:
        fp.write(name.ljust(80, b" "))
        fp.write(struct.pack("<I", len(F)))
        rec = np.zeros(len(F), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
        rec["n"] = nrm; rec["v"] = tri
        fp.write(rec.tobytes())


def _to_mf(V, F):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))


def _from_mf(M):
    m = M.to_mesh()
    return np.asarray(m.vert_properties, float)[:, :3], np.asarray(m.tri_verts, int)


def _cyl_along(p0, axis, length, d, seg=48):
    """p0에서 axis(단위벡터) 방향으로 길이 length, 지름 d인 원기둥"""
    a = np.asarray(axis, float); a /= np.linalg.norm(a)
    u = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    w = np.cross(a, u); w /= np.linalg.norm(w); u = np.cross(w, a)
    M = [[w[0], u[0], a[0], p0[0]], [w[1], u[1], a[1], p0[1]], [w[2], u[2], a[2], p0[2]]]
    return mf.Manifold.cylinder(length, d / 2, d / 2, seg).transform(M)


def body_with_holes(f):
    """반환: (body Manifold, leather (V,F), geometry)"""
    m = build_mesh(f)
    g = core.geometry(f)
    if mf is None:
        return None, m, g
    P = core.PARAM
    body = _to_mf(*m["body"])
    cut = []
    for (C, V, T_, N, h) in core.hole_lines(g):
        n3 = np.array([N[0], N[1], 0.0])                      # 아래(볼록면) 방향
        top = np.array([C[0], C[1], 0.0]) - n3 * 10            # 오목면 위에서 시작
        bot = np.array([V[0], V[1], 0.0])
        cb_top = bot - n3 * (P["groove"] + P["cb_depth"])      # 보어 바닥(홈 중앙 기준 깊이)
        cut.append(_cyl_along(top, n3, np.linalg.norm(cb_top - top) + 0.5, P["hole_d"]))
        cut.append(_cyl_along(cb_top, n3, np.linalg.norm(bot - cb_top) + 5, P["cb_d"]))
    for c in cut:
        body = body - c
    return body, m, g


def _fname(outdir, k, tag):
    return os.path.join(outdir, f"dojigae_L{core.PARAM['L']:.0f}_{k}_{core.GRADES[k]['code']}_{tag}.stl")


def _lay_flat(V):
    """옆면(판재면)을 바닥에: Z=두께 방향 그대로, 최소점 원점으로"""
    return V - V.min(0)


def export_stl(outdir=".", keys=None, factors=None, params=None, bed=250.0):
    """보기용 모델 + 3D 프린트용 STL. bed: 프린터 베드 최대 길이(mm), 초과 시 2분할"""
    if params:
        core.PARAM.update(params)
    if factors:
        for k, f in factors.items():
            core.GRADES[k]["f"] = f
    os.makedirs(outdir, exist_ok=True)
    files = []
    for k in keys or list(core.GRADES):
        body, m, g = body_with_holes(core.GRADES[k]["f"])
        bV, bF = _from_mf(body) if body is not None else m["body"]
        lV, lF = m["leather"]
        fn = _fname(outdir, k, "model")
        write_stl(fn, np.vstack([bV, lV]), np.vstack([bF, lF + len(bV)]))
        files.append(fn)
        # 3D 프린트용 (목재 본체만)
        V = _lay_flat(bV)
        fn = _fname(outdir, k, "print")                          # 통짜(큰 프린터용)
        write_stl(fn, V, bF)
        files.append(fn)
        if body is not None and np.ptp(V[:, 0]) > bed:
            files += _split_print(outdir, k, body, g)
    return files


def _split_print(outdir, k, body, g):
    """꺾임점에서 2분할 + 양쪽에 맞춤 핀 구멍"""
    xs = g["ub"] * core.PARAM["L"]
    yc = float(np.interp(xs, g["xc"], g["yc"]))
    yv = float(np.interp(xs, g["xv"], g["yv"]))
    dep = yc - yv
    pins = []
    for r in (0.30, 0.65):
        p = np.array([xs - PIN_DEPTH, yv + dep * r, 0.0])
        pins.append(_cyl_along(p, [1, 0, 0], 2 * PIN_DEPTH, PIN_D, 32))
    b = body
    for p in pins:
        b = b - p
    left, right = b.split_by_plane([1.0, 0.0, 0.0], xs)    # 법선 쪽(오른쪽)이 첫 번째
    out = []
    for tag, part in (("print_A", right), ("print_B", left)):
        V, F = _from_mf(part)
        fn = _fname(outdir, k, tag)
        write_stl(fn, _lay_flat(V), F)
        out.append(fn)
    return out


if __name__ == "__main__":
    for f in export_stl("output"):
        print(f)
