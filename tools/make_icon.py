"""아이콘 생성: 저장소 루트에서  python tools/make_icon.py  -> assets/icon.ico, icon.png"""
import os, sys
sys.path.insert(0, os.getcwd())
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch
from matplotlib.transforms import Affine2D
from PIL import Image
import dojigae_core as c

g = c.geometry(1.25)
top = np.c_[g["xc"], g["yc"]]
bot = np.c_[g["xv"], g["yv"]][::-1]
body = np.vstack([top, bot])
lt = 9.0  # 아이콘용 가죽 두께(과장)
lea_out = np.c_[g["xv"] + lt * g["nvx"], g["yv"] + lt * g["nvy"]]
leather = np.vstack([np.c_[g["xv"], g["yv"]], lea_out[::-1]])
ctr = body.mean(0)

S = 1024
fig = plt.figure(figsize=(S / 100, S / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, S); ax.set_ylim(0, S); ax.axis("off")
fig.patch.set_alpha(0)
ax.add_patch(FancyBboxPatch((40, 40), S - 80, S - 80, boxstyle="round,pad=0,rounding_size=190",
                            fc="#16362a", ec="none"))
sc = 2.15
def place(pts, dx, dy, rot):
    t = Affine2D().translate(-ctr[0], -ctr[1]).scale(sc, sc * 1.55).rotate_deg(rot).translate(S / 2 + dx, S / 2 + dy)
    return t.transform(pts)
for dx, dy, rot, wood, edge in ((-18, 165, -6, "#e2b678", "#a8743c"), (18, -150, -6, "#d39f5e", "#8f5f2c")):
    ax.add_patch(Polygon(place(leather, dx, dy, rot), closed=True, fc="#2fae72", ec="#1d7a4f", lw=6, joinstyle="round"))
    ax.add_patch(Polygon(place(body, dx, dy, rot), closed=True, fc=wood, ec=edge, lw=8, joinstyle="round"))
    # 나뭇결 두 줄
    for f in (0.35, 0.62):
        ln = np.c_[g["xc"], g["yc"] * (1 - f) + np.interp(g["xc"], g["xv"], g["yv"]) * f][40:-40]
        p = place(ln, dx, dy, rot); ax.plot(p[:, 0], p[:, 1], color=edge, lw=5, alpha=0.45, solid_capstyle="round")
fig.savefig("assets/icon_1024.png", transparent=True)
im = Image.open("assets/icon_1024.png").convert("RGBA")
im.resize((256, 256), Image.LANCZOS).save("assets/icon.png")
im.save("assets/icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
os.remove("assets/icon_1024.png")
