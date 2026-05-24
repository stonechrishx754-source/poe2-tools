"""Jinja2 environment setup with translation support."""

import jinja2
from fastapi.templating import Jinja2Templates

from app.translations import translate
from app.translations_item import translate_item


def create_templates(directory: str = "app/templates") -> Jinja2Templates:
    """Create Jinja2Templates with translation function and category names built-in."""

    CATEGORY_NAMES = {
        "armour": "Armour", "weapon": "Weapon", "weapons": "Weapon",
        "accessory": "Accessory", "jewel": "Jewel", "jewels": "Jewel",
        "flask": "Flask", "flasks": "Flask", "map": "Map", "maps": "Map",
        "sanctum": "Sanctum", "logbook": "Logbook", "currency": "Currency",
        "gem": "Gem", "gems": "Gem", "Unknown": "Misc",
    }

    CATEGORY_ORDER = [
        "armour", "weapon", "accessory", "jewel",
        "flask", "map", "sanctum", "logbook",
        "currency", "gem", "Unknown",
    ]

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(directory),
        autoescape=jinja2.select_autoescape(),
    )

    env.globals["_"] = translate
    env.globals["item_zh"] = translate_item
    env.globals["cat_name"] = CATEGORY_NAMES.get
    env.globals["cat_order"] = CATEGORY_ORDER

    return Jinja2Templates(env=env)
