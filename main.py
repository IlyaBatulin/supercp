#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*_args, **_kwargs) -> bool:  # type: ignore[misc]
        return False


import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_BASE = Path(__file__).resolve().parent
load_dotenv(_BASE / ".env", encoding="utf-8")

LOG_PATH = _BASE / "lab.log"
CHARTS_DIR = _BASE / "charts"
MAIN_CHARTS_DIR = CHARTS_DIR / "main"
MAIN_CHARTS_DIR.mkdir(parents=True, exist_ok=True)

ISSUED_LOGIN = os.environ.get("LAB_LOGIN", "operator")
ISSUED_PASSWORD = os.environ.get("LAB_PASSWORD", "SecureLab-2026")
ACCESS_KEY = os.environ.get("SUPERCOMPUTER_ACCESS_KEY", "demo-key")

_INTEGRATION_1 = os.environ.get("SECRET_INTEGRATION_1", "")
_INTEGRATION_2 = os.environ.get("SECRET_INTEGRATION_2", "")
_INTEGRATION_3 = os.environ.get("SECRET_INTEGRATION_3", "")

# Узлы кластера: id → подпись для UI; пароль в env NODE_PASSWORD_<ID> (ID в верхнем регистре)
NODE_CATALOG: list[tuple[str, str]] = [
    ("alpha", "Узел α — вычислительный"),
    ("beta", "Узел β — вычислительный"),
    ("gamma", "Узел γ — хранилище"),
]

_DEFAULT_NODE_PASSWORDS: dict[str, str] = {
    "alpha": "node-alpha-1",
    "beta": "node-beta-1",
    "gamma": "node-gamma-1",
}


def node_password(node_id: str) -> str:
    env_key = f"NODE_PASSWORD_{node_id.upper()}"
    return os.environ.get(env_key, _DEFAULT_NODE_PASSWORDS.get(node_id, "node-secret"))


def known_node_ids() -> set[str]:
    return {nid for nid, _ in NODE_CATALOG}


def init_logging(level: int = logging.INFO) -> logging.Logger:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger("lab")
    root.setLevel(level)
    root.handlers.clear()

    h_console = logging.StreamHandler(sys.stdout)
    h_console.setLevel(level)
    h_console.setFormatter(logging.Formatter(fmt, datefmt))

    h_file = logging.FileHandler(LOG_PATH, encoding="utf-8")
    h_file.setLevel(level)
    h_file.setFormatter(logging.Formatter(fmt, datefmt))

    root.addHandler(h_console)
    root.addHandler(h_file)

    root.info("Инициализация логирования (console + %s)", LOG_PATH.name)
    root.info(
        "политика доступа: логин/пароль из env (%s/%s), ключ из env (%s)",
        "да" if os.environ.get("LAB_LOGIN") else "нет (дефолт operator)",
        "да" if os.environ.get("LAB_PASSWORD") else "нет (дефолт)",
        "да" if os.environ.get("SUPERCOMPUTER_ACCESS_KEY") else "нет (demo-key)",
    )
    root.debug(
        "secrets integration len: %s/%s/%s",
        len(_INTEGRATION_1),
        len(_INTEGRATION_2),
        len(_INTEGRATION_3),
    )
    env_file = _BASE / ".env"
    if env_file.is_file():
        try:
            import dotenv as _dotenv  # noqa: F401

            _ = _dotenv
            root.info("найден %s — переменные из него учтены при старте", env_file.name)
        except ImportError:
            root.warning(
                "файл %s есть, но пакет python-dotenv не установлен — "
                "выполните: pip install -r requirements.txt",
                env_file.name,
            )
    return root


def new_stats() -> dict:
    return {
        "granted": 0,
        "denied": 0,
        "deny_reasons": defaultdict(int),
        "node_selections": defaultdict(int),
        "node_access_granted": defaultdict(int),
        "node_access_denied_by_node": defaultdict(int),
        "node_access_denied_reasons": defaultdict(int),
    }


