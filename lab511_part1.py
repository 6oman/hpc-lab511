"""Практическая работа 5.11. Часть 1: конвейер из двух подпроцессов и его аналог без подпроцессов.

Задача конвейера: получить список файлов каталога (ls -l) и передать его на вход
второго процесса, который оставляет только строки по шаблону (grep pip).
Запуск: python3 lab511_part1.py [число_повторов]
  без аргумента — быстрый показ (50 повторов, около 3 секунд);
  python3 lab511_part1.py 300 — полная статистика для отчёта.
"""
import fnmatch
import grp
import os
import platform
import pwd
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


C_ENV = dict(os.environ, LC_ALL="C")        # одинаковый формат даты в ls на любой системе
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def pipeline_subprocess(directory):
    """Конвейер из двух подпроцессов: ls -l | grep pip."""
    proc_ls = subprocess.Popen(["ls", "-l"], stdout=subprocess.PIPE, cwd=directory,
                               env=C_ENV, text=True)
    proc_grep = subprocess.Popen(["grep", PATTERN], stdin=proc_ls.stdout,
                                 stdout=subprocess.PIPE, env=C_ENV, text=True)
    proc_ls.stdout.close()                      # чтобы ls получил SIGPIPE, если grep завершится раньше
    out, _ = proc_grep.communicate()
    proc_ls.wait()
    return out.splitlines()


def user_name(uid, cache={}):
    if uid not in cache:
        try:
            cache[uid] = pwd.getpwuid(uid).pw_name
        except KeyError:
            cache[uid] = str(uid)
    return cache[uid]


def group_name(gid, cache={}):
    if gid not in cache:
        try:
            cache[gid] = grp.getgrgid(gid).gr_name
        except KeyError:
            cache[gid] = str(gid)
    return cache[gid]


def ls_line(entry):
    """Строка в формате ls -l: права, ссылки, владелец, группа, размер, дата, имя."""
    info = entry.stat()
    t = time.localtime(info.st_mtime)
    if abs(time.time() - info.st_mtime) < 182 * 24 * 3600:    # как ls: свежие файлы — время
        when = f"{MONTHS[t.tm_mon - 1]} {t.tm_mday:2d} {t.tm_hour:02d}:{t.tm_min:02d}"
    else:                                                     # старые — год
        when = f"{MONTHS[t.tm_mon - 1]} {t.tm_mday:2d}  {t.tm_year}"
    return (f"{stat.filemode(info.st_mode)} {info.st_nlink} {user_name(info.st_uid)} "
            f"{group_name(info.st_gid)} {info.st_size} {when} {entry.name}")


def pipeline_python(directory):
    """Аналог без подпроцессов: те же поля, что у ls -l, та же сортировка и тот же фильтр,
    что у grep (поиск подстроки во всей строке, а не только в имени файла)."""
    with os.scandir(directory) as it:
        lines = [ls_line(entry) for entry in sorted(it, key=lambda e: e.name)]
    return [line for line in lines if PATTERN in line]


def names_python(directory):
    """Если нужны только имена файлов: фильтр по имени через fnmatch (как glob "*pip*").
    Это не полный аналог grep: grep ищет шаблон во всей строке ls -l (в том числе в имени
    владельца), а здесь проверяется только имя файла."""
    return sorted(fnmatch.filter(os.listdir(directory), f"*{PATTERN}*"))


def same_lines(a, b):
    """Доля строк, совпадающих полностью (без учёта ширины колонок)."""
    norm = lambda lines: [" ".join(line.split()) for line in lines]
    return sum(x == y for x, y in zip(norm(a), norm(b))) / max(len(a), 1)


def names(lines):
    if lines and " " not in lines[0]:
        return sorted(lines)
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
    print("Наборы имён совпадают:", names(out_sub) == names(out_py))
    print(f"Строки совпадают полностью: {same_lines(out_sub, out_py):.0%}")
    print("Имена через fnmatch совпадают:", names(out_sub) == names_python(d), "\n")

    print(f"Повторов: {runs}")
    m_sub = report("Конвейер из подпроцессов", timeit(pipeline_subprocess, d, runs))
    m_py = report("Полный аналог ls -l (Python)", timeit(pipeline_python, d, runs))
    m_nm = report("Только имена, fnmatch (Python)", timeit(names_python, d, runs))
    print(f"\nОтношение среднего времени: подпроцессы / полный аналог = {m_sub / m_py:.2f}, "
          f"подпроцессы / fnmatch = {m_sub / m_nm:.2f}")

    for name in os.listdir(d):
        os.remove(os.path.join(d, name))
    os.rmdir(d)
