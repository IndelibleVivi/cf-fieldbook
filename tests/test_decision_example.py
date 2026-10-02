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
        for route, inner in [("cf-clef", "clef"), ("cf-clef-flash", "clef-flash")]:
            body = mod.prepare_cf(route, "synthetic", self.questions)
            self.assertEqual(body["input"]["model"], inner)
            self.assertEqual(body["model"], "@cf/cloudflare/" + inner)

    def test_input_does_not_mutate(self):
        original = deepcopy(self.questions)
        body = mod.prepare_cf("cf-clef", {"text": "synthetic"}, self.questions)
        body["input"]["questions"]["need_source"]["instructions"] = "changed"
        self.assertEqual(self.questions, original)

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("auto", "state", self.questions)

    def test_empty_questions_rejected(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("cf-jev", "state", {})

    def test_demo_limit(self):
        with self.assertRaises(ValueError):
            mod.prepare_cf("cf-jev", "x" * 17000, self.questions)

    def test_known_costs(self):
        expected = {"cf-jev": Decimal("2.10"), "cf-clef-flash": Decimal("4.50"), "cf-clef": Decimal("12.00")}
        rows = json.loads((ROOT / "catalog/decision-routes.json").read_text())["routes"]
        for row in rows:
            if row["id"] in expected:
                self.assertEqual(mod.input_cost(50_000_000, row["input_usd_per_million"]), expected[row["id"]])

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
