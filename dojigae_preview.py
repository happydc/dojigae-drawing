"""
입력 항목 미리보기: 도지개 정면도 + 단면을 그리고, 마우스를 올린 치수를 빨간색으로 표시
"""
import tkinter as tk
import numpy as np
import dojigae_core as core

HL = "#d62828"      # 강조색
WOOD = "#ead1a8"
WOOD_EDGE = "#8a6a3e"
LEATHER = "#2e9e6a"

# 항목별 설명
DESCR = {
    "L": "전체 길이 — 양 끝 사이의 직선 거리",
    "bend_x": "왼쪽 끝 → 꺾임점 — 오목면이 가장 깊은 곳까지의 거리 (짧은 팔 길이)",
    "T": "너비(판재 두께) — 활 너비 방향 두께. 단면의 가로 폭",
    "d_end": "끝단 높이 — 양 끝의 오목면~볼록면 높이(기준값)",
    "d_bend": "꺾임부 높이 — 가장 두꺼운 곳(꺾임점)의 높이",
    "fore": "곡선 보정계수 — 오목면 처짐(굴곡 깊이) 전체에 곱하는 배율",
    "leather": "가죽 두께 — 볼록면(활이 닿는 면)에 붙이는 스웨이드 두께",
    "groove": "볼록면 C홈 깊이 — 볼록면 폭 전체에 판 완만한 C자 홈의 가운데 깊이",
    "hole_d": "끈구멍 지름 — 오목면에서 뚫는 관통 구멍(끈이 나오는 쪽)",
    "cb_d": "매듭 보어 지름 — 가죽 쪽에서 넓게 판 구멍(매듭이 들어가 가죽 아래 숨음)",
    "cb_depth": "매듭 보어 깊이 — 볼록면 홈 바닥에서부터 판 깊이",
    "hole_off": "끝 → 구멍 중심 — 각 끝에서 끈구멍 중심까지 거리",
    "lip_h": "끈 감기 턱 높이 — 양 끝 오목면을 돋운 높이(감은 끈 미끄럼 방지)",
    "lip_len": "끝 → 턱 위치 — 끝에서 턱(돋운 부분)이 끝나는 곳까지",
    "lip_fillet": "턱 둥근 전이 길이 — 턱에서 몸통으로 둥글게 내려가는 구간",
    "recurve_l": "볼록면 끝 되굽힘(왼쪽) — 0%는 끝까지 직선, 100%는 원래 곡선대로 끝에서 다시 휨",
    "recurve_r": "볼록면 끝 되굽힘(오른쪽) — 0%는 끝까지 직선, 100%는 원래 곡선대로 끝에서 다시 휨",
    "edge_r_ratio": "오목면 모서리 R — 가죽 반대쪽 모서리 반경 = 너비 T × 비율",
    "grade": "굴곡 등급 배율 — 표준(2형) 처짐 대비 배율. 1형 중곡 / 3형 심곡",
    "bed": "프린터 베드 최대 길이 — 이보다 길면 꺾임점에서 2분할 STL도 만듦",
}