def _inc(stats: dict, field: str, key: str, amount: int = 1) -> None:
    """
    Инкремент счётчика stats[field][key].
    В CLI мы используем defaultdict(int), а во Flask (cookie-session) структуры
    сериализуются в обычные dict — поэтому делаем безопасно.
    """
    bucket = stats.get(field)
    if not isinstance(bucket, dict):
        bucket = {}
        stats[field] = bucket
    bucket[key] = int(bucket.get(key, 0)) + int(amount)


def log_issued_credentials_safe(log: logging.Logger) -> None:
    log.info(
        "конфигурация доступа: пользователь=%s; узлы=%s (секреты не логируются)",
        ISSUED_LOGIN,
        ",".join(nid for nid, _ in NODE_CATALOG),
    )


def _save_fig(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def build_charts(log: logging.Logger, stats: dict) -> dict[str, list[Path]]:
    granted = stats["granted"]
    denied_total = stats["denied"]
    deny_reasons = dict(stats["deny_reasons"])
    node_sel = dict(stats["node_selections"])
    node_ok = dict(stats["node_access_granted"])
    node_deny = dict(stats["node_access_denied_reasons"])
    node_deny_by = dict(stats["node_access_denied_by_node"])
    out: dict[str, list[Path]] = {"main": []}

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(
        ["доступ разрешён", "доступ запрещён"],
        [granted, denied_total],
        color=["#2ca02c", "#d62728"],
    )
    ax.set_title("Вход в систему (легитимные vs отказ)")
    ax.set_ylabel("Попыток")
    p1 = MAIN_CHARTS_DIR / "access_granted_vs_denied.png"
    _save_fig(fig, p1)
    out["main"].append(p1)
    log.info("chart(main): %s", p1.name)

    fig, ax = plt.subplots(figsize=(6, 6))
    if deny_reasons and sum(deny_reasons.values()) > 0:
        ax.pie(
            list(deny_reasons.values()),
            labels=list(deny_reasons.keys()),
            autopct="%1.0f%%",
            startangle=90,
        )
        ax.set_title("Причины отказа при входе")
    else:
        ax.text(0.5, 0.5, "нет отказов при входе", ha="center", va="center")
        ax.set_axis_off()
    p2 = MAIN_CHARTS_DIR / "login_denial_reasons.png"
    _save_fig(fig, p2)
    out["main"].append(p2)
    log.info("chart(main): %s", p2.name)

    categories = {"вход_ok": granted}
    for k, v in sorted(deny_reasons.items()):
        categories["вход_отказ: " + k] = v
    fig, ax = plt.subplots(figsize=(10, 4))
    if any(categories.values()):
        ax.bar(list(categories.keys()), list(categories.values()), color="#1f77b4")
        ax.set_title("Итоги проверки входа (логин / пароль / ключ)")
        ax.set_ylabel("Событий")
        plt.setp(ax.get_xticklabels(), rotation=22, ha="right")
    else:
        ax.text(0.5, 0.5, "нет данных входа", ha="center", va="center")
        ax.set_axis_off()
    p3 = MAIN_CHARTS_DIR / "login_detail.png"
    _save_fig(fig, p3)
    out["main"].append(p3)
    log.info("chart(main): %s", p3.name)

    fig, ax = plt.subplots(figsize=(8, 4))
    all_ids = sorted(set(node_ok) | set(node_sel) | set(node_deny_by) | {nid for nid, _ in NODE_CATALOG})
    ok_vals = [node_ok.get(i, 0) for i in all_ids]
    bad_vals = [node_deny_by.get(i, 0) for i in all_ids]
    x = range(len(all_ids))
    w = 0.36
    ax.bar([xi - w / 2 for xi in x], ok_vals, width=w, label="доступ к узлу разрешён", color="#2ca02c")
    ax.bar([xi + w / 2 for xi in x], bad_vals, width=w, label="отказ (неверный/пустой пароль узла)", color="#d62728")
    ax.set_xticks(list(x))
    ax.set_xticklabels(list(all_ids))
    ax.set_title("Доступ к узлам: успехи и отказы по узлу")
    ax.set_ylabel("Событий")
    ax.legend(loc="upper right")
    fig.tight_layout()
    p5 = MAIN_CHARTS_DIR / "node_access_ok_vs_denied.png"
    _save_fig(fig, p5)
    out["main"].append(p5)
    log.info("chart(main): %s", p5.name)

    fig, ax = plt.subplots(figsize=(5, 4))
    ok_access = sum(node_ok.values())
    ax.bar(
        ["успешных входов", "успешных доступов к узлу"],
        [granted, ok_access],
        color=["#17becf", "#98df8a"],
    )
    ax.set_title("Успехи: вход в систему и доступ к узлу")
    ax.set_ylabel("Количество")
    p6 = MAIN_CHARTS_DIR / "success_summary.png"
    _save_fig(fig, p6)
    out["main"].append(p6)
    log.info("chart(main): %s", p6.name)
    return out


def format_tables(stats: dict) -> str:
    lines: list[str] = []
    granted = int(stats.get("granted", 0))
    denied = int(stats.get("denied", 0))
    lines.append("Сводка входа")
    lines.append("-" * 48)
    lines.append(f"{'успешно':20} {granted:>8}")
    lines.append(f"{'отказ':20} {denied:>8}")
    lines.append("")

    dr = dict(stats.get("deny_reasons", {}))
    lines.append("Причины отказа (вход)")
    lines.append("-" * 48)
    if not dr:
        lines.append("(нет)")
    else:
        for k, v in sorted(dr.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"{k:20} {int(v):>8}")
    lines.append("")

    ns = dict(stats.get("node_selections", {}))
    lines.append("Выбор сервера (узла)")
    lines.append("-" * 48)
    if not ns:
        lines.append("(нет)")
    else:
        for k, v in sorted(ns.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"{k:20} {int(v):>8}")
    lines.append("")

    ok = dict(stats.get("node_access_granted", {}))
    bad = dict(stats.get("node_access_denied_by_node", {}))
    all_ids = sorted(set(ok) | set(bad) | {nid for nid, _ in NODE_CATALOG})
    lines.append("Доступ к серверу (узлу)")
    lines.append("-" * 48)
    lines.append(f"{'узел':10} {'ok':>8} {'denied':>8}")
    for nid in all_ids:
        lines.append(f"{nid:10} {int(ok.get(nid, 0)):>8} {int(bad.get(nid, 0)):>8}")
    return "\n".join(lines)


def try_access(
    log: logging.Logger,
    login: str,
    password: str,
    key: str,
    stats: dict,
) -> bool:
    login = (login or "").strip()
    password = password or ""
    key = (key or "").strip()

    def deny(reason: str) -> None:
        log.warning("access_denied reason=%s user=%r", reason, login or "?")
        stats["denied"] = int(stats.get("denied", 0)) + 1
        _inc(stats, "deny_reasons", reason)

    if not login:
        deny("empty_login")
        return False
    if not password:
        deny("empty_password")
        return False
    if not key:
        deny("empty_key")
        return False
    if login != ISSUED_LOGIN:
        deny("wrong_login")
        return False
    if password != ISSUED_PASSWORD:
        deny("wrong_password")
        return False
    if key != ACCESS_KEY:
        deny("wrong_key")
        return False

    log.info("access_granted user=%s — сессия: можно выбирать узел", login)
    stats["granted"] = int(stats.get("granted", 0)) + 1
    return True


def record_node_selection(stats: dict, node_id: str) -> None:
    _inc(stats, "node_selections", node_id)


def try_node_access(log: logging.Logger, node_id: str, password: str, stats: dict) -> bool:
    node_id = (node_id or "").strip().lower()
    password = password or ""

    def deny(reason: str) -> None:
        log.warning("node_access_denied node=%s reason=%s", node_id or "?", reason)
        _inc(stats, "node_access_denied_reasons", reason)
        if node_id in known_node_ids() and reason in ("empty_node_password", "wrong_node_password"):
            _inc(stats, "node_access_denied_by_node", node_id)

    if node_id not in known_node_ids():
        deny("unknown_node")
        return False
    if not password:
        deny("empty_node_password")
        return False
    if password != node_password(node_id):
        deny("wrong_node_password")
        return False

    log.info("node_access_granted node=%s", node_id)
    _inc(stats, "node_access_granted", node_id)
    return True


def _node_session_cli(log: logging.Logger, stats: dict) -> None:
    while True:
        print("  Серверы:")
        for i, (nid, title) in enumerate(NODE_CATALOG, start=1):
            print(f"    {i}) [{nid}] {title}")
        print("    0) Назад")
        raw = input("  Выбор: ").strip()
        if raw == "0" or raw == "":
            print()
            return
        try:
            idx = int(raw)
        except ValueError:
            print("  Некорректный номер.\n")
            continue
        if not 1 <= idx <= len(NODE_CATALOG):
            print("  Номер вне диапазона.\n")
            continue
        nid, title = NODE_CATALOG[idx - 1]
        record_node_selection(stats, nid)
        npw = input(f"  Пароль сервера [{nid}]: ")
        if try_node_access(log, nid, npw, stats):
            print("  Доступ разрешён.\n")
        else:
            print("  Доступ запрещён.\n")


def interactive(log: logging.Logger) -> None:
    log_issued_credentials_safe(log)
    stats = new_stats()

    while True:
        cmd = input("Логин (Enter = выход): ").strip()
        if cmd.lower() == "chart":
            if stats["granted"] + stats["denied"] == 0:
                print("Пока нет попыток входа.\n")
                continue
            build_charts(log, stats)
            print("Готово.\n")
            continue
        if cmd.lower() == "table":
            print()
            print(format_tables(stats))
            print()
            continue

        login = cmd
        if not login:
            print("Выход. Лог:", LOG_PATH)
            break

        password = input("Пароль: ")
        key = input("Ключ доступа: ")

        if try_access(log, login, password, key, stats):
            _node_session_cli(log, stats)
        else:
            print("Вход запрещён\n")

    if stats["granted"] + stats["denied"] > 0:
        build_charts(log, stats)


def run_demo(log: logging.Logger) -> None:
    stats = new_stats()
    attempts = [
        ("hacker", "x", "x"),
        (ISSUED_LOGIN, "wrong", ACCESS_KEY),
        (ISSUED_LOGIN, ISSUED_PASSWORD, "bad-key"),
        ("", ISSUED_PASSWORD, ACCESS_KEY),
        (ISSUED_LOGIN, ISSUED_PASSWORD, ACCESS_KEY),
        (ISSUED_LOGIN, ISSUED_PASSWORD, ACCESS_KEY),
    ]
    log.info("=== демо: вход (логин + пароль + ключ) ===")
    for login, pw, k in attempts:
        if not login:
            log.info("демо: пропуск пустого логина")
            continue
        ok = try_access(log, login, pw, k, stats)
        if ok:
            # имитация выбора узла и пароля
            record_node_selection(stats, "alpha")
            try_node_access(log, "alpha", "wrong", stats)
            record_node_selection(stats, "beta")
            try_node_access(log, "beta", node_password("beta"), stats)
            record_node_selection(stats, "gamma")
            try_node_access(log, "gamma", node_password("gamma"), stats)

    log.info("=== демо: конец ===")
    build_charts(log, stats)
    print(format_tables(stats))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()

    log = init_logging()
    if args.demo:
        run_demo(log)
    else:
        interactive(log)


if __name__ == "__main__":
    main()
