"""The company/statements API a separate frontend calls -- real data, not mocks, since
whether the DIU/CoA rollup actually reaches the route correctly is exactly what a mock
would hide.

Run:  python -m pytest tests/ -q      (or: python tests/test_companies_api.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.app import app


def _client():
    return app.test_client()


def test_companies_lists_the_four_real_funds() -> None:
    response = _client().get("/api/companies")
    assert response.status_code == 200
    companies = response.get_json()["companies"]
    assert len(companies) == 4
    assert all({"id", "name"} == set(c) for c in companies)
    assert "Nordvik Infrastructure V SCSp" in [c["name"] for c in companies]


def test_balance_sheet_for_a_real_company() -> None:
    companies = _client().get("/api/companies").get_json()["companies"]
    company_id = companies[0]["id"]

    response = _client().get(f"/api/companies/{company_id}/balance-sheet")
    assert response.status_code == 200
    body = response.get_json()
    assert body["legal_entity"] == companies[0]["name"]
    assert body["ties"] is True
    assert "no opening balance" in body["period"]


def test_income_statement_for_a_real_company() -> None:
    companies = _client().get("/api/companies").get_json()["companies"]
    company_id = companies[0]["id"]

    response = _client().get(f"/api/companies/{company_id}/income-statement")
    assert response.status_code == 200
    body = response.get_json()
    assert body["net_income"] == round(body["revenues"] - body["expenses"], 2)


def test_cash_flow_is_honest_about_not_being_available() -> None:
    companies = _client().get("/api/companies").get_json()["companies"]
    company_id = companies[0]["id"]

    response = _client().get(f"/api/companies/{company_id}/cash-flow")
    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is False
    assert body["reason"]


def test_unknown_company_id_is_a_404_not_a_crash() -> None:
    for endpoint in ("balance-sheet", "income-statement", "cash-flow"):
        response = _client().get(f"/api/companies/not-a-real-company/{endpoint}")
        assert response.status_code == 404


def test_review_scoped_per_company_sums_to_the_whole_dataset() -> None:
    """Every transaction belongs to exactly one company, so filtering /api/review by
    each company id in turn and summing the counts must reproduce the unfiltered total --
    otherwise a row is either double-counted or has fallen through the filter."""
    client = _client()
    whole = client.get("/api/review?all=1").get_json()
    companies = client.get("/api/companies").get_json()["companies"]

    total = 0
    for company in companies:
        scoped = client.get(f"/api/review?all=1&company={company['id']}").get_json()
        total += len(scoped["items"])
        for item in scoped["items"]:
            assert item["transaction"]["row_id"] is not None
    assert total == len(whole["items"])


def test_review_rejects_an_unknown_company() -> None:
    response = _client().get("/api/review?company=not-a-real-company")
    assert response.status_code == 404


def test_api_routes_carry_cors_headers_but_pages_do_not() -> None:
    """The frontend runs on a different origin -- see app.py's after_request hook.
    Server-rendered pages are navigated to directly and never fetched cross-origin."""
    api_response = _client().get("/api/companies")
    assert api_response.headers.get("Access-Control-Allow-Origin") == "*"

    page_response = _client().get("/")
    assert "Access-Control-Allow-Origin" not in page_response.headers


if __name__ == "__main__":
    test_companies_lists_the_four_real_funds()
    test_balance_sheet_for_a_real_company()
    test_income_statement_for_a_real_company()
    test_cash_flow_is_honest_about_not_being_available()
    test_unknown_company_id_is_a_404_not_a_crash()
    test_review_scoped_per_company_sums_to_the_whole_dataset()
    test_review_rejects_an_unknown_company()
    test_api_routes_carry_cors_headers_but_pages_do_not()
    print("all companies API checks pass")