class Preview(tk.Canvas):
    W, H = 560, 365

    def __init__(self, master, **kw):
        super().__init__(master, width=self.W, height=self.H, bg="#fbf8f2",
                         highlightthickness=1, highlightbackground="#d8d0c2", **kw)
        self.g = None
        self.key = None
        self.refresh()

    # ---------- 좌표 ----------
    def _fx(self, x):  # 정면도 mm -> px
        return self.ox + x * self.s

    def _fy(self, y):
        return self.oy - y * self.s

    def _sx(self, u):  # 단면도 mm -> px (u: 너비 방향, v: 높이)
        return self.qx + u * self.ss

    def _sy(self, v):
        return self.qy - v * self.ss

    # ---------- 그리기 ----------
    def refresh(self, params=None):
        try:
            if params:
                core.PARAM.update(params)
            self.g = core.geometry(1.0)
        except Exception:
            if self.g is None:
                return
        self.delete("all")
        g, P = self.g, core.PARAM
        L = P["L"]
        ymin = min(g["yv"].min(), -1)
        self.s = min(380 / L, 150 / (2.5 - ymin + 10))
        self.ox, self.oy = 18, 60
        # 정면도
        pts = list(zip(g["xc"], g["yc"])) + list(zip(g["xv"][::-1], g["yv"][::-1]))
        flat = [c for x, y in pts[::4] for c in (self._fx(x), self._fy(y))]
        self.create_polygon(flat, fill=WOOD, outline=WOOD_EDGE, width=1.5)
        lt = P["leather"]
        lv = [c for x, y in zip(g["xv"][::4] + lt * g["nvx"][::4], g["yv"][::4] + lt * g["nvy"][::4])
              for c in (self._fx(x), self._fy(y))]
        self.create_line(lv, fill=LEATHER, width=max(2, lt * self.s))
        for (C, V, T_, N, h) in core.hole_lines(g):
            self.create_line(self._fx(C[0]), self._fy(C[1]), self._fx(V[0]), self._fy(V[1]),
                             fill="#9a8a70", dash=(3, 2))
        self.create_line(self._fx(-5), self._fy(0), self._fx(L + 5), self._fy(0), fill="#b9ad98", dash=(6, 3))
        self.create_text(self.ox, 14, anchor="w", text="정면도", fill="#6b6150", font=("Malgun Gothic", 9, "bold"))
        # 단면도 (꺾임부)
        T, R, gd = P["T"], P["T"] * P["edge_r_ratio"], P["groove"]
        db = float(g["d"].max())
        self.ss = min(2.6, 125 / max(db, 1), 95 / max(T, 1))
        self.qx, self.qy = 440, 40 + db * self.ss + 18
        u = np.linspace(0, T, 61)
        bot = core.groove_profile(u, T, gd)
        top = db - core.crown_profile(u[::-1], T, R)
        poly = [c for uu, vv in zip(u, bot) for c in (self._sx(uu), self._sy(vv))]
        poly += [c for uu, vv in zip(u[::-1], top) for c in (self._sx(uu), self._sy(vv))]
        self.create_polygon(poly, fill=WOOD, outline=WOOD_EDGE, width=1.5)
        self.create_line([c for uu, vv in zip(u, bot - lt) for c in (self._sx(uu), self._sy(vv))],
                         fill=LEATHER, width=max(2, lt * self.ss))
        self.create_text(self.qx, 14, anchor="w", text="단면(꺾임부)", fill="#6b6150", font=("Malgun Gothic", 9, "bold"))
        # 설명 줄
        self.msg = self.create_text(12, self.H - 14, anchor="w", width=self.W - 24, fill="#4a4237",
                                    text="항목에 마우스를 올리면 해당 치수를 빨간색으로 표시합니다.",
                                    font=("Malgun Gothic", 9))
        if self.key:
            self.show(self.key)

    # ---------- 강조 ----------
    def _dim_h(self, x1, x2, y, text):
        self.create_line(x1, y, x2, y, fill=HL, width=2, arrow="both", arrowshape=(7, 8, 3), tags="hl")
        self.create_text((x1 + x2) / 2, y - 8, text=text, fill=HL, font=("Malgun Gothic", 9, "bold"), tags="hl")

    def _dim_v(self, x, y1, y2, text, side=1):
        self.create_line(x, y1, x, y2, fill=HL, width=2, arrow="both", arrowshape=(7, 8, 3), tags="hl")
        self.create_text(x + side * 6, (y1 + y2) / 2, text=text, anchor="w" if side > 0 else "e",
                         fill=HL, font=("Malgun Gothic", 9, "bold"), tags="hl")

    def _ring(self, x, y, r=10):
        self.create_oval(x - r, y - r, x + r, y + r, outline=HL, width=2, tags="hl")

    END_KEYS = ("hole_d", "cb_d", "cb_depth", "hole_off", "lip_h", "lip_len", "lip_fillet", "d_end")

    def _end_zoom(self, key):
        """왼쪽 끝 확대(3배) — 작은 부위(턱·구멍) 표시용"""
        g, P = self.g, core.PARAM
        X = 42.0
        m = g["x"] <= X
        mv = g["xv"] <= X
        ytop = float(g["yc"][m].max())
        ybot = float(g["yv"][mv].min())
        z = min(3.2, 88 / max(ytop - ybot, 1))
        zx, zy = 40, 222
        mx = lambda x: zx + x * z
        my = lambda y: zy + (ytop - y) * z
        pts = list(zip(g["xc"][m], g["yc"][m])) + list(zip(g["xv"][mv][::-1], g["yv"][mv][::-1]))
        self.create_rectangle(zx - 10, zy - 16, mx(X) + 10, my(ybot) + 12, outline="#cfc6b6", dash=(2, 2), tags="hl")
        self.create_text(zx - 6, zy - 24, anchor="w", text="왼쪽 끝 확대", fill="#6b6150",
                         font=("Malgun Gothic", 8, "bold"), tags="hl")
        self.create_polygon([c for x, y in pts for c in (mx(x), my(y))], fill=WOOD, outline=WOOD_EDGE, width=1.5, tags="hl")
        lt = P["leather"]
        self.create_line([c for x, y in zip(g["xv"][mv] + lt * g["nvx"][mv], g["yv"][mv] + lt * g["nvy"][mv])
                          for c in (mx(x), my(y))], fill=LEATHER, width=max(2, lt * z), tags="hl")
        C, V, T_, N, h = core.hole_lines(g)[0]
        H = P["cb_d"] / 2
        M = V - (P["groove"] + P["cb_depth"]) * N
        def seg(a, b, col, wdt=1, dash=None):
            self.create_line(mx(a[0]), my(a[1]), mx(b[0]), my(b[1]), fill=col, width=wdt, dash=dash, tags="hl")
        hc = HL if key in ("hole_d", "hole_off") else "#8a7a60"
        bc = HL if key in ("cb_d", "cb_depth") else "#8a7a60"
        for sg in (-1, 1):
            seg(C + sg * h * T_, M + sg * h * T_, hc, 2 if hc == HL else 1, None if hc == HL else (3, 2))
            seg(M + sg * H * T_, V + sg * H * T_, bc, 2 if bc == HL else 1, None if bc == HL else (3, 2))
        seg(M - H * T_, M + H * T_, bc, 2 if bc == HL else 1, None if bc == HL else (3, 2))
        f = ("Malgun Gothic", 9, "bold")
        if key == "hole_d":
            self.create_text(mx(C[0]) + 14, my(C[1]) - 8, text=f"Ø{P['hole_d']:g}", anchor="w", fill=HL, font=f, tags="hl")
        elif key == "cb_d":
            self.create_text(mx(V[0]) + H * z + 6, my(V[1]) - 6, text=f"Ø{P['cb_d']:g}", anchor="w", fill=HL, font=f, tags="hl")
        elif key == "cb_depth":
            self.create_text(mx(M[0]) + H * z + 6, (my(M[1]) + my(V[1])) / 2, text=f"깊이 {P['cb_depth']:g}",
                             anchor="w", fill=HL, font=f, tags="hl")
        elif key == "hole_off":
            self._dim_h(mx(0), mx(C[0]), zy - 6, f"{P['hole_off']:g}")
        elif key in ("lip_h", "lip_len", "lip_fillet"):
            lb, w = P["lip_len"], P["lip_fillet"]
            mm = g["x"] <= lb + w
            self.create_line([c for x, y in zip(g["xc"][mm], g["yc"][mm]) for c in (mx(x), my(y))],
                             fill=HL, width=3, tags="hl")
            if key == "lip_len":
                self._dim_h(mx(0), mx(lb), zy - 6, f"{lb:g}")
            elif key == "lip_fillet":
                self._dim_h(mx(lb), mx(lb + w), zy - 6, f"{w:g}")
            else:
                self.create_text(mx(lb + w) + 8, zy - 4, text=f"h{P['lip_h']:g}", anchor="w", fill=HL, font=f, tags="hl")
        elif key == "d_end":
            self._dim_v(mx(0) - 4, my(g["yc"][0]), my(g["yv"][0]), f"{P['d_end']:g}", side=-1)

    def clear(self):
        self.key = None
        self.delete("hl")
        self.itemconfigure(self.msg, text="항목에 마우스를 올리면 해당 치수를 빨간색으로 표시합니다.")

    def show(self, key):
        if self.g is None:
            return
        self.key = key
        self.delete("hl")
        g, P = self.g, core.PARAM
        L, fx, fy = P["L"], self._fx, self._fy
        i0, i1 = 0, len(g["x"]) - 1
        ib = int(np.argmin(g["yc0"]))
        top_y = fy(max(g["yc"].max(), 0)) - 12
        T, db = P["T"], float(g["d"].max())
        R = T * P["edge_r_ratio"]
        if key == "L":
            self._dim_h(fx(0), fx(L), top_y, f"L = {P['L']:g}")
        elif key == "bend_x":
            xb = g["ub"] * L
            self.create_line(fx(xb), top_y, fx(xb), fy(g["yv"][ib]), fill=HL, dash=(4, 2), tags="hl")
            self._dim_h(fx(0), fx(xb), top_y, f"{P['bend_x']:g}")
        elif key == "d_end":
            self._dim_v(fx(0) - 6, fy(g["yc"][i0]), fy(g["yv"][i0]), f"{P['d_end']:g}", side=-1)
            self._dim_v(fx(L) + 6, fy(g["yc"][i1]), fy(g["yv"][i1]), "")
        elif key == "d_bend":
            xb = g["xc"][ib]
            self._dim_v(fx(xb), fy(g["yc"][ib]), fy(g["yv"][ib]), f"{P['d_bend']:g}")
            self._dim_v(self._sx(T) + 12, self._sy(0), self._sy(db), f"{P['d_bend']:g}")
        elif key in ("fore", "grade"):
            xb = g["xc"][ib]
            self._dim_v(fx(xb) + 8, fy(0), fy(g["yc0"][ib]), f"처짐 {-g['yc0'][ib]:.1f}")
            self.create_line([c for x, y in zip(g["xc"][::4], g["yc"][::4]) for c in (fx(x), fy(y))],
                             fill=HL, width=3, tags="hl")
        elif key == "leather":
            lt = P["leather"]
            self.create_line([c for x, y in zip(g["xv"][::4] + lt * g["nvx"][::4], g["yv"][::4] + lt * g["nvy"][::4])
                              for c in (fx(x), fy(y))], fill=HL, width=3, tags="hl")
            u = np.linspace(0, T, 41)
            b = core.groove_profile(u, T, P["groove"]) - lt
            self.create_line([c for uu, vv in zip(u, b) for c in (self._sx(uu), self._sy(vv))], fill=HL, width=3, tags="hl")
        elif key == "groove":
            u = np.linspace(0, T, 41)
            b = core.groove_profile(u, T, P["groove"])
            self.create_line([c for uu, vv in zip(u, b) for c in (self._sx(uu), self._sy(vv))], fill=HL, width=3, tags="hl")
            self._dim_v(self._sx(T / 2), self._sy(0), self._sy(P["groove"]), f"{P['groove']:g}")
        elif key in ("recurve_l", "recurve_r"):
            left = key == "recurve_l"
            m = (g["xv"] <= g["rb_xl"]) if left else (g["xv"] >= g["rb_xr"])
            self.create_line([c for x, y in zip(g["xv"][m], g["yv"][m]) for c in (fx(x), fy(y))],
                             fill=HL, width=5, tags="hl")
            xm = g["rb_xl"] / 2 if left else (g["rb_xr"] + L) / 2
            self.create_text(fx(xm), fy(np.interp(xm, g["xv"], g["yv"])) + 16,
                             text=f"되굽힘 {P[key]:g}%", fill=HL, font=("Malgun Gothic", 9, "bold"), tags="hl")
        elif key == "T":
            self._dim_h(self._sx(0), self._sx(T), self._sy(db) - 14, f"T = {T:g}")
        elif key == "edge_r_ratio":
            u = np.linspace(0, T, 121)
            cr = core.crown_profile(u, T, R)
            for m in (u <= R + 1e-6, u >= T - R - 1e-6):
                self.create_line([c for uu, vv in zip(u[m], db - cr[m]) for c in (self._sx(uu), self._sy(vv))],
                                 fill=HL, width=4, tags="hl")
            self.create_text(self._sx(T / 2), self._sy(db) - 14, text=f"R{R:.1f}", fill=HL,
                             font=("Malgun Gothic", 9, "bold"), tags="hl")
        elif key in ("hole_d", "cb_d", "cb_depth", "hole_off"):
            for (C, V, T_, N, h) in core.hole_lines(g):
                if key == "hole_d":
                    self._ring(fx(C[0]), fy(C[1]), 8)
                elif key in ("cb_d", "cb_depth"):
                    self._ring(fx(V[0]), fy(V[1]), 9)
            lab = {"hole_d": f"Ø{P['hole_d']:g} (오목면 쪽)", "cb_d": f"Ø{P['cb_d']:g} (가죽 쪽)",
                   "cb_depth": f"깊이 {P['cb_depth']:g} (가죽 쪽)"}.get(key)
            if key == "hole_off":
                (C, V, *_ ) = core.hole_lines(g)[0]
                self._dim_h(fx(0), fx(C[0]), top_y, f"{P['hole_off']:g}")
                self.create_line(fx(C[0]), top_y, fx(C[0]), fy(V[1]), fill=HL, dash=(4, 2), tags="hl")
            else:
                self.create_text(fx(L / 2), top_y, text=lab, fill=HL, font=("Malgun Gothic", 9, "bold"), tags="hl")
        elif key in ("lip_h", "lip_len", "lip_fillet"):
            lb, w = P["lip_len"], P["lip_fillet"]
            for side in (0, 1):
                xs = (0, lb + w) if side == 0 else (L - lb - w, L)
                m = (g["x"] >= xs[0]) & (g["x"] <= xs[1])
                self.create_line([c for x, y in zip(g["xc"][m], g["yc"][m]) for c in (fx(x), fy(y))],
                                 fill=HL, width=3, tags="hl")
            if key == "lip_len":
                self._dim_h(fx(0), fx(lb), top_y, f"{lb:g}")
            elif key == "lip_fillet":
                self._dim_h(fx(lb), fx(lb + w), top_y, f"{w:g}")
            else:
                self.create_text(fx(lb + 30), top_y, text=f"턱 h{P['lip_h']:g} (양 끝)", fill=HL,
                                 font=("Malgun Gothic", 9, "bold"), tags="hl")
        elif key == "bed":
            xb = g["ub"] * L
            self.create_line(fx(xb), top_y, fx(xb), fy(g["yv"][ib]) + 6, fill=HL, width=2, dash=(6, 3), tags="hl")
            self.create_text(fx(xb), top_y - 6, text="2분할 위치(꺾임점)", fill=HL, font=("Malgun Gothic", 9, "bold"), tags="hl")
        if key in self.END_KEYS:
            self._end_zoom(key)
        self.itemconfigure(self.msg, text=DESCR.get(key, ""))
