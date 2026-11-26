from flame import *
ev, names = load("part1_new.html")
main = [t for t, n in names.items() if n == "MainThread"][0]
subs = sorted([e for e in ev if e["short"] == "pipeline_subprocess"], key=lambda e: e["ts"])
k = 20                                  # фрагмент из середины серии замеров
a0, a1 = subs[k]["ts"] - 300, subs[k + 3]["ts"] + subs[k + 3]["dur"] + 300
med = sorted(subs, key=lambda e: e["dur"])[len(subs) // 2]
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.5, 4.2), gridspec_kw={"height_ratios": [1, 1.3]})
draw(ax1, ev, names, a0, a1, [(main, "MainThread")], a0, label_min=0.12, hide=("_io.TextIOWrapper.read",), min_depth=2)
ax1.set_title("а) четыре последовательных вызова в серии замеров", fontsize=10, loc="left")
b0, b1 = med["ts"], med["ts"] + med["dur"] + 1
draw(ax2, ev, names, b0, b1, [(main, "MainThread")], med["ts"], label_min=0.2, times=True, min_depth=3)
com = [e for e in ev if e["short"] == "Popen.communicate" and med["ts"] <= e["ts"] <= med["ts"] + med["dur"]][0]
gap = (com["ts"] - med["ts"]) / 1000
ax2.annotate(f"запуск ls и grep\n(Popen), {ms(gap)} мс", xy=(gap / 2, 1.5), xytext=(0.3, 3.35),
             fontsize=9, ha="left", bbox=dict(fc="white", ec="none", pad=1), arrowprops=dict(arrowstyle="->", lw=0.7))
ax2.set_ylim(3.75, -0.3)
ax2.set_title("б) один вызов, время входа и выхода (отсчёт от входа в функцию)", fontsize=10, loc="left")
ax2.set_xlabel("Время от входа в pipeline_subprocess, мс")
fig.tight_layout()
fig.savefig("fig1.png", dpi=220)
print("call", ms(med["dur"] / 1000), "gap", ms(gap), "communicate", ms(com["dur"] / 1000))
