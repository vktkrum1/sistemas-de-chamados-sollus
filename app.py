# app.py
from __future__ import annotations

from flask import Flask, redirect, url_for, send_from_directory, current_app
from pathlib import Path
from config import get_config
from extensions import db, migrate, login_manager, csrf
from flask_wtf.csrf import generate_csrf, CSRFError


# Blueprints
from blueprints.auth import auth_bp
from blueprints.tickets import tickets_bp
from blueprints.admin import admin_bp
from blueprints.kanban import kanban_bp  # <<<
from blueprints.audit import audit_bp


# (opcional) tentar importar mail
try:
    from extensions import mail
except Exception:
    mail = None

def _ensure_dirs(app: Flask) -> None:
    base = Path(app.config.get("UPLOADS_DIR", "uploads"))
    (base / "tickets").mkdir(parents=True, exist_ok=True)

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config())

    # extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    if mail is not None:
        try:
            mail.init_app(app)
        except Exception:
            pass

    with app.app_context():
        _ensure_dirs(app)

    # login
    from models import User
    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": generate_csrf}

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return f"Falha de CSRF: {e.description}", 400

    # blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(kanban_bp)   # <<<
    app.register_blueprint(audit_bp)


    # rotas básicas
    from flask_login import current_user

    @app.route("/", endpoint="index")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("tickets.dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/uploads/<path:filename>", endpoint="uploads")
    def uploads(filename: str):
        base = Path(current_app.config.get("UPLOADS_DIR", "uploads"))
        return send_from_directory(base, filename, as_attachment=False)

    return app

app = create_app()
