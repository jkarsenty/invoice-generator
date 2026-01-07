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

Creer ensuite vos fichiers de travail:
- `config/issuer.json`
- `clients/<client>.json`
- `invoices/<invoice>.json`

CLI metier (recommande)
-----------------------
```bash
uv run python -m scripts.invoice clients
uv run python -m scripts.invoice list
uv run python -m scripts.invoice new
uv run python -m scripts.invoice generate --invoice invoices/invoice.example.json --client clients/client.example.json
cat invoices/invoice.example.json | uv run python -m scripts.invoice generate --stdin --client clients/client.example.json
```

CLI historique (compatible)
---------------------------
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

Validation des donnees
----------------------
Avant toute generation de PDF, les fichiers JSON sont valides.
En cas d'erreur, la generation s'arrete avec un message lisible indiquant le fichier
et le champ en cause. Les cles inconnues sont refusees.

Schemas JSON attendus
---------------------
Regles communes:
- les champs obligatoires sont non vides
- les champs optionnels sont des strings si presents
- les montants restent numeriques jusqu'au rendu

Emetteur (`config/issuer.json`):
- obligatoires: `company_name`, `address`, `email`, `siren`
- optionnels: `representative`, `phone`, `vat_number`, `payment_method`, `iban`, `bic`

Client (`clients/{client}.json`):
- obligatoires: `id`, `name`, `address`, `siren`
- optionnels: `vat_number`, `email`, `notes`

Facture (`invoices/{invoice}.json`):
- obligatoires: `number`, `issue_date`, `service_date`, `due_date`, `items`
- optionnels: `vat_rate` (defaut 20)
Note: si une ligne n'a pas de `date`, la valeur par defaut est derivee de
`service_date` (format attendu: YYYY-MM-DD).
Les champs de date de facture doivent etre au format `YYYY-MM-DD` ou `YYYY/MM/DD`.

Lignes de facture (`items`):
- obligatoires: `description`, `quantity`, `unit_price`
- optionnels: `date` (sinon la date par defaut issue de `service_date`)

Contraintes:
- au moins 1 ligne
- `quantity` > 0
- `unit_price` > 0
- `vat_rate` entre 0 et 100

Exemple facture valide (extrait):
```json
{
  "number": "2024-0001",
  "issue_date": "2024-10-01",
  "service_date": "2024-10-01",
  "due_date": "2024-10-31",
  "vat_rate": 20,
  "items": [
    {
      "description": "Design system",
      "quantity": 2,
      "unit_price": 450
    }
  ]
}
```

Structure du projet
-------------------
- `scripts/invoice.py` point d'entree CLI metier
- `scripts/generate_invoice.py` point d'entree CLI historique
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
