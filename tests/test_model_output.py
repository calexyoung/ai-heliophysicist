"""Offline tests for the CCMC/ISWA model-output registry and refusals.

The live server is exercised in validation/run_validation.py (case `models`).
These pin the registry's internal consistency and the argument handling.
"""

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.models_iswa import _PRODUCTS, available_products


def test_registry_is_internally_consistent():
    for (model, product), variants in _PRODUCTS.items():
        assert model and product and variants
        for v in variants:
            assert {"run", "dataset", "parameters", "columns"} <= set(v)
            params = [p.strip() for p in v["parameters"].split(",")]
            # every fetched parameter must have a rename, or it would reach
            # the CSV under ISWA's own name and collide with observations
            assert set(params) == set(v["columns"]), (model, product, v["run"])
            # renamed columns must be namespaced by model
            for col in v["columns"].values():
                assert col.startswith(f"{model}_"), col


def test_templated_datasets_declare_their_satellites():
    for (model, product), variants in _PRODUCTS.items():
        for v in variants:
            if "{sat}" in v["dataset"]:
                assert v.get("satellites"), (model, product, v["run"])
            else:
                assert not v.get("satellites"), (model, product, v["run"])


def test_runs_are_listed_newest_first():
    """Default selection takes the first covering variant, so ordering is
    load-bearing: a newer model version must be preferred."""
    for (model, product), variants in _PRODUCTS.items():
        numeric = [v["run"] for v in variants if v["run"].isdigit()]
        assert numeric == sorted(numeric, reverse=True), (model, product)


def test_available_products_is_sorted_and_complete():
    ap = available_products()
    assert ap == sorted(ap)
    assert ("swmf", "dst") in ap and ("enlil", "kp") in ap


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(model="swmf", product="nope", start="2024-05-10", end="2024-05-11"),
     "no product"),
    (dict(model="nope", product="dst", start="2024-05-10", end="2024-05-11"),
     "no product"),
    (dict(model="swmf", product="dst", start="2024-05-10", end="2024-05-09"),
     "end must be after start"),
    (dict(model="swmf", product="dst", start="not-a-date", end="2024-05-11"),
     "bad timestamp"),
    (dict(model="swmf", product="dst", start="2024-05-10", end="2024-05-11",
          run="1999"), "no run"),
])
def test_refusals_are_explicit(kwargs, fragment):
    r = run_tool("fetch_model_output", **kwargs)
    assert r["status"] == "error"
    assert fragment in r["error"], r["error"]


def test_satellite_products_require_a_satellite():
    r = run_tool("fetch_model_output", model="swmf", product="themis",
                 start="2026-09-03", end="2026-09-04")
    assert r["status"] == "error"
    assert "needs `satellite`" in r["error"]
    bad = run_tool("fetch_model_output", model="swmf", product="themis",
                   start="2026-09-03", end="2026-09-04", satellite="Z")
    assert bad["status"] == "error"
    assert "not in" in bad["error"]
