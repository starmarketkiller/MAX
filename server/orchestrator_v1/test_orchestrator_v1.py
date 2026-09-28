#!/usr/bin/env python3
"""Orchestrator V1 - suite di test: determinismo, validita' degli
schemi, esempi validati, comportamento fail-closed del validatore,
coerenza dell'inventario ambiente/raccomandazione, decisione finale,
nessuna violazione di perimetro, verificatore."""
import json
import os
import sys
import unittest

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
CONTRACTS_DIR = os.path.join(ROOT, "contracts")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, ORCH_DIR)
import build_environment_inventory as env_builder  # noqa: E402
import build_model_recommendation as model_builder  # noqa: E402
import build_install_plan as install_builder  # noqa: E402
import build_migration_matrix as migration_builder  # noqa: E402
import build_first_pilot_spec as pilot_builder  # noqa: E402
import build_roadmap as roadmap_builder  # noqa: E402
import build_final_decision_card as decision_builder  # noqa: E402
import build_example_instances as examples_builder  # noqa: E402
import verify_orchestrator_v1 as verifier  # noqa: E402
from nxs_schema_validator import validate, validate_or_raise  # noqa: E402

ARTIFACTS = [
    ("environment_inventory_v1.json", env_builder.build),
    ("model_recommendation_v1.json", model_builder.build),
    ("install_plan_v1.json", install_builder.build),
    ("migration_matrix_v1.json", migration_builder.build),
    ("first_pilot_spec_v1.json", pilot_builder.build),
    ("roadmap_v1.json", roadmap_builder.build),
    ("final_decision_card_v1.json", decision_builder.build),
]

SCHEMA_FILES = ["task-manifest.schema.json", "agent-capability-registry.schema.json",
               "context-packet.schema.json", "result-packet.schema.json",
               "nexus-event.schema.json"]


class TestDeterminism(unittest.TestCase):
    def test_all_artifacts_deterministic(self):
        for fname, build_fn in ARTIFACTS:
            saved = load_json(os.path.join(ORCH_DIR, fname))
            self.assertEqual(canonical_sha256(saved["payload"]), canonical_sha256(build_fn()), fname)


class TestSchemasWellFormed(unittest.TestCase):
    def test_all_schemas_valid_json(self):
        for sf in SCHEMA_FILES:
            with open(os.path.join(CONTRACTS_DIR, sf), encoding="utf-8") as f:
                schema = json.load(f)
            self.assertIn("$schema", schema)
            self.assertIn("$id", schema)

    def test_schemas_use_draft07(self):
        for sf in SCHEMA_FILES:
            with open(os.path.join(CONTRACTS_DIR, sf), encoding="utf-8") as f:
                schema = json.load(f)
            self.assertIn("draft-07", schema["$schema"])


class TestExampleInstances(unittest.TestCase):
    def test_5_examples_all_valid(self):
        payload = examples_builder.build()
        self.assertEqual(len(payload), 5)
        for label, entry in payload.items():
            self.assertTrue(entry["valid"], label)


