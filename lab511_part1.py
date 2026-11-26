"""Практическая работа 5.11. Часть 1: конвейер из двух подпроцессов и его аналог без подпроцессов.

Задача конвейера: получить список файлов каталога (ls -l) и передать его на вход
второго процесса, который оставляет только строки по шаблону (grep pip).
Запуск: python3 lab511_part1.py [число_повторов]
  без аргумента — быстрый показ (50 повторов, около 3 секунд);
  python3 lab511_part1.py 300 — полная статистика для отчёта.
"""
import os
import platform
import statistics
import stat
import subprocess
import sys
import tempfile
import time

PATTERN = "pip"
N_FILES = 5000          # всего файлов в тестовом каталоге
N_MATCH = 500           # из них с шаблоном "pip" в имени


def make_testdir():
    """Создаёт тестовый каталог: 500 файлов pip* и 4500 прочих."""
    path = tempfile.mkdtemp(prefix="lab511_")
    for i in range(N_FILES):
        name = f"{PATTERN}{i}" if i < N_MATCH else f"data{i}.txt"
        with open(os.path.join(path, name), "w") as f:
            f.write("x")
    return path


def pipeline_subprocess(directory):
    """Конвейер из двух подпроцессов: ls -l | grep pip."""
    proc_ls = subprocess.Popen(["ls", "-l"], stdout=subprocess.PIPE, cwd=directory, text=True)
    proc_grep = subprocess.Popen(["grep", PATTERN], stdin=proc_ls.stdout,
                                 stdout=subprocess.PIPE, text=True)
    proc_ls.stdout.close()                      # чтобы ls получил SIGPIPE, если grep завершится раньше
    out, _ = proc_grep.communicate()
    proc_ls.wait()
    return out.splitlines()


def pipeline_python(directory):
    """Аналог без подпроцессов: тот же список строк (права, размер, имя) и тот же фильтр."""
    lines = []
    with os.scandir(directory) as it:
        for entry in it:
            info = entry.stat()
            lines.append(f"{stat.filemode(info.st_mode)} {info.st_size} {entry.name}")
    return [line for line in lines if PATTERN in line]


def names(lines):
    return sorted(line.split()[-1] for line in lines)


def timeit(func, directory, runs):
    func(directory)                             # прогрев (кэш файловой системы)
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        func(directory)
        times.append((time.perf_counter() - t0) * 1000)   # мс
    return times


def report(title, times):
    mean = statistics.mean(times)
    print(f"{title:<34}n={len(times):<4}"
          f"среднее {mean:8.2f} мс | медиана {statistics.median(times):8.2f} | "
          f"σ {statistics.stdev(times) if len(times) > 1 else 0:7.2f} | "
          f"мин {min(times):8.2f} | макс {max(times):8.2f}")
    return mean


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    print(f"Платформа: {platform.platform()}, Python {platform.python_version()}, ядер: {os.cpu_count()}")
    d = make_testdir()
    print(f"Тестовый каталог: {N_FILES} файлов, из них с «{PATTERN}» в имени: {N_MATCH}\n")

    out_sub = pipeline_subprocess(d)
    out_py = pipeline_python(d)
    print("Первые 3 строки конвейера ls -l | grep pip:")
    for line in out_sub[:3]:
        print("  ", line)
    print(f"Строк после фильтра: подпроцессы — {len(out_sub)}, Python — {len(out_py)}")
    print("Наборы имён совпадают:", names(out_sub) == names(out_py), "\n")

    print(f"Повторов: {runs}")
    m_sub = report("Конвейер из подпроцессов", timeit(pipeline_subprocess, d, runs))
    m_py = report("Аналог без подпроцессов (Python)", timeit(pipeline_python, d, runs))
    print(f"\nОтношение среднего времени (подпроцессы / Python): {m_sub / m_py:.2f}")

    for name in os.listdir(d):
        os.remove(os.path.join(d, name))
    os.rmdir(d)
