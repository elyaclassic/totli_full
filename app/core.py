"""
Loyiha uchun umumiy obyektlar — template, keyinchalik config.
"""
import json
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["getattr"] = getattr


def _csrf_token_from_request(request):
    """Jinja uchun: request.state dan csrf_token olish (getattr ishlatilmasin)."""
    if request is None:
        return ""
    return getattr(request.state, "csrf_token", "") or ""


templates.env.globals["csrf_token_from_request"] = _csrf_token_from_request


def _tojson(val):
    """Jinja filtri: obyektni JSON qatoriga aylantirish (transfer_form, movement va b.)."""
    return json.dumps(val)


templates.env.filters["tojson"] = _tojson
