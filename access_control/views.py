from __future__ import annotations

import logging
from typing import Any

from django import get_version
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

import main as lab

LOG = logging.getLogger("lab.django")


def _plain_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Convert defaultdict buckets from CLI logic into JSON-session-safe dicts."""
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
                message = "Вход успешен. Теперь можно выбрать серверный узел."
                message_type = "success"
            else:
                message = "Вход запрещен. Проверьте логин, пароль и ключ доступа."
                message_type = "danger"

        elif action == "node":
            if not request.session.get("logged_in"):
                message = "Сначала выполните успешный вход в систему."
                message_type = "warning"
            else:
                node_id = (request.POST.get("node_id") or "").strip().lower()
                lab.record_node_selection(stats, node_id)
                ok = lab.try_node_access(LOG, node_id, request.POST.get("node_password", ""), stats)
                if ok:
                    message = f"Доступ к узлу {node_id} разрешен."
                    message_type = "success"
                else:
                    message = f"Доступ к узлу {node_id or '?'} запрещен."
                    message_type = "danger"

        elif action == "reset":
            stats = _plain_stats(lab.new_stats())
            request.session["logged_in"] = False
            message = "Статистика и состояние входа сброшены."
            message_type = "info"

        elif action == "logout":
            request.session["logged_in"] = False
            message = "Вы вышли из личного кабинета."
            message_type = "info"

        request.session["stats"] = _plain_stats(stats)
        request.session.modified = True

    context = {
        "nodes": lab.NODE_CATALOG,
        "logged_in": bool(request.session.get("logged_in")),
        "message": message,
        "message_type": message_type,
        "django_version": get_version(),
        "stats_table": lab.format_tables(_plain_stats(stats)),
        "env_vars": [
            "LAB_LOGIN",
            "LAB_PASSWORD",
            "SUPERCOMPUTER_ACCESS_KEY",
            "NODE_PASSWORD_ALPHA",
            "NODE_PASSWORD_BETA",
            "NODE_PASSWORD_GAMMA",
            "DJANGO_SECRET_KEY",
            "DJANGO_ALLOWED_HOSTS",
        ],
    }
    return render(request, "access_control/index.html", context)
