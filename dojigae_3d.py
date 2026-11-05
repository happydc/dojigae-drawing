"""
도지개 3D 모델 생성 — dojigae_core의 형상(곡선, C홈, 오목면 모서리 R, 끈 감기 턱)을
단면 스윕으로 메시화하여 STL로 저장.  (끈구멍·매듭 보어는 표시하지 않음)
  python dojigae_3d.py           -> output/dojigae_L360_<등급>.stl
"""
import os
import struct
import numpy as np
import dojigae_core as core

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


def export_stl(outdir=".", keys=None, factors=None, params=None):
    if params:
        core.PARAM.update(params)
    if factors:
        for k, f in factors.items():
            core.GRADES[k]["f"] = f
    os.makedirs(outdir, exist_ok=True)
    files = []
    for k in keys or list(core.GRADES):
        m = build_mesh(core.GRADES[k]["f"])
        V = np.vstack([m["body"][0], m["leather"][0]])
        F = np.vstack([m["body"][1], m["leather"][1] + len(m["body"][0])])
        fn = os.path.join(outdir, f"dojigae_L{core.PARAM['L']:.0f}_{k}_{core.GRADES[k]['code']}.stl")
        write_stl(fn, V, F)
        files.append(fn)
    return files


if __name__ == "__main__":
    for f in export_stl("output"):
        print(f)
