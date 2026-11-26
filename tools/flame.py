# Построение диаграмм вызовов функций по данным трассировки VizTracer (формат Chrome Trace Event).
# Каждый прямоугольник — один вызов функции: левый край — вход, правый — выход.
import json, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 10})

COLORS = {"pipeline_subprocess": "#9ecae1", "pipeline_python": "#a1d99b", "Popen.communicate": "#fdd0a2",
          "_io.TextIOWrapper.read": "#fee6ce", "variant_a": "#c6dbef", "variant_b": "#fdd0a2",
          "variant_c": "#fcbba1", "variant_d": "#c7e9c0", "gzip_python": "#deebf7", "run": "#feedde",
          "lambda": "#e5f5e0", "ls_line": "#d9f0d3", "builtins.sorted": "#f0f0f0"}


def load(path):
    if path.endswith(".html"):
        s = open(path, encoding="utf-8", errors="replace").read()
        i = s.find('{"traceEvents"')
        d, _ = json.JSONDecoder().raw_decode(s[i:])
    else:
        d = json.load(open(path))
    ev = [e for e in d["traceEvents"] if e.get("ph") == "X"]
    names = {e["tid"]: e["args"]["name"] for e in d["traceEvents"]
             if e.get("ph") == "M" and e["name"] == "thread_name"}
    for e in ev:
        n = e["name"].split(" (")[0]
        n = n.replace("variant_d.<locals>.<lambda>", "lambda")
        e["short"] = n
    return ev, names


def depth_map(ev):
    """Глубина вложенности каждого вызова внутри своего потока."""
    out = {}
    for tid in {e["tid"] for e in ev}:
        stack = []
        for e in sorted([x for x in ev if x["tid"] == tid], key=lambda x: (x["ts"], -x["dur"])):
            while stack and stack[-1]["ts"] + stack[-1]["dur"] <= e["ts"]:
                stack.pop()
            out[id(e)] = len(stack)
            stack.append(e)
    return out


def ms(x):
    return f"{x:.1f}".replace(".", ",")


def draw(ax, ev, names, t0, t1, lanes, base, label_min=0.06, times=False, max_depth=9, hide=(), min_depth=0, keep=None, rename=None, outside=False):
    """lanes: список (tid, подпись дорожки). base — начало отсчёта времени, мкс."""
    dm = depth_map(ev)
    y = 0
    yt, yl = [], []
    span = (t1 - t0) / 1000
    for tid, title in lanes:
        sel = [e for e in ev if e["tid"] == tid and e["ts"] < t1 and e["ts"] + e["dur"] > t0
               and min_depth <= dm[id(e)] <= max_depth and e["short"] not in hide
               and (keep is None or e["short"] in keep)]
        if not sel:
            continue
        mind = min(dm[id(e)] for e in sel)
        nd = max(dm[id(e)] for e in sel) - mind + 1
        for e in sel:
            dd = dm[id(e)] - mind
            x0 = (max(e["ts"], t0) - base) / 1000
            x1 = (min(e["ts"] + e["dur"], t1) - base) / 1000
            yy = y + dd
            c = COLORS.get(e["short"], "#e0e0e0")
            ax.add_patch(Rectangle((x0, yy + 0.08), x1 - x0, 0.84, fc=c, ec="#333333", lw=0.6))
            w = (x1 - x0) / span
            if w >= label_min:
                txt = (rename or {}).get(e["short"], e["short"])
                if callable(txt): txt = txt(e)
                if times:
                    txt += f"\nвход {ms((e['ts'] - base) / 1000)} мс — выход {ms((e['ts'] + e['dur'] - base) / 1000)} мс"
                ax.text((x0 + x1) / 2, yy + 0.5, txt, ha="center", va="center", fontsize=9, clip_on=True)
            elif outside:
                txt = (rename or {}).get(e["short"], e["short"])
                if callable(txt): txt = txt(e)
                if times:
                    txt += f": вход {ms((e['ts'] - base) / 1000)} — выход {ms((e['ts'] + e['dur'] - base) / 1000)} мс"
                ax.text(x1 + span * 0.01, yy + 0.5, txt, ha="left", va="center", fontsize=9)
        yt.append(y + nd / 2)
        yl.append(title)
        ax.axhline(y - 0.05, color="#999999", lw=0.5)
        y += nd + 0.3
    ax.set_xlim((t0 - base) / 1000, (t1 - base) / 1000)
    ax.set_ylim(y, -0.3)
    ax.set_yticks(yt)
    ax.set_yticklabels(yl)
    ax.set_xlabel("Время от начала фрагмента, мс")
    ax.grid(axis="x", color="#cccccc", lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
