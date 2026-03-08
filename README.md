Invoice Generator (Python)
==========================

Projet Python pour produire des factures a partir de JSON, avec un flux **JSON d'abord** puis conversion PDF optionnelle.

Fonctionnalites
---------------
- CLI Typer claire et typée
- Validation stricte des JSON (issuer/client/invoice)
- Generation JSON interactive
- Conversion PDF explicite depuis un JSON valide
- Refus d'ecrasement par defaut (`--force` requis)

Prerequis
---------
- Python 3.11+
- Dependances Python: `typer`, `jinja2`, `weasyprint`
- Pour le PDF, installer aussi les libs systeme WeasyPrint (ex: cairo, pango, gdk-pixbuf, libffi)

Utilisation
-----------
Utiliser les exemples comme base:
- `config/issuer.example.json`
- `clients/client.example.json`
- `invoices/invoice.example.json`

Creer ensuite vos fichiers de travail:
- `config/issuer.json`
- `clients/<client>.json`
- `invoices/<invoice>.json`

CLI (contrat JSON-first)
------------------------
```bash
# commandes non-PDF
uv run python -m scripts.invoice --help
uv run python -m scripts.invoice clients
uv run python -m scripts.invoice list

# JSON
uv run python -m scripts.invoice json validate --invoice invoices/invoice.example.json
uv run python -m scripts.invoice json new
uv run python -m scripts.invoice json new --force

# PDF explicite
uv run python -m scripts.invoice pdf from-json \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output output/invoice.example.pdf

# compat temporaire (deprecie)
uv run python -m scripts.invoice generate --invoice invoices/invoice.example.json --client clients/client.example.json
```

Comportement garanti
--------------------
Commande | Effet | Code sortie
--- | --- | ---
`invoice clients` | Liste les clients valides + erreurs de validation | `0` si succes
`invoice list` | Liste les factures JSON et leur statut | `0` si succes
`invoice json validate --invoice <path>` | Valide schema/types/contraintes d'une facture JSON | `0` valide, `1` invalide
`invoice json new` | Cree une facture JSON interactive, puis demande `Convertir en PDF maintenant ? (o/N)` | `0` si succes
`invoice pdf from-json ...` | Genere un PDF depuis JSON + client | `0` si succes
`invoice generate ...` | Alias de compatibilite (deprecie) | `0` si succes

Politique de securite
---------------------
- JSON existant: refus d'ecrasement
- PDF existant: refus d'ecrasement
- `--force`: seul moyen d'ecraser

Validation des donnees
----------------------
Avant creation/validation/generation:
- champs obligatoires non vides
- types controles strictement
- cles inconnues refusees
- contraintes metier verifiees (`items`, quantites, prix, TVA)

Tests
-----
Tests automatises inclus:
- services: auto-numerotation, anti-ecrasement, `--force`
- CLI: help/list/clients sans crash PDF, codes de sortie, flux `json new` avec/sans conversion

Commande:
```bash
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Structure
---------
- `scripts/invoice.py`: point d'entree
- `cli/`: interface Typer
- `services/`: logique metier re-utilisable
- `core/`: validation/schema/rendu
- `templates/`: HTML/CSS facture

Licence
-------
MIT
