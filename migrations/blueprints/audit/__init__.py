from __future__ import annotations
from flask import Blueprint

audit_bp = Blueprint("audit", __name__, url_prefix="/audit", template_folder="templates")

from . import routes  # noqa: E402,F401
