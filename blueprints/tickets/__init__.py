# blueprints/tickets/__init__.py
from flask import Blueprint

tickets_bp = Blueprint("tickets", __name__, url_prefix="/tickets")

# Importa TANTO as views (dashboard/relatórios/listas) quanto as rotas de tickets.
# A ordem importa pouco, mas manter assim evita import circular.
from . import views  # noqa: F401,E402
from . import routes  # noqa: F401,E402
