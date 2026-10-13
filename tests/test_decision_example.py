from copy import deepcopy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("decision_payloads", ROOT / "examples/decision-routing/payloads.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DecisionPreparationTests(unittest.TestCase):
    def setUp(self):
        self.questions = {"need_source": {"type": "noul", "instructions": "需要取得原文吗？"}}

    def test_jev_has_no_inner_model(self):
        body = mod.prepare_cf("cf-jev", "synthetic", self.questions)
        self.assertEqual(body["model"], "typesafe/jev")
        self.assertNotIn("model", body["input"])

    def test_clef_selectors_are_consistent(self):
        for route, inner in [("cf-clef", "clef"), ("cf-clef-flash", "clef-flash"), ("cf-clef-omni", "clef-omni")]:
            with self.subTest(route=route):
                body = mod.prepare_cf(route, "synthetic", self.questions)
                self.assertEqual(body["input"], {"state": "synthetic", "questions": self.questions, "model": inner})
                self.assertEqual(body["model"], "@cf/cloudflare/" + inner)

    def test_all_cf_catalog_routes_have_matching_request_selectors(self):
        rows = json.loads((ROOT / "catalog/decision-routes.json").read_text())["routes"]
        catalog_selectors = {row["id"]: row["selector"] for row in rows if row["id"].startswith("cf-")}
        self.assertEqual(set(mod.CF_MODELS), set(catalog_selectors))
        for route, selector in catalog_selectors.items():
            with self.subTest(route=route):
                self.assertEqual(mod.prepare_cf(route, "synthetic", self.questions)["model"], selector)

    def test_input_does_not_mutate(self):
        for route in mod.CF_MODELS:
            with self.subTest(route=route):
                original = deepcopy(self.questions)
                state = {"records": ["synthetic"]}
                body = mod.prepare_cf(route, state, self.questions)
                body["input"]["questions"]["need_source"]["instructions"] = "changed"
                body["input"]["state"]["records"].append("changed")
                self.assertEqual(self.questions, original)
                self.assertEqual(state, {"records": ["synthetic"]})

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("auto", "state", self.questions)

    def test_empty_questions_rejected(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("cf-jev", "state", {})

    def test_demo_limit(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("cf-jev", "x" * 17000, self.questions)

    def test_cost_arithmetic_with_fixed_inputs(self):
        # Fixed mathematical fixtures, independent of a provider's current price.
        for tokens, unit_price, expected in [
            (0, "0.09", "0"),
            (50_000_000, "0.09", "4.50"),
            (1_234_567, "0.038", "0.046913546"),
            (1, "0.150", "0.00000015"),
        ]:
            with self.subTest(tokens=tokens, unit_price=unit_price):
                self.assertEqual(mod.input_cost(tokens, unit_price), Decimal(expected))

    def test_current_cf_catalog_costs(self):
        # Current source-backed values: all CF routes must be covered, including
        # a newly catalogued model that could otherwise be silently skipped.
        expected = {
            "cf-jev": ("0.042", "2.10"),
            "cf-clef-flash": ("0.038", "1.90"),
            "cf-clef-omni": ("0.150", "7.50"),
            "cf-clef": ("0.24", "12.00"),
        }
        rows = json.loads((ROOT / "catalog/decision-routes.json").read_text())["routes"]
        cf_rows = {row["id"]: row for row in rows if row["id"].startswith("cf-")}
        self.assertEqual(set(cf_rows), set(expected))
        for route, (unit_price, charge) in expected.items():
            with self.subTest(route=route):
                catalog_price = cf_rows[route]["input_usd_per_million"]
                self.assertEqual(Decimal(catalog_price), Decimal(unit_price))
                self.assertEqual(mod.input_cost(50_000_000, catalog_price), Decimal(charge))

    def test_invalid_cost_inputs(self):
        for tokens, price in [(-1, "0.1"), (True, "0.1"), (1, "NaN"), (1, "-1")]:
            with self.assertRaises(ValueError):
                mod.input_cost(tokens, price)

    def test_imprecise_display_price_is_not_calculable(self):
        rows = json.loads((ROOT / "catalog/decision-routes.json").read_text())["routes"]
        vercel = next(r for r in rows if r["id"] == "vercel-jev")
        self.assertIsNone(vercel["input_usd_per_million"])
        self.assertEqual(vercel["display_price"], "$0.04/M")

    def test_personal_author_not_github_handle(self):
        for name in ["reports/2026-10-02.md", "guides/handbook.md", "comparisons/clef-vs-jev.md"]:
            text = (ROOT / name).read_text()
            self.assertIn("author: Faye & Cove", text)
            self.assertIn("github: https://github.com/IndelibleVivi", text)
            self.assertNotIn("author: IndelibleVivi", text)


if __name__ == "__main__":
    unittest.main()
