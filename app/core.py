"""
Loyiha uchun umumiy obyektlar — template, keyinchalik config.
"""
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
