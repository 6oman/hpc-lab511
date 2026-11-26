"""Практическая работа 5.11. Часть 2: параллельное сжатие файлов подпроцессами.

Четыре варианта сжатия набора файлов в формат gzip:
  A) библиотека gzip, последовательно (без подпроцессов);
  B) внешняя команда gzip, подпроцессы по одному (последовательно);
  C) внешняя команда gzip, параллельные подпроцессы (не больше ядер сразу);
  D) библиотека gzip в ThreadPoolExecutor (потоки; zlib освобождает GIL).
Запуск: python3 lab511_part2.py [число_повторов]
  без аргумента — быстрый показ (1 повтор, несколько секунд);
  python3 lab511_part2.py 30 — полная статистика для отчёта.
"""
import gzip
import hashlib
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

N_FILES = 16                      # количество файлов
FILE_MB = 2                       # размер каждого файла, МБ
LEVEL = 6                         # уровень сжатия (как у команды gzip по умолчанию)
WORKERS = os.cpu_count() or 4


def make_files(directory):
    """Создаёт текстоподобные файлы (хорошо сжимаются, как логи и CSV)."""
    rnd = random.Random(511)
    vocab = [bytes(rnd.choices(b"abcdefghijklmnopqrstuvwxyz", k=rnd.randint(3, 9))) for _ in range(5000)]
    paths = []
    for i in range(N_FILES):
        buf, size = [], 0
        while size < FILE_MB * 1024 * 1024:
            line = b" ".join(rnd.choices(vocab, k=12)) + b"\n"
            buf.append(line)
            size += len(line)
        path = os.path.join(directory, f"data{i:02d}.txt")
        with open(path, "wb") as f:
            f.write(b"".join(buf))
        paths.append(path)
    return paths


def gzip_python(src, dst):
    with open(src, "rb") as fin, gzip.open(dst, "wb", compresslevel=LEVEL) as fout:
        shutil.copyfileobj(fin, fout, 1024 * 1024)


def variant_a(paths, outdir):
    for p in paths:
        gzip_python(p, os.path.join(outdir, os.path.basename(p) + ".gz"))


def variant_b(paths, outdir):
    for p in paths:
        with open(os.path.join(outdir, os.path.basename(p) + ".gz"), "wb") as fout:
            subprocess.run(["gzip", f"-{LEVEL}", "-c", p], stdout=fout, check=True)


def variant_c(paths, outdir):
    running = []
    for p in paths:
        while len(running) >= WORKERS:          # не больше WORKERS подпроцессов одновременно
            proc, fout = running.pop(0)
            proc.wait()
            fout.close()
        fout = open(os.path.join(outdir, os.path.basename(p) + ".gz"), "wb")
        running.append((subprocess.Popen(["gzip", f"-{LEVEL}", "-c", p], stdout=fout), fout))
    for proc, fout in running:
        proc.wait()
        fout.close()


def variant_d(paths, outdir):
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(lambda p: gzip_python(p, os.path.join(outdir, os.path.basename(p) + ".gz")), paths))


VARIANTS = [
    ("A: gzip (библиотека), последовательно", variant_a),
    ("B: gzip (команда), по одному", variant_b),
    ("C: gzip (команда), параллельно", variant_c),
    ("D: gzip (библиотека), потоки", variant_d),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(paths, outdir):
    """Распаковывает результаты и сверяет с исходными файлами."""
    for p in paths:
        with open(p, "rb") as f:
            expected = sha(f.read())
        with gzip.open(os.path.join(outdir, os.path.basename(p) + ".gz"), "rb") as f:
            if sha(f.read()) != expected:
                return False
    return True


def clean(outdir):
    for name in os.listdir(outdir):
        os.remove(os.path.join(outdir, name))


def stats_line(title, times, base_mean):
    mean = statistics.mean(times)
    sd = statistics.stdev(times) if len(times) > 1 else 0.0
    print(f"{title:<40}n={len(times):<3}среднее {mean:6.3f} с | медиана {statistics.median(times):6.3f} | "
          f"σ {sd:6.3f} | мин {min(times):6.3f} | макс {max(times):6.3f} | ускорение ×{base_mean / mean:5.2f}")


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print(f"Платформа: {platform.platform()}, Python {platform.python_version()}, ядер: {os.cpu_count()}, "
          f"одновременных потоков/подпроцессов: {WORKERS}")
    print(f"Набор данных: {N_FILES} файлов по {FILE_MB} МБ, всего {N_FILES * FILE_MB} МБ, уровень сжатия {LEVEL}")

    root = tempfile.mkdtemp(prefix="lab511_")
    src_dir, out_dir = os.path.join(root, "src"), os.path.join(root, "out")
    os.makedirs(src_dir)
    os.makedirs(out_dir)
    files = make_files(src_dir)
    total = sum(os.path.getsize(p) for p in files)

    print("\nПроверка корректности (распаковка и сравнение с исходными файлами):")
    for title, func in VARIANTS:
        func(files, out_dir)
        ok = verify(files, out_dir)
        packed = sum(os.path.getsize(os.path.join(out_dir, n)) for n in os.listdir(out_dir))
        print(f"  {title:<40}{'совпадает' if ok else 'ОШИБКА'}, размер архивов {packed / total * 100:5.1f} % от исходного")
        clean(out_dir)

    print(f"\nПовторов каждого варианта: {runs}")
    results = {}
    warm = 1 if runs > 1 else 0                # при полной статистике первый проход — прогрев
    for r in range(runs + warm):
        for title, func in VARIANTS:
            t0 = time.perf_counter()
            func(files, out_dir)
            dt = time.perf_counter() - t0
            clean(out_dir)
            if r >= warm:
                results.setdefault(title, []).append(dt)

    base = statistics.mean(results[VARIANTS[0][0]])
    for title, _ in VARIANTS:
        stats_line(title, results[title], base)

    if runs > 1:                               # CSV пишем только при полной статистике
        csv_name = f"timings_{platform.system().lower()}.csv"
        with open(csv_name, "w", encoding="utf-8") as f:
            f.write("run;" + ";".join(t.split(":")[0] for t, _ in VARIANTS) + "\n")
            for i in range(runs):
                f.write(f"{i + 1};" + ";".join(f"{results[t][i]:.4f}" for t, _ in VARIANTS) + "\n")
        print(f"\nСырые замеры сохранены в файл {csv_name}")
    shutil.rmtree(root)
