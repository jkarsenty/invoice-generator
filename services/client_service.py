import json
from pathlib import Path

from core.errors import InvalidInputError, NotFoundError, ValidationError
from core.loader import load_json
from core.validate import ValidationError as CoreValidationError
from core.validate import validate_client_data


def _load_json_file(path: Path, label: str) -> dict:
    try:
        data = load_json(path)
    except FileNotFoundError:
        raise CoreValidationError(label, "<fichier>", "introuvable") from None
    except json.JSONDecodeError:
        raise CoreValidationError(label, "<fichier>", "JSON invalide") from None

    if not isinstance(data, dict):
        raise CoreValidationError(label, "<racine>", "mauvais type (objet JSON attendu)")

    return data


def list_clients(clients_dir: Path) -> dict:
    clients = []
    errors = []
    for path in sorted(clients_dir.glob("*.json")):
        try:
            data = _load_json_file(path, path.as_posix())
            client = validate_client_data(data, path.as_posix())
        except CoreValidationError as exc:
            errors.append(str(exc))
            continue
        clients.append(
            {
                "path": path,
                "id": client.id,
                "name": client.name,
                "data": data,
                "filename": path.name,
            }
        )
    return {"clients": clients, "errors": errors}


def resolve_client_selector(
    selector: str,
    *,
    base_dir: Path,
    clients_dir: Path,
) -> dict:
    listed = list_clients(clients_dir)
    clients = listed["clients"]

    if not clients:
        raise NotFoundError("Aucun client valide disponible.")

    if selector.isdigit():
        index = int(selector)
        if 1 <= index <= len(clients):
            return clients[index - 1]
        raise InvalidInputError("Index client invalide.")

    candidate = Path(selector)
    if not candidate.is_absolute():
        candidate = base_dir / selector
    if candidate.exists():
        try:
            data = _load_json_file(candidate, candidate.as_posix())
            client = validate_client_data(data, candidate.as_posix())
        except CoreValidationError as exc:
            raise ValidationError(str(exc)) from None
        return {
            "path": candidate,
            "id": client.id,
            "name": client.name,
            "data": data,
            "filename": candidate.name,
        }

    candidate = clients_dir / selector
    if candidate.exists():
        try:
            data = _load_json_file(candidate, candidate.as_posix())
            client = validate_client_data(data, candidate.as_posix())
        except CoreValidationError as exc:
            raise ValidationError(str(exc)) from None
        return {
            "path": candidate,
            "id": client.id,
            "name": client.name,
            "data": data,
            "filename": candidate.name,
        }

    selector_lower = selector.lower()
    for client in clients:
        if (
            client["id"].lower() == selector_lower
            or client["name"].lower() == selector_lower
            or client["filename"].lower() == selector_lower
            or client["filename"].lower().removesuffix(".json") == selector_lower
        ):
            return client

    raise NotFoundError("Client introuvable.")
