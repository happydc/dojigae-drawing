"""
각궁도지개 제작도면 생성기 — 윈도우용 GUI
치수를 입력하고 [도면 생성]을 누르면 PDF(A3, 정면도 1:1)와 DXF(1:1)를 만듭니다.
"""
import os
import sys
import json
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import dojigae_core as core
import dojigae_3d as d3
import dojigae_viewer as viewer
from dojigae_preview import Preview

APP_TITLE = "각궁도지개 제작도면 생성기"
SETTINGS = os.path.join(os.path.expanduser("~"), ".gakgung_dojigae.json")

# (키, 라벨, 단위) — core.PARAM 항목
FIELDS = [
    ("L", "전체 길이", "mm"),
    ("bend_x", "왼쪽 끝→꺾임점", "mm"),
    ("T", "너비(판재 두께)", "mm"),
    ("d_end", "끝단 높이", "mm"),
    ("d_bend", "꺾임부 높이", "mm"),
    ("fore", "곡선 보정계수", "배"),
    ("leather", "가죽 두께", "mm"),
    ("groove", "볼록면 C홈 깊이", "mm"),
    ("hole_d", "끈구멍 지름", "mm"),
    ("cb_d", "매듭 보어 지름", "mm"),
    ("cb_depth", "매듭 보어 깊이", "mm"),
    ("hole_off", "끝→구멍 중심", "mm"),
    ("lip_h", "끈 감기 턱 높이", "mm"),
    ("lip_len", "끝→턱 위치", "mm"),
    ("lip_fillet", "턱 둥근 전이 길이", "mm"),
    ("edge_r_ratio", "오목면 모서리 R (T×)", "배"),
    ("recurve_l", "볼록면 끝 되굽힘(왼쪽)", "%"),
    ("recurve_r", "볼록면 끝 되굽힘(오른쪽)", "%"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        try:  # 창 아이콘 (exe 안에 묶인 경우 _MEIPASS 기준)
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            self._icon = tk.PhotoImage(file=os.path.join(base, "assets", "icon.png"))
            self.iconphoto(True, self._icon)
        except Exception:
            pass
        self.resizable(False, False)
        try:
            self.option_add("*Font", ("Malgun Gothic", 10))
        except Exception:
            pass
        self.defaults = dict(core.PARAM)
        self.def_f = {k: g["f"] for k, g in core.GRADES.items()}
        self.vars = {}
        self.fvars = {}
        self.gvars = {}
        self._build()
        self._bed_state()
        self._load()

    def _build(self):
        pad = dict(padx=6, pady=3)
        frm = ttk.LabelFrame(self, text="치수")
        frm.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        pfrm = ttk.LabelFrame(self, text="미리보기 — 항목에 마우스를 올려 보세요")
        pfrm.grid(row=0, column=1, rowspan=5, sticky="nsew", padx=(0, 8), pady=8)
        self.preview = Preview(pfrm)
        self.preview.pack(padx=6, pady=6)
        for i, (k, lab, unit) in enumerate(FIELDS):
            r, c = i % 9, (i // 9) * 3
            la = ttk.Label(frm, text=lab)
            la.grid(row=r, column=c, sticky="e", **pad)
            v = tk.StringVar(value=f"{core.PARAM[k]:g}")
            en = ttk.Entry(frm, textvariable=v, width=8, justify="right")
            en.grid(row=r, column=c + 1, **pad)
            ttk.Label(frm, text=unit).grid(row=r, column=c + 2, sticky="w", padx=(0, 14))
            self.vars[k] = v
            self._hover(k, la, en)
            en.bind("<FocusOut>", lambda e: self._refresh_preview(), add="+")
            en.bind("<Return>", lambda e: self._refresh_preview(), add="+")

        gfrm = ttk.LabelFrame(self, text="굴곡 등급 (표준 곡선 대비 처짐 배율)")
        gfrm.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        for i, (k, g) in enumerate(core.GRADES.items()):
            b = tk.BooleanVar(value=(k == "2"))   # 기본: 2형(표준)만
            ttk.Checkbutton(gfrm, text=f"{k}형 {g['name']}", variable=b).grid(row=0, column=i * 2, sticky="w", **pad)
            f = tk.StringVar(value=f"{g['f']:g}")
            ttk.Entry(gfrm, textvariable=f, width=6, justify="right").grid(row=0, column=i * 2 + 1, padx=(0, 16))
            self.gvars[k], self.fvars[k] = b, f
        self._hover("grade", gfrm)

        ofrm = ttk.Frame(self)
        ofrm.grid(row=2, column=0, sticky="ew", padx=8, pady=4)
        ttk.Label(ofrm, text="저장 폴더").pack(side="left")
        self.outdir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Documents", "도지개도면"))
        ttk.Entry(ofrm, textvariable=self.outdir, width=52).pack(side="left", padx=6)
        ttk.Button(ofrm, text="찾기…", command=self._browse).pack(side="left")

        bfrm = ttk.Frame(self)
        bfrm.grid(row=4, column=0, sticky="ew", padx=8, pady=(4, 10))
        self.want_dxf = tk.BooleanVar(value=False)
        self.want_stl = tk.BooleanVar(value=False)
        self.want_view = tk.BooleanVar(value=True)
        tfrm = ttk.LabelFrame(self, text="추가 출력 (PDF 도면은 항상 생성)")
        tfrm.grid(row=3, column=0, sticky="ew", padx=8, pady=4)
        r1 = ttk.Frame(tfrm); r1.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Checkbutton(r1, text="DXF (CAD·레이저용)", variable=self.want_dxf).pack(side="left")
        ttk.Checkbutton(r1, text="3D 뷰어 (HTML)", variable=self.want_view).pack(side="left", padx=12)
        ttk.Checkbutton(r1, text="STL (3D 모델·3D 프린트용)", variable=self.want_stl,
                        command=self._bed_state).pack(side="left")
        tfrm = ttk.Frame(tfrm); tfrm.pack(fill="x", padx=6, pady=4)
        ttk.Label(tfrm, text="프린터 베드 최대 길이").pack(side="left", padx=(0, 4))
        self.bed = tk.StringVar(value="250")
        bed_en = ttk.Entry(tfrm, textvariable=self.bed, width=6, justify="right")
        bed_en.pack(side="left")
        self.bed_en = bed_en
        self._hover("bed", bed_en)
        ttk.Label(tfrm, text="mm (초과 시 2분할 + 핀 구멍)").pack(side="left", padx=4)
        self.btn = ttk.Button(bfrm, text="도면 생성", command=self._run)
        self.btn.pack(side="left")
        ttk.Button(bfrm, text="기본값", command=self._reset).pack(side="left", padx=6)
        self.status = tk.StringVar(value="치수를 확인하고 [도면 생성]을 누르세요.")
        ttk.Label(bfrm, textvariable=self.status, foreground="#555").pack(side="left", padx=10)

    def _bed_state(self):
        self.bed_en.state(["!disabled"] if self.want_stl.get() else ["disabled"])

    def _hover(self, key, *widgets):
        for w in widgets:
            w.bind("<Enter>", lambda e, k=key: self.preview.show(k), add="+")
            w.bind("<FocusIn>", lambda e, k=key: self.preview.show(k), add="+")
            w.bind("<Leave>", lambda e: self._leave(), add="+")

    def _leave(self):
        self.preview.clear()

    def _refresh_preview(self):
        p = {}
        for k, _, _ in FIELDS:
            try:
                p[k] = float(self.vars[k].get())
            except ValueError:
                pass
        try:
            self.preview.refresh(p)
        except Exception:
            pass

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.outdir.get() or os.path.expanduser("~"))
        if d:
            self.outdir.set(d)

    def _reset(self):
        for k, v in self.vars.items():
            v.set(f"{self.defaults[k]:g}")
        for k, v in self.fvars.items():
            v.set(f"{self.def_f[k]:g}")
        for k, b in self.gvars.items():
            b.set(k == "2")
        self.want_dxf.set(False); self.want_stl.set(False); self.want_view.set(True)
        self._bed_state()
        self._refresh_preview()

    def _collect(self):
        params, factors = {}, {}
        for k, lab, _ in FIELDS:
            try:
                params[k] = float(self.vars[k].get())
            except ValueError:
                raise ValueError(f"'{lab}' 값이 숫자가 아닙니다.")
            if params[k] < 0:
                raise ValueError(f"'{lab}' 값은 0 이상이어야 합니다.")
        for k, v in self.fvars.items():
            try:
                factors[k] = float(v.get())
            except ValueError:
                raise ValueError(f"{k}형 배율이 숫자가 아닙니다.")
        keys = [k for k, b in self.gvars.items() if b.get()]
        if not keys:
            raise ValueError("굴곡 등급을 하나 이상 선택하세요.")
        if params["cb_d"] <= params["hole_d"]:
            raise ValueError("매듭 보어 지름은 끈구멍 지름보다 커야 합니다.")
        if not (0.15 * params["L"] <= params["bend_x"] <= 0.85 * params["L"]):
            raise ValueError("꺾임점은 전체 길이의 15~85% 범위여야 합니다.")
        for k in ("recurve_l", "recurve_r"):
            if params[k] > 100:
                raise ValueError("되굽힘은 0~100% 범위여야 합니다.")
        if params["edge_r_ratio"] > 0.5:
            raise ValueError("모서리 R 비율은 0.5 이하여야 합니다.")
        if params["groove"] <= 0:
            raise ValueError("C홈 깊이는 0보다 커야 합니다.")
        return params, factors, keys

    def _run(self):
        try:
            params, factors, keys = self._collect()
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, str(e))
            return
        out = self.outdir.get().strip() or "."
        want_dxf, want_stl, want_view = self.want_dxf.get(), self.want_stl.get(), self.want_view.get()
        try:
            bed = float(self.bed.get())
        except ValueError:
            if want_stl:
                messagebox.showwarning(APP_TITLE, "프린터 베드 길이가 숫자가 아닙니다.")
                return
            bed = 250.0
        self.btn.state(["disabled"])
        self.status.set("생성 중…")

        def work():
            try:
                files = core.generate(out, keys=keys, params=params, factors=factors, dxf=want_dxf)
                if want_stl:
                    files += d3.export_stl(out, keys=keys, bed=bed)
                if want_view:
                    vf = os.path.join(out, f"dojigae_L{core.PARAM['L']:.0f}_3d_viewer.html")
                    with open(vf, "w", encoding="utf-8") as fp:
                        fp.write(viewer.build_html(keys))
                    files.append(vf)
                self.after(0, lambda: self._done(out, files))
            except Exception as e:  # noqa
                self.after(0, lambda: self._fail(e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, out, files):
        self.btn.state(["!disabled"])
        self.status.set(f"완료: {len(files)}개 파일")
        self._save()
        if messagebox.askyesno(APP_TITLE, f"도면을 만들었습니다. ({len(files)}개 파일)\n\n" + "\n".join(os.path.basename(f) for f in files[:12])
                               + ("\n…" if len(files) > 12 else "")
                               + "\n\n저장 폴더를 열까요?"):
            if sys.platform.startswith("win"):
                os.startfile(out)  # noqa
            else:
                subprocess.Popen(["xdg-open", out])

    def _fail(self, e):
        self.btn.state(["!disabled"])
        self.status.set("오류")
        messagebox.showerror(APP_TITLE, f"도면 생성 중 오류가 났습니다.\n\n{e}")

    def _save(self):
        try:
            data = {"params": {k: v.get() for k, v in self.vars.items()},
                    "factors": {k: v.get() for k, v in self.fvars.items()},
                    "outdir": self.outdir.get()}
            with open(SETTINGS, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def _load(self):
        try:
            with open(SETTINGS, encoding="utf-8") as fp:
                data = json.load(fp)
            for k, v in data.get("params", {}).items():
                if k in self.vars:
                    self.vars[k].set(v)
            for k, v in data.get("factors", {}).items():
                if k in self.fvars:
                    self.fvars[k].set(v)
            if data.get("outdir"):
                self.outdir.set(data["outdir"])
            self._refresh_preview()
        except Exception:
            pass


if __name__ == "__main__":
    App().mainloop()