class TestValidatorFailsClosed(unittest.TestCase):
    def test_rejects_incomplete_task_manifest(self):
        with open(os.path.join(CONTRACTS_DIR, "task-manifest.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
        errors = validate({"task_id": "X"}, schema)
        self.assertGreater(len(errors), 0)

    def test_rejects_bad_enum_value(self):
        with open(os.path.join(CONTRACTS_DIR, "result-packet.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
        bad = {"task_id": "t", "executor": "e", "start_time": "2026-01-01T00:00:00Z",
              "end_time": "2026-01-01T00:00:00Z", "files_read": [], "files_changed": [],
              "tools_or_commands": [], "artifacts_created": [],
              "tests": {"ran": True, "passed": 1, "failed": 0},
              "verifier": {"ran": True, "passed": True, "errors": []}, "commit": None,
              "push_status": "NOT_PUSHED", "decision": "X", "confidence": "SUPER_HIGH_NOT_REAL",
              "limitations": [], "unresolved_issues": [], "suggested_next_tasks": [],
              "escalation_needed": {"needed": False, "reason": None, "target_tier": None}}
        errors = validate(bad, schema)
        self.assertGreater(len(errors), 0)

    def test_accepts_valid_instance_raises_nothing(self):
        with open(os.path.join(CONTRACTS_DIR, "nexus-event.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
        good = {"event_id": "E1", "event_type": "TASK_CREATED", "task_id": None,
               "timestamp": "2026-01-01T00:00:00Z", "tenant_id": "tenant-1", "payload": {}}
        validate_or_raise(good, schema, "smoke test")  # non deve sollevare


class TestEnvironmentInventory(unittest.TestCase):
    def test_no_gpu_acceleration_flag_present(self):
        payload = env_builder.build()
        self.assertIn("nessuna", payload["hardware"]["gpu_acceleration_available"].lower())

    def test_no_existing_runtime_installed(self):
        payload = env_builder.build()
        self.assertFalse(payload["runtime_inventory"]["ollama"]["installed"])

    def test_github_auth_confirmed(self):
        payload = env_builder.build()
        self.assertTrue(payload["repository_readiness"]["github_auth"].startswith("Autenticato"))


class TestModelRecommendation(unittest.TestCase):
    def test_recommendation_matches_hardware_ceiling(self):
        payload = model_builder.build()
        self.assertIn("Ollama", payload["final_recommendation"]["local_runtime_chosen"])
        self.assertIn("7b", payload["final_recommendation"]["primary_local_model"])

    def test_vllm_excluded_with_reason(self):
        payload = model_builder.build()
        self.assertIn("ESCLUSO", payload["runtime_comparison"]["vLLM"]["verdict"])

    def test_no_heavy_install_flag(self):
        payload = model_builder.build()
        self.assertTrue(payload["no_heavy_install_performed_this_phase"])


class TestInstallPlan(unittest.TestCase):
    def test_not_installed_flag(self):
        payload = install_builder.build()
        self.assertTrue(payload["not_installed_in_this_phase"])

    def test_no_login_required(self):
        payload = install_builder.build()
        self.assertTrue(payload["no_login_required_for_any_step"])


class TestMigrationMatrix(unittest.TestCase):
    def test_backfill_example_present_and_local_strong(self):
        payload = migration_builder.build()
        self.assertEqual(payload["pilot_candidate_tier"], "LOCAL_STRONG")
        titles = [e["task"] for e in payload["examples"]]
        self.assertTrue(any("temporal_concentration" in t and "exit_efficiency" in t for t in titles))


class TestFirstPilotSpec(unittest.TestCase):
    def test_not_executed_flag(self):
        payload = pilot_builder.build()
        self.assertTrue(payload["not_executed_this_phase"])

    def test_task_manifest_example_validates(self):
        with open(os.path.join(CONTRACTS_DIR, "task-manifest.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
        payload = pilot_builder.build()
        validate_or_raise(payload["task_manifest_example"], schema, "pilot task manifest")


class TestRoadmap(unittest.TestCase):
    def test_8_stages_v0_to_v8(self):
        payload = roadmap_builder.build()
        self.assertEqual(len(payload["stages"]), 9)  # V0..V8 inclusi = 9 stadi
        self.assertEqual(payload["stages"][0]["stage"], "V0")
        self.assertEqual(payload["stages"][-1]["stage"], "V8")

    def test_trading_action_stage_is_last(self):
        payload = roadmap_builder.build()
        self.assertIn("approval", payload["stages"][-1]["name"].lower())


class TestFinalDecisionCard(unittest.TestCase):
    def test_architecture_ready(self):
        payload = decision_builder.build()
        self.assertEqual(payload["architecture_decision"], "ORCHESTRATOR_ARCHITECTURE_READY")

    def test_runtime_needs_setup_matches_inventory(self):
        payload = decision_builder.build()
        self.assertEqual(payload["local_runtime_decision"], "LOCAL_RUNTIME_NEEDS_SETUP")

    def test_no_deploy_no_optimization_flags(self):
        payload = decision_builder.build()
        self.assertTrue(payload["no_deploy"])
        self.assertTrue(payload["no_heavy_install_performed"])


class TestNoScopeViolations(unittest.TestCase):
    def test_no_mql5_product_platform_changes(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/"],
                               cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_no_pre_existing_contracts_modified(self):
        import subprocess
        result = subprocess.run(["git", "diff", "--name-only", "--", "contracts/"],
                               cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "")

    def test_docs_architecture_01_17_untouched(self):
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain", "--", "docs/architecture/"],
                               cwd=ROOT, capture_output=True, text=True)
        for line in result.stdout.strip().splitlines():
            base = os.path.basename(line.strip().split()[-1])
            self.assertFalse(any(base.startswith(f"{n:02d}_") for n in range(1, 18)), line)


class TestIndependentVerifier(unittest.TestCase):
    def test_verifier_reports_zero_errors(self):
        self.assertEqual(verifier.verify(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
