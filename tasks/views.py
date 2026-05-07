from __future__ import annotations

import logging
import os
from typing import Any

from django import get_version
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

import main as lab

LOG = logging.getLogger("lab.django.tasks")


def _plain_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "granted": int(stats.get("granted", 0)),
        "denied": int(stats.get("denied", 0)),
        "deny_reasons": dict(stats.get("deny_reasons", {})),
        "node_selections": dict(stats.get("node_selections", {})),
        "node_access_granted": dict(stats.get("node_access_granted", {})),
        "node_access_denied_by_node": dict(stats.get("node_access_denied_by_node", {})),
        "node_access_denied_reasons": dict(stats.get("node_access_denied_reasons", {})),
    }


def _session_stats(request: HttpRequest) -> dict[str, Any]:
    raw_stats = request.session.get("stats")
    if isinstance(raw_stats, dict):
        return _plain_stats(raw_stats)
    return _plain_stats(lab.new_stats())


def index(request: HttpRequest) -> HttpResponse:
    stats = _session_stats(request)
    message = ""
    message_type = "info"

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "login":
            ok = lab.try_access(
                LOG,
                request.POST.get("login", ""),
                request.POST.get("password", ""),
                request.POST.get("key", ""),
                stats,
            )
            request.session["logged_in"] = ok
            if ok:
                message = "Вход выполнен. Можно переходить к задачам и узлам."
                message_type = "success"
            else:
                message = "Вход запрещён. Проверьте логин, пароль и ключ."
                message_type = "danger"
        elif action == "node":
            if not request.session.get("logged_in"):
                message = "Сначала выполните вход."
                message_type = "warning"
            else:
                node_id = (request.POST.get("node_id") or "").strip().lower()
                lab.record_node_selection(stats, node_id)
                ok = lab.try_node_access(LOG, node_id, request.POST.get("node_password", ""), stats)
                if ok:
                    message = f"Доступ к узлу {node_id} разрешён."
                    message_type = "success"
                else:
                    message = f"Доступ к узлу {node_id or '?'} запрещён."
                    message_type = "danger"
        elif action == "logout":
            request.session["logged_in"] = False
            message = "Сессия завершена."
            message_type = "info"

        request.session["stats"] = _plain_stats(stats)
        request.session.modified = True

    context = {
        "student_fio": os.environ.get("STUDENT_FIO", "Батулин И.И."),
        "logged_in": bool(request.session.get("logged_in")),
        "message": message,
        "message_type": message_type,
        "nodes": lab.NODE_CATALOG,
        "stats_table": lab.format_tables(_plain_stats(stats)),
        "django_version": get_version(),
        "today_tasks": [
            "Подготовить Replit-окружение и переменные.",
            "Выполнить вход по логину, паролю и ключу.",
            "Подключить узел alpha и проверить доступ.",
            "Подключить узел beta и проверить доступ.",
            "Подключить узел gamma и проверить доступ.",
            "Проверить статистику и собрать скриншоты.",
            "Подготовить и отправить отчёт по ЛР4.",
        ],
        "description_vars": [
            "LAB_LOGIN",
            "LAB_PASSWORD",
            "SUPERCOMPUTER_ACCESS_KEY",
            "NODE_PASSWORD_ALPHA",
            "NODE_PASSWORD_BETA",
            "NODE_PASSWORD_GAMMA",
            "STUDENT_FIO",
            "DJANGO_SECRET_KEY",
            "DJANGO_ALLOWED_HOSTS",
            "DJANGO_CSRF_TRUSTED_ORIGINS",
            "PORT",
        ],
    }
    return render(request, "tasks/index.html", context)
