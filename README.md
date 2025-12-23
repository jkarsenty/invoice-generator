Invoice Generator (Python)
==========================

Projet Python simple pour generer des factures PDF professionnelles a partir de
fichiers JSON. Les factures sont rendues en HTML/CSS (Jinja2), puis converties
en PDF via WeasyPrint.

Fonctionnalites
---------------
- Generation de PDF via CLI
- Configuration JSON (emetteur, clients, factures)
- Templates HTML/CSS personnalisables
- Aucune base de donnees
- Architecture claire et modulaire

Prerequis
---------
- Python 3.11+
- Dependances: `jinja2`, `weasyprint` (voir `pyproject.toml`)

Utilisation
-----------
Utiliser uniquement les fichiers d'exemple comme base:
- `config/issuer.example.json`
- `clients/client.example.json`
- `invoices/invoice.example.json`

```bash
uv run python -m scripts.generate_invoice \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output output/invoice.example.pdf
```

Sortie
------
Le PDF est ecrit au chemin indique par `--output` (le dossier est cree si besoin).
Guide: pour l'exemple ci-dessus, le fichier est genere dans `output/invoice.example.pdf`.

Structure du projet
-------------------
- `scripts/generate_invoice.py` point d'entree CLI
- `config/` infos emetteur (exemple: `config/issuer.example.json`)
- `clients/` donnees clients (exemple: `clients/client.example.json`)
- `invoices/` contenu factures (exemple: `invoices/invoice.example.json`)
- `templates/` templates HTML/CSS
- `output/` PDFs generes

Personnalisation
----------------
Vous pouvez:
- modifier les JSON d'exemple
- personnaliser les templates HTML/CSS
- remplacer le logo d'exemple

Confidentialite et donnees
--------------------------
Ce depot ne doit contenir aucune facture reelle ni donnee personnelle.
Seuls les fichiers `.example.json` doivent etre versionnes.

Licence
-------
MIT
