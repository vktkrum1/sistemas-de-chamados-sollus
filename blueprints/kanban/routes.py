# blueprints/kanban/routes.py
from __future__ import annotations

from datetime import datetime, date
from time import sleep
from typing import Dict, List

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from . import kanban_bp
from extensions import db
from models import (
    User, Task, TaskLog, Subtask,
    SubtaskFlowNode, SubtaskFlowEdge
)
from utils.audit import write_audit

# ---------- helpers ----------
def _must_be_agent_like() -> bool:
    role = (getattr(current_user, "role", "") or "").lower()
    return current_user.is_authenticated and role in ("agent", "gestor", "admin")

def _user_list_for_assign() -> List[User]:
    return (
        User.query.filter(User.role.in_(("agent", "gestor", "admin")))
        .order_by(User.name.asc(), User.email.asc())
        .all()
    )

def _normalize_status(s: str) -> str:
    s = (s or "").strip().lower()
    return s if s in ("todo", "doing", "done") else "todo"

def _iso_date_or_none(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    try:
        return v.isoformat()
    except Exception:
        return None

def _add_log(task_id: int, text_: str):
    db.session.add(TaskLog(
        task_id=task_id,
        author_id=current_user.id,
        note=text_,
        log_date=date.today()
    ))

def _normalize_sub_status(s: str) -> str:
    s = (s or "").strip().lower()
    return s if s in ("open", "done") else "open"

# ---------- board (HTML) ----------
@kanban_bp.route("/", methods=["GET"], endpoint="board")
@login_required
def board():
    if not _must_be_agent_like():
        return render_template("errors/403.html"), 403
    agents = _user_list_for_assign()
    return render_template("kanban/board.html", agents=agents)

# ---------- API: listar tarefas ----------
@kanban_bp.route("/api/tasks", methods=["GET"], endpoint="api_list_tasks")
@login_required
def api_list_tasks():
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403

    rows = Task.query.order_by(Task.status.asc(), Task.position.asc(), Task.id.asc()).all()

    def dump(t: Task):
        return {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "position": t.position,
            "due_date": _iso_date_or_none(t.due_date),
            "assignee_id": t.assignee_id,
            "assignee_name": (t.assignee.name if t.assignee and t.assignee.name else (t.assignee.email if t.assignee else None)),
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    result: Dict[str, List[Dict]] = {"todo": [], "doing": [], "done": []}
    for r in rows:
        result[r.status].append(dump(r))
    return jsonify(result)

# ---------- API: criar tarefa ----------
@kanban_bp.route("/api/tasks", methods=["POST"], endpoint="api_create_task")
@login_required
def api_create_task():
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title é obrigatório"}), 400

    description = (data.get("description") or "").strip() or None
    status = _normalize_status(data.get("status") or "todo")

    due_date = data.get("due_date")
    if due_date:
        try:
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"error": "due_date inválido (use YYYY-MM-DD)"}), 400
    else:
        due_date = None

    assignee_id = data.get("assignee_id")
    try:
        assignee_id = int(assignee_id) if assignee_id else None
    except Exception:
        assignee_id = None

    last_pos = db.session.scalar(
        select(func.coalesce(func.max(Task.position), 0)).where(Task.status == status)
    ) or 0

    t = Task(
        title=title,
        description=description,
        status=status,
        position=last_pos + 1,
        due_date=due_date,
        assignee_id=assignee_id,
    )
    db.session.add(t)
    db.session.flush()
    _add_log(t.id, f"created in {status}")
    write_audit(entity_type="Task", entity_id=t.id, action="create",
                message=f"Task criada em {status}", after=t.as_dict())
    db.session.commit()

    return jsonify({"id": t.id}), 201

