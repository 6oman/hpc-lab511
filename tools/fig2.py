from flame import *
ev, names = load("part1_new.html")
main = [t for t, n in names.items() if n == "MainThread"][0]
def med(n):
    c = sorted([e for e in ev if e["short"] == n], key=lambda e: e["dur"]); return c[len(c) // 2]
calls = [("pipeline_python", "а) полный аналог ls -l без подпроцессов (pipeline_python)"),
         ("names_python", "б) только имена через fnmatch (names_python)")]
span = med("pipeline_subprocess")["dur"] / 1000 + 0.05     # тот же масштаб, что на рисунке 1, б
fig, axes = plt.subplots(2, 1, figsize=(6.5, 3.1), gridspec_kw={"height_ratios": [2, 1.25]})
for ax, (n, title) in zip(axes, calls):
    e = med(n)
    sub = [k for k in ev if k["tid"] != main or k["ts"] + k["dur"] > e["ts"] + e["dur"] or k["ts"] >= e["ts"]]
    sub = [k for k in sub if not (k["tid"] == main and k["ts"] > e["ts"] + e["dur"])]
    draw(ax, sub, names, e["ts"], e["ts"] + span * 1000, [(main, "MainThread")], e["ts"],
         label_min=0.45, times=True, min_depth=3, outside=True,
         hide=("posix.listdir", "filter"), rename={"builtins.sorted": "sorted (обход каталога)", "posix.listdir": "listdir", "filter": "filter"})
    ax.set_xlim(0, span)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlabel("")
    print(n, ms(e["dur"] / 1000), [(k["short"], ms((k["ts"]-e["ts"])/1000), ms(k["dur"]/1000)) for k in ev if k["tid"]==main and e["ts"]<k["ts"]<e["ts"]+e["dur"]])
axes[-1].set_xlabel("Время от входа в функцию, мс")
fig.tight_layout()
fig.savefig("fig2.png", dpi=220)
