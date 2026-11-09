"""
웹(브라우저, Pyodide) 버전의 파이썬 쪽 연결부.
dojigae_core / dojigae_3d / dojigae_viewer 를 그대로 쓰고, 화면에 필요한 값만 JSON으로 넘긴다.
입력 항목(FIELDS)과 설명(DESCR)은 데스크톱 GUI·미리보기 파일에서 읽어 와서 한 곳에서만 관리한다.
3D 프린트용 구멍·2분할 불리언은 Pyodide에 manifold3d가 없어 브라우저(manifold-3d WASM)에서 한다.
"""
import ast
import json
import os
import shutil

import numpy as np
import dojigae_core as core
import dojigae_3d as d3
import dojigae_viewer as viewer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = dict(core.PARAM)
DEF_F = {k: g["f"] for k, g in core.GRADES.items()}
OUT = "/out"


def _literal(fn, name):
    """tkinter를 import하지 않고 파일에서 상수만 읽음"""
    with open(os.path.join(HERE, fn), encoding="utf-8") as fp:
        tree = ast.parse(fp.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def ui():
    return json.dumps(dict(
        fields=_literal("dojigae_gui.py", "FIELDS"),
        descr=_literal("dojigae_preview.py", "DESCR"),
        defaults=DEFAULTS,
        grades={k: dict(name=g["name"], f=g["f"]) for k, g in core.GRADES.items()},
    ), ensure_ascii=False)


def _set(params, factors=None):
    core.PARAM.clear()
    core.PARAM.update(DEFAULTS)
    core.PARAM.update({k: float(v) for k, v in (params or {}).items() if k in DEFAULTS})
    for k in core.GRADES:
        core.GRADES[k]["f"] = float((factors or {}).get(k, DEF_F[k]))


def _errors(params, factors=None, keys=None):
    """데스크톱 GUI와 같은 입력 검사"""
    e = []
    labels = {k: lab for k, lab, _ in _literal("dojigae_gui.py", "FIELDS")}
    p = {}
    for k in DEFAULTS:
        if k not in labels:
            continue
        try:
            p[k] = float(params.get(k, DEFAULTS[k]))
        except (TypeError, ValueError):
            e.append(f"'{labels[k]}' 값이 숫자가 아닙니다.")
            continue
        if p[k] < 0:
            e.append(f"'{labels[k]}' 값은 0 이상이어야 합니다.")
    if e:
        return e
    if not (0.15 * p["L"] <= p["bend_x"] <= 0.85 * p["L"]):
        e.append("꺾임점은 전체 길이의 15~85% 범위여야 합니다.")
    if p["edge_r_ratio"] > 0.5:
        e.append("모서리 R 비율은 0.5 이하여야 합니다.")
    if p["groove"] <= 0:
        e.append("C홈 깊이는 0보다 커야 합니다.")
    if p["cb_d"] <= p["hole_d"]:
        e.append("매듭 보어 지름은 끈구멍 지름보다 커야 합니다.")
    if keys is not None and not keys:
        e.append("굴곡 등급을 하나 이상 선택하세요.")
    for k, v in (factors or {}).items():
        try:
            if float(v) <= 0:
                e.append(f"{k}형 배율은 0보다 커야 합니다.")
        except (TypeError, ValueError):
            e.append(f"{k}형 배율이 숫자가 아닙니다.")
    return e


def _r(a, n=2):
    return np.round(np.asarray(a, float), n).tolist()


def preview(params_json):
    """미리보기용 형상 (표준 곡선 f=1.0)"""
    params = json.loads(params_json)
    errs = _errors(params)
    if errs:
        return json.dumps(dict(errors=errs), ensure_ascii=False)
    try:
        _set(params)
        g = core.geometry(1.0)
    except Exception as ex:  # noqa
        return json.dumps(dict(errors=[f"계산 오류: {ex}"]), ensure_ascii=False)
    s = slice(None, None, 3)
    holes = [[_r(C), _r(V), _r(T_, 4), _r(N, 4), float(h)] for (C, V, T_, N, h) in core.hole_lines(g)]
    ib = int(np.argmin(g["yc0"]))
    return json.dumps(dict(
        x=_r(g["x"][s]), xc=_r(g["xc"][s]), yc=_r(g["yc"][s]), yc0=_r(g["yc0"][s]),
        xv=_r(g["xv"][s]), yv=_r(g["yv"][s]), nvx=_r(g["nvx"][s], 4), nvy=_r(g["nvy"][s], 4),
        ub=float(g["ub"]), dmax=float(g["d"].max()), ib=dict(xc=float(g["xc"][ib]), yc=float(g["yc"][ib]),
        yc0=float(g["yc0"][ib]), yv=float(g["yv"][ib])),
        end=dict(yc0=float(g["yc"][0]), yv0=float(g["yv"][0]), yc1=float(g["yc"][-1]), yv1=float(g["yv"][-1])),
        holes=holes, P={k: float(v) for k, v in core.PARAM.items()}, errors=[],
    ), ensure_ascii=False)


def generate(params_json, factors_json, keys_json, want3d):
    """PDF·DXF(·3D 뷰어)를 /out 에 만들고, 3D 프린트용 STL 작업 목록(메시+절삭 원기둥)을 돌려줌"""
    params, factors, keys = json.loads(params_json), json.loads(factors_json), json.loads(keys_json)
    errs = _errors(params, factors, keys)
    if errs:
        return json.dumps(dict(errors=errs), ensure_ascii=False)
    _set(params, factors)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    files = core.generate(OUT, keys=keys)
    jobs = []
    if want3d:
        vf = os.path.join(OUT, f"dojigae_L{core.PARAM['L']:.0f}_3d_viewer.html")
        with open(vf, "w", encoding="utf-8") as fp:
            fp.write(viewer.build_html(keys))
        files.append(vf)
        for k in keys:
            G = core.GRADES[k]
            m = d3.build_mesh(G["f"])
            g = core.geometry(G["f"])
            xs, pins = d3.split_spec(g)
            cyl = lambda c: [_r(c[0], 4), _r(c[1], 6), float(c[2]), float(c[3])]
            jobs.append(dict(
                base=f"dojigae_L{core.PARAM['L']:.0f}_{k}_{G['code']}",
                body=dict(v=_r(m["body"][0].ravel(), 4), f=m["body"][1].ravel().tolist()),
                leather=dict(v=_r(m["leather"][0].ravel(), 4), f=m["leather"][1].ravel().tolist()),
                cuts=[cyl(c) for c in d3.hole_cuts(g)],
                xs=xs, pins=[cyl(c) for c in pins],
            ))
    return json.dumps(dict(files=files, jobs=jobs, errors=[]), ensure_ascii=False)
