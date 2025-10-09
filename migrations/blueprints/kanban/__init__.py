# blueprints/kanban/__init__.py
from flask import Blueprint

kanban_bp = Blueprint(
    "kanban",
    __name__,
    url_prefix="/kanban",
    template_folder="../../templates/kanban",
    static_folder="../../static",
)

from . import routes  # noqa: E402,F401
