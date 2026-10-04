
from unittest.mock import patch

import pytest
import requests

import cli
from tests.conftest import OFF_PRODUCT


class FakeResponse:
    def __init__(self, resp):
        self._r = resp
        self.status_code = resp.status_code
        self.ok = resp.status_code < 400

    def json(self):
        return self._r.get_json()


@pytest.fixture
def run_cli(client, capsys):
    def fake_request(method, url, **kwargs):
        path = url.split("/api", 1)[1]
        resp = client.open(
            "/api" + path, method=method,
            json=kwargs.get("json"), query_string=kwargs.get("params"),
        )
        return FakeResponse(resp)

    def runner(*argv):
        with patch("cli.requests.request", side_effect=fake_request):
            code = cli.main(list(argv))
        out = capsys.readouterr()
        return code, out.out, out.err

    return runner


def test_add_and_list(run_cli):
    code, out, _ = run_cli("add", "--name", "Milk", "--barcode", "111", "--price", "1.5", "--quantity", "4")
    assert code == 0 and "Item created" in out and "Milk" in out
    code, out, _ = run_cli("list")
    assert code == 0 and "Milk" in out


def test_view_edit_delete(run_cli):
    run_cli("add", "--name", "Milk")
    code, out, _ = run_cli("view", "1")
    assert "Milk" in out
    code, out, _ = run_cli("edit", "1", "--price", "9.99")
    assert code == 0 and "9.99" in out
    code, out, _ = run_cli("delete", "1", "--yes")
    assert code == 0 and "deleted" in out
    code, _, err = run_cli("view", "1")
    assert code == 1 and "not found" in err.lower()


def test_edit_requires_field(run_cli):
    run_cli("add", "--name", "Milk")
    code, _, err = run_cli("edit", "1")
    assert code == 1 and "Nothing to update" in err


def test_json_output(run_cli):
    run_cli("add", "--name", "Milk")
    code, out, _ = run_cli("--json", "view", "1")
    assert '"name": "Milk"' in out


def test_validation_error_surfaces(run_cli):
    code, _, err = run_cli("add", "--name", "X", "--price", "-5")
    assert code == 1 and "price" in err


@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_lookup_barcode_command(_m, run_cli):
    code, out, _ = run_cli("lookup-barcode", "3017620422003")
    assert code == 0 and "Nutella" in out


@patch("app.routes.off.search_by_name", return_value=[OFF_PRODUCT])
def test_lookup_name_command(_m, run_cli):
    code, out, _ = run_cli("lookup-name", "nutella")
    assert code == 0 and "Nutella" in out and "Ferrero" in out


@patch("app.routes.off.fetch_by_barcode", return_value=OFF_PRODUCT)
def test_add_with_enrich_flag(_m, run_cli):
    code, out, _ = run_cli("add", "--name", "Spread", "--barcode", "3017620422003", "--enrich")
    assert code == 0 and "Ferrero" in out


def test_connection_error_message(capsys):
    with patch("cli.requests.request", side_effect=requests.ConnectionError):
        code = cli.main(["list"])
    assert code == 1
    assert "Cannot connect" in capsys.readouterr().err


def test_delete_cancelled(run_cli):
    run_cli("add", "--name", "Milk")
    with patch("builtins.input", return_value="n"):
        code, out, _ = run_cli("delete", "1")
    assert "Cancelled" in out
    assert "Milk" in run_cli("list")[1]
