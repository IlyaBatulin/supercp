#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask фронт для Replit/браузера: вход → выбор сервера (узла) → модальное окно пароля узла.

Запуск локально:
  pip install -r requirements.txt
  python web_app.py

Переменные (берутся из .env через python-dotenv, если файл есть):
  LAB_LOGIN, LAB_PASSWORD, SUPERCOMPUTER_ACCESS_KEY
  NODE_PASSWORD_ALPHA / BETA / GAMMA
  FLASK_SECRET_KEY (для cookie-сессии)
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

import main as lab

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

    @app.get("/")
    def index():
        if session.get("logged_in"):
            return redirect(url_for("nodes"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            login_ = request.form.get("login", "")
            password = request.form.get("password", "")
            key = request.form.get("key", "")

            stats = session.setdefault("stats", lab.new_stats())
            ok = lab.try_access(app.logger, login_, password, key, stats)
            session["stats"] = stats

            if ok:
                session["logged_in"] = True
                flash("Вход успешен. Выберите узел.", "success")
                return redirect(url_for("nodes"))

            flash("Вход запрещён. Проверьте данные.", "danger")
            return redirect(url_for("login"))

        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.pop("logged_in", None)
        flash("Вы вышли из сессии.", "info")
        return redirect(url_for("login"))

    def require_login():
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return None

    @app.get("/nodes")
    def nodes():
        redir = require_login()
        if redir:
            return redir
        return render_template("nodes.html", nodes=lab.NODE_CATALOG)

    @app.post("/nodes/access")
    def nodes_access():
        redir = require_login()
        if redir:
            return redir

        node_id = (request.form.get("node_id") or "").strip().lower()
        node_pw = request.form.get("node_password") or ""

        stats = session.setdefault("stats", lab.new_stats())
        lab.record_node_selection(stats, node_id)
        ok = lab.try_node_access(app.logger, node_id, node_pw, stats)
        session["stats"] = stats
        # тихо строим 3 ключевые диаграммы (страницы для них нет)
        if stats.get("granted", 0) + stats.get("denied", 0) > 0:
            lab.build_charts(app.logger, stats)

        if ok:
            flash(f"Успешно: доступ к серверу «{node_id}» разрешён.", "success")
        else:
            flash(f"Ошибка: доступ к серверу «{node_id}» запрещён.", "danger")
        return redirect(url_for("nodes"))

    return app


app = create_app()

if __name__ == "__main__":
    # Replit обычно пробрасывает PORT; локально будет 5000
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