# ---------- API: atualizar tarefa ----------
@kanban_bp.route("/api/tasks/<int:task_id>", methods=["PUT"], endpoint="api_update_task")
@login_required
def api_update_task(task_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403

    t = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}

    before = t.as_dict()
    changed = []

    if "title" in data:
        new_title = (data["title"] or "").strip()
        if new_title and new_title != t.title:
            t.title = new_title
            changed.append("title")
    if "description" in data:
        new_desc = (data["description"] or "").strip() or None
        if new_desc != (t.description or None):
            t.description = new_desc
            changed.append("description")
    if "due_date" in data:
        v = data["due_date"]
        if v:
            try:
                new_dd = datetime.strptime(v, "%Y-%m-%d").date()
            except Exception:
                return jsonify({"error": "due_date inválido (use YYYY-MM-DD)"}), 400
        else:
            new_dd = None
        if new_dd != (t.due_date or None):
            t.due_date = new_dd
            changed.append("due_date")
    if "assignee_id" in data:
        v = data["assignee_id"]
        try:
            new_assignee = int(v) if v else None
        except Exception:
            new_assignee = None
        if new_assignee != (t.assignee_id or None):
            t.assignee_id = new_assignee
            changed.append("assignee")

    if changed:
        _add_log(t.id, f"updated: {', '.join(changed)}")
        write_audit(entity_type="Task", entity_id=t.id, action="update",
                    message=f"Campos: {', '.join(changed)}",
                    before=before, after=t.as_dict())

    db.session.commit()
    return jsonify({"ok": True})

# ---------- API: mover tarefa ----------
@kanban_bp.route("/api/tasks/<int:task_id>/move", methods=["PUT"], endpoint="api_move_task")
@login_required
def api_move_task(task_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}

    for attempt in (1, 2):
        try:
            with db.session.begin_nested():
                t: Task | None = (
                    db.session.query(Task)
                    .filter(Task.id == task_id)
                    .with_for_update()
                    .first()
                )
                if not t:
                    return jsonify({"error": "not_found"}), 404

                new_status = _normalize_status(payload.get("status", t.status))
                try:
                    new_position = int(payload.get("position", t.position))
                    if new_position < 1:
                        new_position = 1
                except Exception:
                    new_position = t.position

                old_status = t.status
                old_position = t.position

                if new_status == old_status and new_position == old_position:
                    return jsonify({"ok": True})

                if new_status != old_status:
                    db.session.execute(
                        text(
                            "UPDATE tasks SET position = position - 1 "
                            "WHERE status = :st AND position > :pos"
                        ),
                        {"st": old_status, "pos": old_position},
                    )
                    max_pos = db.session.scalar(
                        select(func.coalesce(func.max(Task.position), 0))
                        .where(Task.status == new_status)
                    ) or 0
                    if new_position > max_pos + 1:
                        new_position = max_pos + 1

                    db.session.execute(
                        text(
                            "UPDATE tasks SET position = position + 1 "
                            "WHERE status = :st AND position >= :pos"
                        ),
                        {"st": new_status, "pos": new_position},
                    )

                    t.status = new_status
                    t.position = new_position
                    _add_log(t.id, f"moved {old_status}#{old_position} -> {new_status}#{new_position}")
                    write_audit(entity_type="Task", entity_id=t.id, action="move",
                                message=f"{old_status}#{old_position} -> {new_status}#{new_position}",
                                before={"status": old_status, "position": old_position},
                                after={"status": t.status, "position": t.position})
                else:
                    if new_position > old_position:
                        db.session.execute(
                            text(
                                "UPDATE tasks SET position = position - 1 "
                                "WHERE status = :st AND position > :old AND position <= :new"
                            ),
                            {"st": new_status, "old": old_position, "new": new_position},
                        )
                    else:
                        db.session.execute(
                            text(
                                "UPDATE tasks SET position = position + 1 "
                                "WHERE status = :st AND position >= :new AND position < :old"
                            ),
                            {"st": new_status, "old": old_position, "new": new_position},
                        )
                    t.position = new_position
                    _add_log(t.id, f"reordered {new_status} -> #{new_position}")
                    write_audit(entity_type="Task", entity_id=t.id, action="move",
                                message=f"reordered {new_status} -> #{new_position}",
                                before={"position": old_position},
                                after={"position": t.position})

            db.session.commit()
            return jsonify({"ok": True})

        except OperationalError as e:
            if "1020" in str(e.orig) and attempt == 1:
                db.session.rollback()
                sleep(0.05)
                continue
            db.session.rollback()
            return jsonify({"ok": False, "error": "conflict", "detail": "record_changed"}), 409
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "server_error"}), 500

