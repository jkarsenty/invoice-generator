import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PYTHON_BIN = REPO / ".venv" / "bin" / "python"


def _run(*args):
    return subprocess.run(
        [str(PYTHON_BIN), "-m", "scripts.invoice", *args],
        cwd=str(REPO),
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works_without_pdf_runtime():
    result = _run("--help")
    assert result.returncode == 0
    assert "Usage" in result.stdout


def test_clients_and_list_do_not_crash():
    clients = _run("clients")
    invoices = _run("list")
    assert clients.returncode == 0
    assert invoices.returncode == 0


def test_generate_usage_error_exit_code_2():
    result = _run("generate")
    assert result.returncode == 2
    assert "Invalid value for --invoice/--stdin" in result.stderr
    assert "one of the arguments --invoice --stdin" in result.stderr


def test_json_validate_invalid_returns_1(tmp_path):
    invalid = tmp_path / "bad.json"
    invalid.write_text("{bad}", encoding="utf-8")
    result = _run("json", "validate", "--invoice", str(invalid))
    assert result.returncode == 1
    assert "JSON invalide" in result.stderr


def test_help_contains_descriptions_for_clients_and_list():
    result = _run("--help")
    assert result.returncode == 0
    assert "Lister les factures JSON presentes dans invoices/." in result.stdout
    assert "Lister les clients valides et signaler les clients" in result.stdout
    assert "invalides." in result.stdout
