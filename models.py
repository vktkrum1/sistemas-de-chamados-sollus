# models.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from flask_login import UserMixin
from flask import current_app
from extensions import db

# =========================
# USER
# =========================
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), default="user")  # user|agent|gestor|admin
    is_active     = db.Column(db.Boolean, nullable=False, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    tickets = db.relationship(
        "Ticket",
        back_populates="user",
        foreign_keys="Ticket.user_id",
        lazy="dynamic",
    )
    assigned_tickets = db.relationship(
        "Ticket",
        back_populates="assignee",
        foreign_keys="Ticket.assignee_id",
        lazy="dynamic",
    )
    messages = db.relationship(
        "TicketMessage",
        back_populates="author",
        foreign_keys="TicketMessage.author_id",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

# =========================
# TICKET
# =========================
class Ticket(db.Model):
    __tablename__ = "tickets"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    priority    = db.Column(db.String(20), default="medium")  # low|medium|high|urgent
    status      = db.Column(db.String(20), default="open")    # open|in_progress|closed

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user        = db.relationship("User", back_populates="tickets", foreign_keys=[user_id])

    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignee    = db.relationship("User", back_populates="assigned_tickets", foreign_keys=[assignee_id])

    attachments = db.relationship(
        "Attachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Attachment.uploaded_at.desc()",
        lazy="dynamic",
    )
    messages = db.relationship(
        "TicketMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketMessage.created_at.asc()",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.id} '{self.title}'>"

# =========================
# KANBAN TASKS
# =========================
class Task(db.Model):
    __tablename__ = "tasks"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status      = db.Column(db.String(20), nullable=False, default="todo")  # todo|doing|done
    position    = db.Column("position", db.Integer, nullable=False, default=0)
    due_date    = db.Column(db.Date)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = db.relationship("User", backref=db.backref("tasks", lazy="dynamic"))
    logs     = db.relationship("TaskLog", backref="task", cascade="all, delete-orphan", lazy="dynamic")

    def as_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "position": self.position,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assignee_id": self.assignee_id,
            "assignee_name": (self.assignee.name if self.assignee and self.assignee.name else (self.assignee.email if self.assignee else None)),
        }

class TaskLog(db.Model):
    __tablename__ = "task_logs"
    id         = db.Column(db.Integer, primary_key=True)
    task_id    = db.Column(db.Integer, db.ForeignKey("tasks.id"), index=True, nullable=False)
    log_date   = db.Column(db.Date, nullable=False)
    note       = db.Column(db.Text, nullable=False)
    author_id  = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

# =========================
# SUBTASKS
# =========================
class Subtask(db.Model):
    __tablename__ = "subtasks"

    id          = db.Column(db.Integer, primary_key=True)
    task_id     = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    work_date   = db.Column(db.Date, nullable=True)  # data de trabalho (não é due)
    status      = db.Column(db.String(20), nullable=False, default="open")  # open|done
    position    = db.Column(db.Integer, nullable=False, default=0)

    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee    = db.relationship("User", lazy="joined")

    def as_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "work_date": self.work_date.isoformat() if self.work_date else None,
            "status": self.status,
            "position": self.position,
            "assignee_id": self.assignee_id,
            "assignee_name": (self.assignee.name if self.assignee and self.assignee.name else (self.assignee.email if self.assignee else None)),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

# =========================
# FLOW POR SUBTAREFA (NÓS / ARESTAS)
# =========================
class SubtaskFlowNode(db.Model):
    __tablename__ = "subtask_flow_nodes"

    id         = db.Column(db.Integer, primary_key=True)
    subtask_id = db.Column(db.Integer, db.ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    body  = db.Column(db.Text, nullable=True)  # descrição do bloco
    shape = db.Column(db.String(20), nullable=False, default="rect")  # rect|diamond|pill
    color = db.Column(db.String(16), nullable=False, default="#e5e7eb")

    x = db.Column(db.Integer, nullable=False, default=40)
    y = db.Column(db.Integer, nullable=False, default=40)
    w = db.Column(db.Integer, nullable=False, default=180)
    h = db.Column(db.Integer, nullable=False, default=60)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subtask = db.relationship("Subtask", backref=db.backref("flow_nodes", cascade="all, delete-orphan"))

    __table_args__ = (db.Index("ix_sfn_subtask_id", "subtask_id"),)

    def as_dict(self):
        return dict(
            id=self.id, subtask_id=self.subtask_id, title=self.title, body=(self.body or None),
            shape=self.shape, color=self.color, x=self.x, y=self.y, w=self.w, h=self.h,
            created_at=self.created_at.isoformat() if self.created_at else None
        )

class SubtaskFlowEdge(db.Model):
    __tablename__ = "subtask_flow_edges"
    id         = db.Column(db.Integer, primary_key=True)
    subtask_id = db.Column(db.Integer, db.ForeignKey("subtasks.id", ondelete="CASCADE"), nullable=False, index=True)
    from_id    = db.Column(db.Integer, db.ForeignKey("subtask_flow_nodes.id", ondelete="CASCADE"), nullable=False)
    to_id      = db.Column(db.Integer, db.ForeignKey("subtask_flow_nodes.id", ondelete="CASCADE"), nullable=False)
    label      = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    subtask   = db.relationship("Subtask", backref=db.backref("flow_edges", cascade="all, delete-orphan"))
    from_node = db.relationship("SubtaskFlowNode", foreign_keys=[from_id])
    to_node   = db.relationship("SubtaskFlowNode", foreign_keys=[to_id])

    __table_args__ = (
        db.UniqueConstraint("subtask_id", "from_id", "to_id", name="uq_sfe_sub_from_to"),
        db.Index("ix_sfe_subtask_id", "subtask_id"),
    )

    def as_dict(self):
        return dict(id=self.id, subtask_id=self.subtask_id, from_id=self.from_id, to_id=self.to_id, label=self.label or None)

# =========================
# TICKET MESSAGE
# =========================
class TicketMessage(db.Model):
    __tablename__ = "ticket_messages"

    id         = db.Column(db.Integer, primary_key=True)
    ticket_id  = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    author_id  = db.Column(db.Integer, db.ForeignKey("users.id",   ondelete="RESTRICT"), nullable=False)
    body       = db.Column(db.Text, nullable=False)
    public     = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    ticket = db.relationship("Ticket", back_populates="messages", foreign_keys=[ticket_id])
    author = db.relationship("User", back_populates="messages", foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<TicketMessage {self.id} ticket={self.ticket_id}>"

# =========================
# ATTACHMENT
# =========================
class Attachment(db.Model):
    __tablename__ = "attachments"

    id           = db.Column(db.Integer, primary_key=True)
    ticket_id    = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)

    original_name = db.Column(db.String(255))
    filename      = db.Column(db.String(255), nullable=False)
    stored_name   = db.Column(db.String(255), nullable=False)

    content_type = db.Column(db.String(120))
    size         = db.Column(db.Integer)
    uploaded_at  = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by  = db.Column("uploader_id", db.Integer, db.ForeignKey("users.id"), nullable=True)

    ticket = db.relationship("Ticket", back_populates="attachments", foreign_keys=[ticket_id])

    def __repr__(self) -> str:
        return f"<Attachment {self.id} ticket={self.ticket_id} {self.filename}>"

    @property
    def filepath(self) -> str:
        base_dir = current_app.config.get("UPLOADS_DIR", "uploads")
        return str(Path(base_dir) / "tickets" / str(self.ticket_id) / self.stored_name)

# =========================
# AUDIT LOG
# =========================
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    actor_id    = db.Column(db.Integer, nullable=True, index=True)
    actor_email = db.Column(db.String(255), nullable=True)
    actor_name  = db.Column(db.String(255), nullable=True)

    ip = db.Column(db.String(64), nullable=True)
    ua = db.Column(db.String(255), nullable=True)

    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id   = db.Column(db.Integer, nullable=True, index=True)
    action      = db.Column(db.String(40), nullable=False, index=True)

    message = db.Column(db.Text, nullable=True)

    before = db.Column(db.Text, nullable=True)  # JSON como texto
    after  = db.Column(db.Text, nullable=True)  # JSON como texto


    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.entity_type}#{self.entity_id} {self.action}>"