# ---------- API: deletar tarefa ----------
@kanban_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"], endpoint="api_delete_task")
@login_required
def api_delete_task(task_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403

    t = Task.query.get_or_404(task_id)
    st, pos = t.status, t.position

    _add_log(task_id, "deleted")
    db.session.flush()

    db.session.delete(t)
    db.session.flush()

    db.session.execute(
        text(
            "UPDATE tasks SET position = position - 1 "
            "WHERE status = :st AND position > :pos"
        ),
        {"st": st, "pos": pos},
    )

    write_audit(entity_type="Task", entity_id=task_id, action="delete",
                message=f"Task removida de {st}#{pos}",
                before={"status": st, "position": pos}, after=None)

    db.session.commit()
    return jsonify({"ok": True})

# =========================
# SubTarefas
# =========================
@kanban_bp.route("/api/tasks/<int:task_id>/subtasks", methods=["GET"], endpoint="api_list_subtasks")
@login_required
def api_list_subtasks(task_id: int):
    if not _must_be_agent_like():
        return jsonify({"error":"forbidden"}), 403
    Task.query.get_or_404(task_id)
    rows = (Subtask.query
            .filter(Subtask.task_id == task_id)
            .order_by(Subtask.position.asc(), Subtask.id.asc())
            .all())
    return jsonify([r.as_dict() for r in rows])

@kanban_bp.route("/api/tasks/<int:task_id>/subtasks", methods=["POST"], endpoint="api_create_subtask")
@login_required
def api_create_subtask(task_id: int):
    if not _must_be_agent_like():
        return jsonify({"error":"forbidden"}), 403
    Task.query.get_or_404(task_id)

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error":"title é obrigatório"}), 400

    last_pos = db.session.scalar(
        select(func.coalesce(func.max(Subtask.position), 0)).where(Subtask.task_id == task_id)
    ) or 0

    work_date = data.get("work_date")
    if work_date:
        try:
            work_date = datetime.strptime(work_date, "%Y-%m-%d").date()
        except Exception:
            return jsonify({"error":"work_date inválido (use YYYY-MM-DD)"}), 400
    else:
        work_date = None

    assignee_id = data.get("assignee_id")
    try:
        assignee_id = int(assignee_id) if assignee_id else None
    except Exception:
        assignee_id = None

    s = Subtask(
        task_id=task_id,
        title=title,
        description=(data.get("description") or "").strip() or None,
        work_date=work_date,
        status=_normalize_sub_status(data.get("status")),
        position=last_pos + 1,
        assignee_id=assignee_id,
    )
    db.session.add(s)
    db.session.commit()

    write_audit(entity_type="Subtask", entity_id=s.id, action="create",
                message=f"Subtask criada para task #{task_id}", after=s.as_dict())

    return jsonify(s.as_dict()), 201

@kanban_bp.route("/api/subtasks/<int:subtask_id>", methods=["PUT"], endpoint="api_update_subtask")
@login_required
def api_update_subtask(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error":"forbidden"}), 403
    s = Subtask.query.get_or_404(subtask_id)
    data = request.get_json(silent=True) or {}
    before = s.as_dict()
    changed = []

    if "title" in data:
        new_t = (data["title"] or "").strip()
        if new_t and new_t != s.title:
            s.title = new_t; changed.append("title")
    if "description" in data:
        new_d = (data["description"] or "").strip() or None
        if new_d != (s.description or None):
            s.description = new_d; changed.append("description")
    if "status" in data:
        new_st = _normalize_sub_status(data["status"])
        if new_st != s.status:
            s.status = new_st; changed.append("status")
    if "work_date" in data:
        wd = data["work_date"]
        if wd:
            try:
                new_wd = datetime.strptime(wd, "%Y-%m-%d").date()
            except Exception:
                return jsonify({"error":"work_date inválido (use YYYY-MM-DD)"}), 400
        else:
            new_wd = None
        if (s.work_date or None) != new_wd:
            s.work_date = new_wd; changed.append("work_date")
    if "assignee_id" in data:
        v = data["assignee_id"]
        try:
            new_assignee = int(v) if v else None
        except Exception:
            new_assignee = None
        if new_assignee != (s.assignee_id or None):
            s.assignee_id = new_assignee; changed.append("assignee")

    if "position" in data:
        try:
            new_pos = int(data["position"])
            if new_pos < 1: new_pos = 1
        except Exception:
            new_pos = s.position
        if new_pos != s.position:
            task_id = s.task_id
            old_pos = s.position
            if new_pos > old_pos:
                db.session.execute(
                    text(
                        "UPDATE subtasks SET position = position - 1 "
                        "WHERE task_id = :tid AND position > :old AND position <= :new"
                    ),
                    {"tid": task_id, "old": old_pos, "new": new_pos},
                )
            else:
                db.session.execute(
                    text(
                        "UPDATE subtasks SET position = position + 1 "
                        "WHERE task_id = :tid AND position >= :new AND position < :old"
                    ),
                    {"tid": task_id, "old": old_pos, "new": new_pos},
                )
            s.position = new_pos
            changed.append("position")

    if changed:
        write_audit(entity_type="Subtask", entity_id=s.id, action="update",
                    message=f"Campos: {', '.join(changed)}",
                    before=before, after=s.as_dict())

    db.session.commit()
    return jsonify({"ok": True, "changed": changed})

@kanban_bp.route("/api/subtasks/<int:subtask_id>", methods=["DELETE"], endpoint="api_delete_subtask")
@login_required
def api_delete_subtask(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error":"forbidden"}), 403
    s = Subtask.query.get_or_404(subtask_id)
    tid, pos = s.task_id, s.position
    write_audit(entity_type="Subtask", entity_id=subtask_id, action="delete",
                message=f"Subtask removida (task #{tid}, pos {pos})",
                before={"task_id": tid, "position": pos}, after=None)
    db.session.delete(s)
    db.session.flush()
    db.session.execute(
        text(
            "UPDATE subtasks SET position = position - 1 "
            "WHERE task_id = :tid AND position > :pos"
        ),
        {"tid": tid, "pos": pos},
    )
    db.session.commit()
    return jsonify({"ok": True})

# =========================
# FLOW: NODES
# =========================
@kanban_bp.route("/api/subtasks/<int:subtask_id>/flow/nodes", methods=["GET"], endpoint="api_flow_nodes_list")
@login_required
def api_flow_nodes_list(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    Subtask.query.get_or_404(subtask_id)
    rows = (SubtaskFlowNode.query
            .filter(SubtaskFlowNode.subtask_id == subtask_id)
            .order_by(SubtaskFlowNode.id.asc())
            .all())
    return jsonify([r.as_dict() for r in rows])

@kanban_bp.route("/api/subtasks/<int:subtask_id>/flow/nodes", methods=["POST"], endpoint="api_flow_nodes_create")
@login_required
def api_flow_nodes_create(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    Subtask.query.get_or_404(subtask_id)
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title é obrigatório"}), 400
    shape = (data.get("shape") or "rect").lower()
    if shape not in ("rect", "diamond", "pill"):
        shape = "rect"
    color = (data.get("color") or "#e5e7eb").strip()[:16]
    try:
        x = int(data.get("x", 40)); y = int(data.get("y", 40))
    except Exception:
        x, y = 40, 40
    node = SubtaskFlowNode(subtask_id=subtask_id, title=title, shape=shape, color=color, x=x, y=y, body=(data.get("body") or None))
    db.session.add(node)
    db.session.commit()

    write_audit(entity_type="FlowNode", entity_id=node.id, action="create",
                message=f"Nó criado na subtarefa #{subtask_id}", after=node.as_dict())

    return jsonify(node.as_dict()), 201

@kanban_bp.route("/api/flow/nodes/<int:node_id>", methods=["PUT"], endpoint="api_flow_nodes_update")
@login_required
def api_flow_nodes_update(node_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    node = SubtaskFlowNode.query.get_or_404(node_id)
    data = request.get_json(silent=True) or {}
    before = node.as_dict()
    changed = []
    if "title" in data:
        t = (data["title"] or "").strip()
        if t and t != node.title:
            node.title = t; changed.append("title")
    if "shape" in data:
        shp = (data["shape"] or "rect").lower()
        if shp in ("rect","diamond","pill") and shp != node.shape:
            node.shape = shp; changed.append("shape")
    if "color" in data:
        col = (data["color"] or "#e5e7eb").strip()[:16]
        if col and col != node.color:
            node.color = col; changed.append("color")
    if "body" in data:
        b = (data["body"] or None)
        if b != (node.body or None):
            node.body = b; changed.append("body")
    if "x" in data or "y" in data:
        try:
            nx = int(data.get("x", node.x)); ny = int(data.get("y", node.y))
            if nx != node.x or ny != node.y:
                node.x, node.y = nx, ny; changed.append("pos")
        except Exception:
            pass
    if changed:
        db.session.commit()
        write_audit(entity_type="FlowNode", entity_id=node.id, action="update",
                    message=f"Campos: {', '.join(changed)}",
                    before=before, after=node.as_dict())
    return jsonify({"ok": True, "changed": changed})

@kanban_bp.route("/api/flow/nodes/<int:node_id>", methods=["DELETE"], endpoint="api_flow_nodes_delete")
@login_required
def api_flow_nodes_delete(node_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    node = SubtaskFlowNode.query.get_or_404(node_id)
    sub_id = node.subtask_id
    write_audit(entity_type="FlowNode", entity_id=node_id, action="delete",
                message=f"Nó removido da subtarefa #{sub_id}",
                before=node.as_dict(), after=None)
    SubtaskFlowEdge.query.filter(
        SubtaskFlowEdge.subtask_id == sub_id,
        ((SubtaskFlowEdge.from_id == node_id) | (SubtaskFlowEdge.to_id == node_id))
    ).delete(synchronize_session=False)
    db.session.delete(node)
    db.session.commit()
    return jsonify({"ok": True})

# =========================
# FLOW: EDGES
# =========================
@kanban_bp.route("/api/subtasks/<int:subtask_id>/flow/edges", methods=["GET"], endpoint="api_flow_edges_list")
@login_required
def api_flow_edges_list(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    Subtask.query.get_or_404(subtask_id)
    rows = (SubtaskFlowEdge.query
            .filter(SubtaskFlowEdge.subtask_id == subtask_id)
            .order_by(SubtaskFlowEdge.id.asc())
            .all())
    return jsonify([r.as_dict() for r in rows])

@kanban_bp.route("/api/subtasks/<int:subtask_id>/flow/edges", methods=["POST"], endpoint="api_flow_edges_create")
@login_required
def api_flow_edges_create(subtask_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    Subtask.query.get_or_404(subtask_id)
    data = request.get_json(silent=True) or {}
    try:
        from_id = int(data.get("from_id")); to_id = int(data.get("to_id"))
    except Exception:
        return jsonify({"error": "from_id/to_id inválidos"}), 400
    if from_id == to_id:
        return jsonify({"error": "from_id e to_id não podem ser iguais"}), 400
    f = SubtaskFlowNode.query.get_or_404(from_id)
    t = SubtaskFlowNode.query.get_or_404(to_id)
    if f.subtask_id != subtask_id or t.subtask_id != subtask_id:
        return jsonify({"error": "nós não pertencem a esta subtarefa"}), 400
    label = (data.get("label") or "").strip() or None

    exists = SubtaskFlowEdge.query.filter_by(subtask_id=subtask_id, from_id=from_id, to_id=to_id).first()
    if exists:
        if label != exists.label:
            before = exists.as_dict()
            exists.label = label
            db.session.commit()
            write_audit(entity_type="FlowEdge", entity_id=exists.id, action="update",
                        message=f"Aresta {from_id}->{to_id} label alterada",
                        before=before, after=exists.as_dict())
        return jsonify(exists.as_dict()), 200

    e = SubtaskFlowEdge(subtask_id=subtask_id, from_id=from_id, to_id=to_id, label=label)
    db.session.add(e)
    db.session.commit()
    write_audit(entity_type="FlowEdge", entity_id=e.id, action="link",
                message=f"Ligado {from_id} -> {to_id} (sub #{subtask_id})",
                after=e.as_dict())
    return jsonify(e.as_dict()), 201

@kanban_bp.route("/api/flow/edges/<int:edge_id>", methods=["DELETE"], endpoint="api_flow_edges_delete")
@login_required
def api_flow_edges_delete(edge_id: int):
    if not _must_be_agent_like():
        return jsonify({"error": "forbidden"}), 403
    e = SubtaskFlowEdge.query.get_or_404(edge_id)
    before = e.as_dict()
    db.session.delete(e)
    db.session.commit()
    write_audit(entity_type="FlowEdge", entity_id=edge_id, action="unlink",
                message=f"Aresta removida {before['from_id']}->{before['to_id']} (sub #{before['subtask_id']})",
                before=before, after=None)
    return jsonify({"ok": True})
