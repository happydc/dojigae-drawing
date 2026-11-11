"""
도지개 도면 생성 코어 — 도지개 3종(중곡 / 중곡~심곡 표준 / 심곡) 제작도면
PDF: A3, 정면도 1:1 (형판으로 바로 출력 가능)   DXF: 1:1
  python3 dojigae_v2.py
치수 수정: PARAM / GRADES
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Arc
import os
import ezdxf

def _setup_font():
    names = {f.name for f in fm.fontManager.ttflist}
    for cand in ("Malgun Gothic", "맑은 고딕", "NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP", "AppleGothic"):
        if cand in names:
            plt.rcParams["font.family"] = cand
            return cand
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(getattr(__import__("sys"), "_MEIPASS", here), "assets", "fonts", "NanumGothic-Regular.ttf")
    for p in (r"C:\Windows\Fonts\malgun.ttf", bundled, "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.exists(p):
            fm.fontManager.addfont(p)
            plt.rcParams["font.family"] = fm.FontProperties(fname=p).get_name()
            return p
    return None


_setup_font()
plt.rcParams["axes.unicode_minus"] = False

PARAM = dict(
    L=360.0,        # 전체 길이 mm
    T=30.0,         # 두께(판재 두께, 활 너비 방향) mm
    d_end=22.0,     # 끝단 높이 mm
    d_bend=40.0,    # 꺾임부 높이 mm
    hole=10.0,      # 끈구멍 지름
    hole_off=16.0,  # 끝에서 구멍 중심까지
    scallop_r=6.0,  # 리커브 머리 끝면 오목홈 반경
    groove=2.0,     # 볼록면(접촉면) C자 홈 깊이(중앙)
    groove_rim=0.0, # 테두리 없음 — 모서리에서 바로 시작
    leather=2.0,    # 접촉면 가죽(스웨이드) 두께
    hole_d=7.0,     # 끈구멍(오목면 쪽, 끈 나오는 쪽) 정공
    cb_d=12.0, cb_depth=8.0,  # 가죽쪽 카운터보어(매듭 숨김)
    corner_r=3.0,
    lip_h=2.5,      # 끈 감기 턱 높이(오목면 쪽)
    lip_len=8.0,    # 끝에서 턱까지(돋운 블록 길이)
    lip_fillet=4.0, # 턱 안쪽 둥근 전이 길이
    fore=1.30,      # 곡선 보정계수(처짐 전체 배율)
    bend_x=167.0,   # 왼쪽 끝 → 꺾임점(오목면 최저점) 거리 mm
    edge_r_ratio=0.45,  # 오목면 쪽(가죽 반대쪽) 모서리 R = T × 비율
    recurve_l=0.0,      # 볼록면 왼쪽 끝 되굽힘 % (0 = 되굽힘 없이 직선 연장, 100 = 원래 곡선대로 다시 휨)
    recurve_r=0.0,      # 볼록면 오른쪽 끝 되굽힘 %
)
GRADES = {
    "1": dict(name="중곡", f=0.75, code="DJG-1",
              use="완만한 굴곡. 길이 잘 든 활, 무른 활, 가벼운 해궁·보관용."),
    "2": dict(name="중곡~심곡 (표준)", f=1.00, code="DJG-2",
              use="표준 굴곡. 일반 각궁 해궁·얹기용."),
    "3": dict(name="심곡", f=1.30, code="DJG-3",
              use="깊은 굴곡. 새 활 형잡기, 센 활, 줌·한오금 살리기."),
}


# 오목면 기준 곡선 (u=0..1, 341점, 현 길이로 정규화한 처짐)
_V = np.array([0.000000,0.000316,0.000663,0.001040,0.001446,0.001880,0.002343,0.002833,0.003349,0.003891,0.004457,0.005049,0.005663,0.006301,0.006961,0.007642,0.008345,0.009067,0.009808,0.010569,0.011347,0.012142,0.012954,0.013782,0.014624,0.015482,0.016352,0.017236,0.018132,0.019040,0.019959,0.020887,0.021825,0.022772,0.023727,0.024689,0.025658,0.026632,0.027612,0.028596,0.029584,0.030575,0.031568,0.032563,0.033559,0.034555,0.035633,0.036684,0.037708,0.038707,0.039682,0.040634,0.041567,0.042482,0.043380,0.044263,0.045134,0.045993,0.046843,0.047683,0.048518,0.049347,0.050170,0.050987,0.051797,0.052600,0.053395,0.054184,0.054963,0.055734,0.056496,0.057250,0.057995,0.058732,0.059461,0.060183,0.060899,0.061607,0.062310,0.063004,0.063690,0.064368,0.065037,0.065695,0.066343,0.066980,0.067607,0.068224,0.068830,0.069426,0.070011,0.070588,0.071158,0.071718,0.072268,0.072807,0.073338,0.073861,0.074379,0.074890,0.075395,0.075893,0.076386,0.076870,0.077347,0.077816,0.078276,0.078728,0.079171,0.079605,0.080031,0.080449,0.080857,0.081255,0.081647,0.082030,0.082405,0.082772,0.083130,0.083481,0.083824,0.084159,0.084487,0.084808,0.085124,0.085433,0.085734,0.086028,0.086314,0.086591,0.086860,0.087120,0.087371,0.087614,0.087850,0.088079,0.088301,0.088514,0.088718,0.088912,0.089098,0.089277,0.089446,0.089607,0.089758,0.089900,0.090033,0.090155,0.090267,0.090370,0.090464,0.090546,0.090618,0.090680,0.090732,0.090772,0.090802,0.090820,0.090828,0.090826,0.090815,0.090796,0.090766,0.090725,0.090673,0.090610,0.090538,0.090455,0.090363,0.090260,0.090147,0.090023,0.089889,0.089744,0.089590,0.089427,0.089255,0.089073,0.088882,0.088681,0.088471,0.088250,0.088020,0.087779,0.087528,0.087270,0.087003,0.086728,0.086444,0.086148,0.085841,0.085522,0.085193,0.084854,0.084506,0.084149,0.083784,0.083409,0.083026,0.082633,0.082232,0.081822,0.081404,0.080977,0.080541,0.080096,0.079641,0.079178,0.078705,0.078224,0.077733,0.077234,0.076725,0.076205,0.075674,0.075132,0.074578,0.074013,0.073438,0.072852,0.072256,0.071650,0.071033,0.070407,0.069769,0.069118,0.068456,0.067782,0.067098,0.066405,0.065703,0.064990,0.064268,0.063536,0.062794,0.062044,0.061286,0.060522,0.059750,0.058973,0.058189,0.057401,0.056609,0.055813,0.055012,0.054207,0.053402,0.052596,0.051789,0.050983,0.050177,0.049371,0.048567,0.047763,0.046965,0.046169,0.045377,0.044588,0.043803,0.043020,0.042240,0.041465,0.040695,0.039930,0.039169,0.038414,0.037665,0.036921,0.036183,0.035451,0.034725,0.034007,0.033296,0.032595,0.031902,0.031214,0.030532,0.029853,0.029177,0.028504,0.027834,0.027168,0.026506,0.025848,0.025192,0.024540,0.023893,0.023252,0.022619,0.021994,0.021379,0.020774,0.020181,0.019600,0.019034,0.018484,0.017919,0.017360,0.016807,0.016261,0.015722,0.015189,0.014662,0.014142,0.013629,0.013123,0.012624,0.012131,0.011645,0.011167,0.010695,0.010230,0.009772,0.009321,0.008878,0.008442,0.008013,0.007591,0.007176,0.006769,0.006370,0.005977,0.005593,0.005215,0.004846,0.004484,0.004130,0.003783,0.003444,0.003113,0.002790,0.002475,0.002167,0.001868,0.001577,0.001294,0.001018,0.000752,0.000493,0.000242,0.000000])


def base_curve():
    uu = np.linspace(0, 1, len(_V))
    return uu, _V * PARAM["fore"]


def _lower_hull(px, py):
    """볼록면이 다시 꺾이지 않도록: 점열의 아래쪽 볼록 껍질"""
    h = []
    for p in zip(px, py):
        while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                               - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
            h.pop()
        h.append(p)
    h = np.array(h)
    return np.interp(px, h[:, 0], h[:, 1])


def geometry(f):
    L = PARAM["L"]
    uu, v = base_curve()
    ub0 = uu[int(np.argmax(v))]                       # 기준 곡선의 꺾임 위치
    ubn = float(np.clip(PARAM["bend_x"] / L, 0.15, 0.85))
    x = np.linspace(0, L, 1441)
    u = x / L
    src = np.where(u < ubn, u * ub0 / ubn, ub0 + (u - ubn) * (1 - ub0) / (1 - ubn))
    yc = -np.interp(src, uu, v) * L * f               # 오목면(위), 가운데가 아래로 처짐
    ub = ubn
    d = PARAM["d_end"] + (PARAM["d_bend"] - PARAM["d_end"]) * np.exp(-((u - ub) / 0.22) ** 2)
    dy = np.gradient(yc, x)
    nx, ny = dy / np.hypot(1, dy), -1 / np.hypot(1, dy)   # 아래쪽 법선
    xv, yv = x + d * nx, yc + d * ny     # 볼록면(아래, 활 접촉면)
    o = np.argsort(xv); xv, yv = xv[o], yv[o]
    yh = _lower_hull(xv, yv)             # 끝부분 역굴곡 제거(직선으로 이어짐)
    # 되굽힘: 직선(0%) ↔ 원래 곡선(100%)을 왼쪽·오른쪽 끝 따로 섞음
    xb = ubn * L
    rl = np.clip(PARAM.get("recurve_l", 0.0), 0, 100) / 100
    rr = np.clip(PARAM.get("recurve_r", 0.0), 0, 100) / 100
    diff = yv - yh                       # >= 0, 되굽힘 구간에서만 0보다 큼
    yv = yh + np.where(xv < xb, rl, rr) * diff
    on = diff > 0.05
    rb_xl = float(xv[on & (xv < xb)].max()) if np.any(on & (xv < xb)) else 0.0
    rb_xr = float(xv[on & (xv > xb)].min()) if np.any(on & (xv > xb)) else L
    dyv = np.gradient(yv, xv)
    nvx, nvy = dyv / np.hypot(1, dyv), -1 / np.hypot(1, dyv)  # 볼록면 바깥(아래) 법선
    # 끈 감기 턱: 양끝 블록을 오목면 쪽으로 h만큼 돋움
    h, Lb, w = PARAM["lip_h"], PARAM["lip_len"], PARAM["lip_fillet"]
    def ramp(t):
        return np.where(t <= 0, 1.0, np.where(t >= w, 0.0, 0.5 * (1 + np.cos(np.pi * t / w))))
    b = np.maximum(ramp(x - Lb), ramp((L - x) - Lb))
    xc, ycr = x - h * b * nx, yc - h * b * ny
    return dict(x=x, xc=xc, yc=ycr, yc0=yc, xv=xv, yv=yv, d=d, ub=ub, nx=nx, ny=ny, nvx=nvx, nvy=nvy,
                rb_xl=rb_xl, rb_xr=rb_xr)


def outline(g):
    """닫힌 외곽선(끝단 처리 포함): 오목면 → 긴쪽 끝(오른쪽, 사선) → 볼록면 → 짧은쪽 머리(왼쪽, 오목홈)"""
    pts = list(zip(g["xc"], g["yc"]))
    # 오른쪽(긴 쪽) 끝: 볼록면 끝으로 직선
    pts += list(zip(g["xv"][::-1], g["yv"][::-1]))
    # 왼쪽 머리: 볼록면 시작 -> 오목면 시작 사이에 오목홈(바깥에서 안쪽으로 파임)
    a = np.array([g["xv"][0], g["yv"][0]]); b = np.array([g["xc"][0], g["yc"][0]])
    mid = (a + b) / 2; t = (b - a) / np.linalg.norm(b - a)
    inward = np.array([t[1], -t[0]])
    if inward[0] < 0:
        inward = -inward
    r = PARAM["scallop_r"]
    ang = np.linspace(np.pi, 0, 25)
    arc = [mid + r * np.cos(q) * t + r * 0.75 * np.sin(q) * inward for q in ang]
    # a -> (홈) -> b
    seg = [a + (mid - r * t - a) * s for s in np.linspace(0, 1, 4)]
    seg2 = [mid + r * t + (b - mid - r * t) * s for s in np.linspace(0, 1, 4)]
    pts.append(tuple(b))   # 직각 끝 (모서리 R3)
    return np.array(pts)


def holes(g):
    o = PARAM["hole_off"]
    out = []
    for i, sgn in ((0, 1), (-1, -1)):
        k = np.searchsorted(g["x"], g["x"][i] + sgn * o)
        k = min(max(k, 0), len(g["x"]) - 1)
        out.append(((g["x"][k] + g["xv"][k]) / 2, (g["yc"][k] + g["yv"][k]) / 2))
    return out


def hole_lines(g):
    """끈구멍: 오목면 -> 볼록면(가죽 포함) 관통. 정면도에서 숨은선 2줄 + 중심선"""
    o = PARAM["hole_off"]; lt = 0.0; h = PARAM["hole_d"] / 2
    res = []
    for i, sgn in ((0, 1), (-1, -1)):
        k = int(np.clip(np.searchsorted(g["x"], g["x"][i] + sgn * o), 0, len(g["x"]) - 1))
        nx, ny = g["nx"][k], g["ny"][k]
        tx, ty = -ny, nx
        C = np.array([g["xc"][k], g["yc"][k]])
        ts = np.linspace(0, 120, 2401)        # 구멍 축과 볼록면의 교점
        px, py = C[0] + ts * nx, C[1] + ts * ny
        j = int(np.argmax(py - np.interp(px, g["xv"], g["yv"]) <= 0))
        V = np.array([px[j], py[j]])
        T_ = np.array([tx, ty])
        res.append((C, V, T_, np.array([nx, ny]), h))
    return res


def crown_profile(u, T, R):
    """오목면 쪽(가죽 반대쪽) 모서리 라운드: 꼭대기에서 아래로 내려간 양 (0 = 평면부)"""
    R = min(R, T / 2)
    dl = np.where(u < R, R - np.sqrt(np.maximum(R ** 2 - (R - u) ** 2, 0)), 0.0)
    dr = np.where(u > T - R, R - np.sqrt(np.maximum(R ** 2 - (u - (T - R)) ** 2, 0)), 0.0)
    return np.maximum(dl, dr)


def section_outline(x0, ybot_prof_x, ybot_prof_y, T, ytop, R, S):
    """단면 외곽: 아래(볼록면 C홈) → 오른쪽 → 라운드 꼭대기 → 왼쪽"""
    uu = np.linspace(T, 0, 241)
    cr = crown_profile(uu, T, R)
    # 라운드가 옆면까지 내려가는 높이 R
    xs = np.r_[ybot_prof_x, x0 + uu * S, x0]
    ys = np.r_[ybot_prof_y, ytop - cr * S, ybot_prof_y[0]]
    return xs, ys


def groove_profile(u, T, gd):
    """폭 전체 원호(C자) 홈: 양 모서리 0, 중앙 깊이 gd"""
    R = ((T / 2) ** 2 + gd ** 2) / (2 * gd)
    return np.sqrt(np.maximum(R ** 2 - (u - T / 2) ** 2, 0)) - (R - gd)


def dim_h(ax, x1, x2, y, text, fs=7):
    ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<|-|>", lw=0.5,
                shrinkA=0, shrinkB=0, mutation_scale=6))
    ax.text((x1 + x2) / 2, y + 2, text, ha="center", va="bottom", fontsize=fs)


def dim_v(ax, x, y1, y2, text, fs=7, side=1):
    ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<|-|>", lw=0.5,
                shrinkA=0, shrinkB=0, mutation_scale=6))
    ax.text(x + side * 2.5, (y1 + y2) / 2, text, rotation=90, va="center",
            ha="left" if side > 0 else "right", fontsize=fs)


def line(ax, xs, ys, **k):
    k.setdefault("lw", 0.3); k.setdefault("color", "k")
    ax.plot(xs, ys, **k)


def sheet(key, G, pdf):
    g = geometry(G["f"]); L, T = PARAM["L"], PARAM["T"]
    sag = -g["yc0"].min()
    fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 420); ax.set_ylim(0, 297); ax.axis("off")
    ax.add_patch(Rectangle((10, 10), 400, 277, fill=False, lw=1.0))

    ox, oy = 40, 255  # 1:1
    ol = outline(g)
    ax.plot(ox + ol[:, 0], oy + ol[:, 1], lw=1.2, color="k")
    ax.plot(ox + np.r_[ol[:, 0], ol[0, 0]], oy + np.r_[ol[:, 1], ol[0, 1]], lw=1.2, color="k")
    # 접촉면 홈 표시선(숨은선)
    k = PARAM["groove"]; lt = PARAM["leather"]
    xl, yl = g["xv"] + lt * g["nvx"], g["yv"] + lt * g["nvy"]
    ax.fill(ox + np.r_[g["xv"], xl[::-1]], oy + np.r_[g["yv"], yl[::-1]], color="0.55", lw=0)
    ax.plot(ox + xl, oy + yl, lw=0.8, color="k")
    Re = PARAM["T"] * PARAM["edge_r_ratio"]   # 모서리 라운드 접선(가는 실선)
    ax.plot(ox + g["xc"] + Re * g["nx"], oy + g["yc"] + Re * g["ny"], lw=0.35, color="0.35")
    gd = PARAM["groove"]
    ax.plot(ox + g["xv"] - gd * g["nvx"], oy + g["yv"] - gd * g["nvy"], lw=0.5, color="k", ls=(0, (4, 2)))
    for (C, V, T_, N, h) in hole_lines(g):
        H = PARAM["cb_d"] / 2; dep = PARAM["cb_depth"]
        M = V - dep * N            # 카운터보어 바닥
        for sg in (-1, 1):
            p, q = C + sg * h * T_, M + sg * h * T_
            ax.plot(ox + np.array([p[0], q[0]]), oy + np.array([p[1], q[1]]), lw=0.6, color="k", ls=(0, (3, 1.5)))
            p, q = M + sg * H * T_, V + sg * H * T_
            ax.plot(ox + np.array([p[0], q[0]]), oy + np.array([p[1], q[1]]), lw=0.6, color="k", ls=(0, (3, 1.5)))
        p, q = M - H * T_, M + H * T_
        ax.plot(ox + np.array([p[0], q[0]]), oy + np.array([p[1], q[1]]), lw=0.6, color="k", ls=(0, (3, 1.5)))
        p, q = C - 6 * N, V + 6 * N
        line(ax, ox + np.array([p[0], q[0]]), oy + np.array([p[1], q[1]]), ls="-.")
    # 끈 감기 턱 표시 (오른쪽 끝)
    k2 = int(np.searchsorted(g["x"], L - PARAM["lip_len"] - PARAM["lip_fillet"] - 6))
    xt, yt = g["xc"][k2], g["yc"][k2]
    ax.annotate(f"끈 감기 턱 h{PARAM['lip_h']:.1f} (양끝)\n끝에서 {PARAM['lip_len']:.0f}, 안쪽 R 전이 {PARAM['lip_fillet']:.0f}",
                (ox + xt, oy + yt), (ox + xt - 70, oy + yt + 30), fontsize=6,
                arrowprops=dict(arrowstyle="-|>", lw=0.5, mutation_scale=6))
    # 기준선
    line(ax, [ox - 8, ox + L + 8], [oy, oy], ls="-.", lw=0.4)
    ax.text(ox + L - 2, oy + 2, "기준선(턱 제외 오목면 양끝)", fontsize=6, va="bottom", ha="right")
    # 꺾임 위치
    xb = g["ub"] * L
    line(ax, [ox + xb] * 2, [oy + 6, oy - sag - g["d"].max() - 6], ls="-.", lw=0.4)

    # 치수
    dim_h(ax, ox, ox + L, oy + 14, f"L = {L:.0f}")
    line(ax, [ox] * 2, [oy, oy + 16]); line(ax, [ox + L] * 2, [oy, oy + 16])
    dim_h(ax, ox, ox + xb, oy + 6, f"{xb:.0f} (꺾임점)", fs=6)
    dim_v(ax, ox + xb + 4, oy, oy - sag, f"처짐 {sag:.1f}", fs=6)
    i0 = 0
    dim_v(ax, ox - 6, oy + g["yc"][i0], oy + g["yv"][i0], f"{g['yc'][i0] - g['yv'][i0]:.1f}", side=-1)
    ib = int(np.argmin(g["yc"]))
    dim_v(ax, ox + xb - 4, oy + g["yc"][ib], oy + g["yv"][ib], f"{g['d'][ib]:.0f}", side=-1, fs=6)
    hx, hy = holes(g)[1]
    ax.text(ox + hx, oy + 9, f"끈구멍 Ø{PARAM['hole_d']:.0f} 관통 + 가죽쪽 카운터보어 Ø{PARAM['cb_d']:.0f}×{PARAM['cb_depth']:.0f} ×2, 끝에서 {PARAM['hole_off']:.0f} (상세 C)",
            fontsize=6, ha="right")
    ax.text(ox + 4, oy + g["yv"][0] - 12, "직각 끝, 모서리 R3\n(끝단 옵션: 상세 C)", fontsize=6, va="top")
    i6 = int(0.22 * (len(g["x"]) - 1))
    ax.text(ox + g["xv"][i6] - 6, oy + g["yv"][i6] - 10,
            f"볼록면 = 활 접촉면\nC자 홈 깊이 {PARAM['groove']:.0f} + 스웨이드 가죽 t{PARAM['leather']:.0f} (단면 B-B)", fontsize=6, ha="right", va="top")
    ax.text(ox, oy + 26, f"정면도 (축척 1:1)  — 굴곡 등급: {G['name']}", fontsize=10, weight="bold")

    # 단면 B-B (1:1)
    sx, sy = 205, 36
    db = g["d"].max()
    S2 = 2.0   # 단면 2:1
    gd, rim, lt = PARAM["groove"], PARAM["groove_rim"], PARAM["leather"]
    uu = np.linspace(0, T, 121)
    prof = groove_profile(uu, T, gd)
    X = sx + uu * S2; Yb = sy + prof * S2
    Re = T * PARAM["edge_r_ratio"]
    PX, PY = section_outline(sx, X, Yb, T, sy + db * S2, Re, S2)
    clip = matplotlib.patches.Polygon(np.c_[PX, PY], closed=True, fill=False, lw=0)
    ax.add_patch(clip)
    for k0 in np.arange(-T * S2 - 100, db * S2 + 100, 3.0):      # 해칭(45°)을 직접 그려 PDF 이음매 방지
        ln, = ax.plot([sx + k0, sx + k0 + 200], [sy, sy + 200], lw=0.4, color="k")
        ln.set_clip_path(clip)
    ax.plot(PX, PY, lw=1.2, color="k")
    ax.text(sx + T * S2 + 3, sy + db * S2 - Re * S2 * 0.3, f"← R{Re:.1f} (T×{PARAM['edge_r_ratio']:g})", fontsize=6, va="center")
    ax.fill(np.r_[X, X[::-1]], np.r_[Yb, (Yb - lt * S2)[::-1]], color="0.55", lw=0)
    ax.plot(X, Yb - lt * S2, lw=0.6, color="k")
    dim_h(ax, sx, sx + T * S2, sy + db * S2 + 4, f"T = {T:.0f}")
    dim_v(ax, sx + T * S2 + 5, sy, sy + db * S2, f"{db:.0f}")
    Rg = ((T / 2) ** 2 + gd ** 2) / (2 * gd)
    ax.text(sx + T * S2 / 2, sy - lt * S2 - 6, f"C자 원호 홈 R≈{Rg:.0f} (폭 전체 {T:.0f})", fontsize=6, ha="center", va="top")
    ax.text(sx + T * S2 + 3, sy + gd * S2 / 2, f"← 홈 깊이 {gd:.0f}", fontsize=6, va="center")
    ax.text(sx, sy + db * S2 + 16, "단면 B-B (꺾임부, 2:1)", fontsize=9, weight="bold")
    ax.text(sx + T * S2 / 2, sy - lt * S2 - 13, f"볼록면: 모서리에서 바로 시작하는 완만한 C자 홈\n스웨이드 가죽 t{lt:.0f} 홈 따라 접착", fontsize=6, ha="center", va="top")

    # 상세 C: 끝단 옵션 (2:1)
    S = 2; de = PARAM["d_end"]
    cx, cy = 318, 170
    ax.text(cx - 5, cy + 22, "상세 C — 끈구멍 (매듭 숨김형)", fontsize=9, weight="bold")
    T = PARAM["T"]; Lb = 45
    hd, cbd, cbh = PARAM["hole_d"], PARAM["cb_d"], PARAM["cb_depth"]
    gd, rim, lt = PARAM["groove"], PARAM["groove_rim"], PARAM["leather"]
    # (1) 오목면에서 본 끝단 1:1
    ax.plot([cx + Lb, cx, cx, cx + Lb], [cy, cy, cy - T, cy - T], lw=1, color="k")
    hx = cx + PARAM["hole_off"]; hy = cy - T / 2
    ax.add_patch(Circle((hx, hy), hd / 2, fill=False, lw=0.9))
    tt = np.linspace(0, 2 * np.pi, 120)
    ax.plot(hx + cbd / 2 * np.cos(tt), hy + cbd / 2 * np.sin(tt), lw=0.5, color="k", ls=(0, (2, 1.2)))
    line(ax, [hx - 11, hx + 11], [hy, hy], ls="-."); line(ax, [hx, hx], [hy - 11, hy + 11], ls="-.")
    dim_h(ax, cx, hx, cy + 1, f"{PARAM['hole_off']:.0f}", fs=5)
    ax.text(cx, cy + 9, "C-1. 오목면에서 본 끝단 (1:1)", fontsize=6.5, weight="bold")
    ax.text(cx + Lb + 2, hy, f"Ø{hd:.0f} 정공\n(숨은선 Ø{cbd:.0f}\n 카운터보어)", fontsize=5.5, va="center")
    # (2) 구멍 중심 단면 D-D (2:1): 위 = 오목면(끈 나오는 쪽), 아래 = 볼록면(가죽)
    S2 = 1.5; de = PARAM["d_end"]
    qx, qy = cx, 72      # 아래 기준(볼록면 목재 테두리 높이)
    uu = np.linspace(0, T, 121)
    prof = groove_profile(uu, T, gd)
    X = qx + uu * S2; Yb = qy + prof * S2
    top = qy + de * S2
    c0 = qx + T / 2 * S2
    # 목재 외곽(구멍 부분 제외)
    Re = T * PARAM["edge_r_ratio"]
    PX, PY = section_outline(qx, X, Yb, T, top, Re, S2)
    ax.plot(PX, PY, lw=1.1, color="k")
    ytop_hole = top - float(crown_profile(np.array([T / 2 - hd / 2]), T, Re)[0]) * S2
    # 가죽 (구멍 위로도 연속 — 매듭을 덮음)
    ax.fill(np.r_[X, X[::-1]], np.r_[Yb, (Yb - lt * S2)[::-1]], color="0.55", lw=0)
    ax.plot(X, Yb - lt * S2, lw=0.6, color="k")
    # 카운터보어 + 정공 (흰색으로 비움)
    ycb = qy + gd * S2              # 홈 바닥(중앙) 기준
    ax.fill([c0 - cbd * S2 / 2, c0 + cbd * S2 / 2, c0 + cbd * S2 / 2, c0 - cbd * S2 / 2], [ycb, ycb, ycb + cbh * S2, ycb + cbh * S2], color="white", zorder=3)
    ax.fill([c0 - hd * S2 / 2, c0 + hd * S2 / 2, c0 + hd * S2 / 2, c0 - hd * S2 / 2], [ycb + cbh * S2, ycb + cbh * S2, top + 1, top + 1], color="white", zorder=3)
    ywall = qy + np.interp(T / 2 - cbd / 2, uu, prof) * S2
    ax.fill([c0 - cbd * S2 / 2, c0 + cbd * S2 / 2, c0 + cbd * S2 / 2, c0 - cbd * S2 / 2], [ywall, ywall, ycb, ycb], color="white", zorder=2.5)
    ax.plot(X, Yb, lw=0.6, color="k", zorder=2.6)
    ax.plot([c0 - cbd * S2 / 2, c0 - cbd * S2 / 2, c0 - hd * S2 / 2, c0 - hd * S2 / 2], [ywall, ycb + cbh * S2, ycb + cbh * S2, ytop_hole], lw=1.1, color="k", zorder=4)
    ax.plot([c0 + cbd * S2 / 2, c0 + cbd * S2 / 2, c0 + hd * S2 / 2, c0 + hd * S2 / 2], [ywall, ycb + cbh * S2, ycb + cbh * S2, ytop_hole], lw=1.1, color="k", zorder=4)
    # 끈 + 매듭(개략)
    ax.plot([c0, c0], [top + 8, ycb + cbh * S2], lw=1.6, color="0.4", zorder=5)
    ax.add_patch(Circle((c0, ycb + cbh * S2 / 2), cbh * S2 / 2 - 1.5, fc="0.75", ec="0.3", lw=0.6, zorder=5))
    ax.text(c0 + 3, top + 6, "끈 (오목면 쪽으로 나옴)", fontsize=5.5)
    ax.text(qx + T * S2 + 14, ycb + cbh * S2 / 2 + 4, "매듭\n(카운터보어 안)", fontsize=5.5, va="center")
    dim_v(ax, qx + T * S2 + 8, ycb, ycb + cbh * S2, f"{cbh:.0f}", fs=5.5)
    dim_h(ax, c0 - cbd * S2 / 2, c0 + cbd * S2 / 2, qy - lt * S2 - 6, f"Ø{cbd:.0f}", fs=5.5)
    dim_h(ax, c0 - hd * S2 / 2, c0 + hd * S2 / 2, top + 13, f"Ø{hd:.0f}", fs=5.5)
    ax.text(qx, top + 21, "C-2. 끈구멍 단면 D-D (1.5:1)", fontsize=6.5, weight="bold")
    ax.text(qx + T * S2 + 14, qy - 2, "가죽은 구멍을 덮고\n끝까지 연속\n(매듭을 가죽 속에 숨김)", fontsize=5.5, va="top")

    # 좌표표
    tx, ty = 22, 152
    ax.text(tx, ty + 8, "좌표표 [mm] — x: 기준선 방향, 오목면/볼록면: 기준선에서 아래로 거리 (−: 기준선 위, 턱 포함)", fontsize=8, weight="bold")
    xs = np.arange(0, L + 0.1, 20)
    yc = -np.interp(xs, g["xc"], g["yc"])
    yv = -np.interp(xs, g["xv"], g["yv"])
    cw, rh = 14.2, 5.0
    for c, X in enumerate(xs):
        ax.text(tx + 18 + c * cw, ty, f"{X:.0f}", fontsize=6, ha="center")
        ax.text(tx + 18 + c * cw, ty - rh, f"{yc[c]:.1f}", fontsize=6, ha="center")
        ax.text(tx + 18 + c * cw, ty - 2 * rh, f"{yv[c]:.1f}", fontsize=6, ha="center")
    for i, lab in enumerate(["x", "오목면", "볼록면"]):
        ax.text(tx, ty - i * rh, lab, fontsize=6, weight="bold")
    line(ax, [tx, tx + 18 + len(xs) * cw - 6], [ty - 2 * rh - 2.5] * 2, color="0.5")

    notes = [
        "주기",
        "1. 재질: 물푸레나무 / 참죽나무 / 느티나무 중 택1 — 충분히 건조된 것(함수율 12% 이하).",
        f"2. 결은 긴 팔 방향. 오목면 쪽 모서리 R{PARAM['T'] * PARAM['edge_r_ratio']:.1f}(T×{PARAM['edge_r_ratio']:g}). 볼록면 끝 되굽힘 왼쪽 {PARAM['recurve_l']:g}% · 오른쪽 {PARAM['recurve_r']:g}%.",
        f"3. 가공: 정면도 1:1 출력(A3, 배율 100%) → 형판 제작 → 판재(T{PARAM['T']:g})에 금긋기 → 띠톱 → 다듬기.",
        f"4. 볼록면(활 접촉면): 폭 전체 완만한 C자 홈(중앙 깊이 {PARAM['groove']:g}) 가공 후 스웨이드 가죽 t{PARAM['leather']:g}를 홈 따라 접착(끝까지).",
        f"5. 끈구멍: 오목면 Ø{PARAM['hole_d']:g} 관통 + 볼록면 카운터보어 Ø{PARAM['cb_d']:g}×{PARAM['cb_depth']:g}. 매듭을 보어 안에 넣고 가죽으로 덮음. 각인: 옆면 긴 팔.",
        f"6. 양끝 오목면에 끈 감기 턱 h{PARAM['lip_h']:g}(끝에서 {PARAM['lip_len']:g}) — 감은 끈 미끄럼 방지. 2개 1벌, 2EA. 오일 마감.",
        f"7. 용도: {G['use']}",
        f"8. 길이 {PARAM['L']:g}, 너비 {PARAM['T']:g}. 처짐량은 실물·형판 대조 후 곡선 보정계수로 확정.",
    ]
    for i, s in enumerate(notes):
        ax.text(22, 122 - i * 6.3, s, fontsize=7 if i else 8, weight="bold" if i == 0 else "normal")

    bx, by, bw = 290, 10, 120
    ax.add_patch(Rectangle((bx, by), bw, 50, fill=False, lw=1.0))
    for yy_ in (by + 12, by + 24, by + 36):
        line(ax, [bx, bx + bw], [yy_] * 2, lw=0.5)
    line(ax, [bx + 35] * 2, [by, by + 36], lw=0.5)
    ax.text(bx + bw / 2, by + 43, f"도지개 {key}형 — {G['name']}", fontsize=10, ha="center",
            va="center", weight="bold")
    for i, (a, b) in enumerate([("도면번호", G["code"]), ("축척", "1:1"),
                                ("재질 / 수량", "물푸레·참죽·느티 / 2EA")]):
        ax.text(bx + 3, by + 30 - i * 12, a, fontsize=7, va="center")
        ax.text(bx + 38, by + 30 - i * 12, b, fontsize=7, va="center")
    pdf.savefig(fig); plt.close(fig)
    return g


def to_dxf(key, g):
    doc = ezdxf.new("R2010", setup=True)
    for nm, c in (("OUTLINE", 7), ("HIDDEN", 3), ("CENTER", 1), ("HOLE", 5), ("TEXT", 2)):
        doc.layers.add(nm, color=c)
    msp = doc.modelspace()
    ol = outline(g)
    msp.add_lwpolyline([tuple(p) for p in ol], close=True, dxfattribs={"layer": "OUTLINE"})
    k = PARAM["groove"]
    msp.add_lwpolyline(list(zip(g["xv"] - k * g["nvx"], g["yv"] - k * g["nvy"])), dxfattribs={"layer": "HIDDEN"})
    for (C, V, T_, N, h) in hole_lines(g):
        H = PARAM["cb_d"] / 2; M = V - PARAM["cb_depth"] * N
        for sg in (-1, 1):
            for p, q in ((C + sg * h * T_, M + sg * h * T_), (M + sg * H * T_, V + sg * H * T_)):
                msp.add_line(tuple(p), tuple(q), dxfattribs={"layer": "HIDDEN", "linetype": "DASHED"})
        msp.add_line(tuple(M - H * T_), tuple(M + H * T_), dxfattribs={"layer": "HIDDEN", "linetype": "DASHED"})
        msp.add_line(tuple(C - 6 * N), tuple(V + 6 * N), dxfattribs={"layer": "CENTER", "linetype": "CENTER"})
    msp.add_line((-8, 0), (PARAM["L"] + 8, 0), dxfattribs={"layer": "CENTER"})
    msp.add_text(f"DOJIGAE {key} L{PARAM['L']:.0f} T{PARAM['T']:.0f}", height=5,
                 dxfattribs={"layer": "TEXT"}).set_placement((0, 20))
    fn = os.path.join(OUTDIR, f"dojigae_L{PARAM['L']:.0f}_{key}_{GRADES[key]['code']}.dxf")
    doc.saveas(fn)
    return fn


OUTDIR = "."


def generate(outdir=".", keys=None, params=None, factors=None, dxf=True):
    """도면 생성(PDF, dxf=True면 DXF도). 반환: 생성된 파일 경로 목록"""
    global OUTDIR
    OUTDIR = outdir
    os.makedirs(outdir, exist_ok=True)
    if params:
        PARAM.update(params)
    if factors:
        for k_, f_ in factors.items():
            GRADES[k_]["f"] = f_
    keys = keys or list(GRADES)
    files = []
    pdfn = os.path.join(outdir, f"dojigae_L{PARAM['L']:.0f}_drawings.pdf")
    with PdfPages(pdfn) as pdf:
        for k_ in keys:
            g = sheet(k_, GRADES[k_], pdf)
            if dxf:
                files.append(to_dxf(k_, g))
    files.insert(0, pdfn)
    return files


if __name__ == "__main__":
    for f in generate("output"):
        print(f)
