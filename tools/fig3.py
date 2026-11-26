from flame import *
ev, names = load("part2.json")
main = [t for t, n in names.items() if n == "MainThread"][0]
va = sorted([e for e in ev if e["short"] == "variant_a"], key=lambda e: e["ts"])[-1]   # замерный проход
vd = sorted([e for e in ev if e["short"] == "variant_d"], key=lambda e: e["ts"])[-1]
vc = sorted([e for e in ev if e["short"] == "variant_c"], key=lambda e: e["ts"])[-1]
t0, t1 = va["ts"] - 2000, vd["ts"] + vd["dur"] + 2000
workers = sorted({e["tid"] for e in ev if e["short"] == "lambda" and e["ts"] >= vd["ts"]},
                 key=lambda t: int(names[t].split("-")[1]))
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 5.4), gridspec_kw={"height_ratios": [1, 2.4]})
draw(ax1, ev, names, t0, t1, [(main, "MainThread")], va["ts"], label_min=0.05, min_depth=2, max_depth=2,
     rename={"variant_a": lambda e: f"A: {ms(e['dur'] / 1000)} мс", "variant_b": lambda e: f"B: {ms(e['dur'] / 1000)} мс", "variant_c": "C", "variant_d": "D"})
for v in ("variant_a", "variant_b", "variant_c", "variant_d"):
    e = sorted([x for x in ev if x["short"] == v], key=lambda x: x["ts"])[-1]
    x0 = (e["ts"] - va["ts"]) / 1000
    print(v, ms(x0), ms(e["dur"] / 1000))
ax1.set_title("а) четыре варианта в замерном проходе (вызовы variant_a … variant_d)", fontsize=10, loc="left")
ax1.set_xlabel("Время от входа в variant_a, мс")
c0, c1 = vc["ts"] - 300, vd["ts"] + vd["dur"] + 2000
lanes = [(main, "MainThread")] + [(t, f"поток {i}") for i, t in enumerate(workers, 1)]
draw(ax2, ev, names, c0, c1, lanes, vc["ts"], label_min=0.04, max_depth=12,
     keep=("variant_c", "variant_d", "Popen.wait", "gzip_python"),
     rename={"Popen.wait": "wait", "gzip_python": "gzip", "variant_c": lambda e: f"variant_c (C): {ms(e['dur'] / 1000)} мс", "variant_d": lambda e: f"variant_d (D): {ms(e['dur'] / 1000)} мс"})
ax2.set_title("б) варианты C и D крупно: подпроцессы gzip и 10 рабочих потоков", fontsize=10, loc="left")
ax2.set_xlabel("Время от входа в variant_c, мс")
fig.tight_layout()
fig.savefig("fig3.png", dpi=220)
