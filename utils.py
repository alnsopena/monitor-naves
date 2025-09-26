# utils.py
# Archivo de utilidades con funciones compartidas

import json
import config

def is_in_error_state():
    """Comprueba si el script está actualmente en estado de error."""
    try:
        with open(config.ERROR_STATE_FILE, 'r') as f:
            state = json.load(f)
            return state.get("in_error_state", False)
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def set_error_state(status: bool):
    """Establece el estado de error del script."""
    with open(config.ERROR_STATE_FILE, 'w') as f:
        json.dump({"in_error_state": status}, f)
