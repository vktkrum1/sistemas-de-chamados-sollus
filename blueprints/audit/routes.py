from __future__ import annotations
from flask import render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import desc
from models import AuditLog
from . import audit_bp

def _parse_int(v, default):
    try:
        v = int(v)
        return v if v > 0 else default
    except Exception:
        return default

@audit_bp.route("/", methods=["GET"])
@login_required
def page():
    q_entity = (request.args.get("entity_type") or "").strip()
    q_action = (request.args.get("action") or "").strip()
    q_actor  = (request.args.get("actor") or "").strip()
    q_text   = (request.args.get("q") or "").strip()

    page_num = _parse_int(request.args.get("page", 1), 1)
    per_page = min(100, _parse_int(request.args.get("per_page", 25), 25))

    qry = AuditLog.query
    if q_entity:
        qry = qry.filter(AuditLog.entity_type == q_entity)
    if q_action:
        qry = qry.filter(AuditLog.action == q_action)
    if q_actor:
        like = f"%{q_actor}%"
        qry = qry.filter(
            (AuditLog.actor_email.ilike(like)) |
            (AuditLog.actor_name.ilike(like)) |
            (AuditLog.actor_id == q_actor)
        )
    if q_text:
        like = f"%{q_text}%"
        qry = qry.filter(AuditLog.message.ilike(like))

    qry = qry.order_by(desc(AuditLog.created_at))
    pagination = qry.paginate(page=page_num, per_page=per_page, error_out=False)

    return render_template(
        "audit/index.html",
        rows=pagination.items,
        pagination=pagination,
        filters=dict(entity_type=q_entity, action=q_action, actor=q_actor, q=q_text, per_page=per_page),
    )

@audit_bp.route("/api", methods=["GET"])
@login_required
def api_list():
    q_entity = (request.args.get("entity_type") or "").strip()
    q_action = (request.args.get("action") or "").strip()
    limit = _parse_int(request.args.get("limit", 50), 50)
    limit = min(200, max(1, limit))

    qry = AuditLog.query
    if q_entity:
        qry = qry.filter(AuditLog.entity_type == q_entity)
    if q_action:
        qry = qry.filter(AuditLog.action == q_action)
    qry = qry.order_by(desc(AuditLog.created_at)).limit(limit)

    def dump(r: AuditLog):
        return dict(
            id=r.id,
            created_at=r.created_at.isoformat() if r.created_at else None,
            actor=dict(id=r.actor_id, email=r.actor_email, name=r.actor_name),
            ip=r.ip, ua=r.ua,
            entity_type=r.entity_type, entity_id=r.entity_id,
            action=r.action,
            message=r.message,
            before=r.before, after=r.after,
        )

    return jsonify([dump(r) for r in qry.all()])
