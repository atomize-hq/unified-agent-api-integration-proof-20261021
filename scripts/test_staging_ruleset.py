from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import check_staging_ruleset as check


ROOT = Path(__file__).resolve().parents[1]
REPO = "atomize-hq/unified-agent-api"
DESIRED = ROOT / "docs/agents/lifecycle/staging-integration-ruleset.json"


class RulesetTests(unittest.TestCase):
    def setUp(self):
        self.desired = json.loads(DESIRED.read_text())
        self.detail = copy.deepcopy(self.desired) | {
            "id": 42, "source_type": "Repository", "source": REPO, "current_user_can_bypass": "never",
        }
        self.listed = [{key: self.detail[key] for key in
                        ("id", "name", "target", "source_type", "source", "enforcement")}]
        self.effective = [copy.deepcopy(rule) | {
            "ruleset_id": 42, "ruleset_source_type": "Repository", "ruleset_source": REPO,
        } for rule in self.desired["rules"]]
        self.legacy = {"data": {"repository": {"nameWithOwner": REPO, "viewerPermission": "ADMIN", "ref": {
            "name": "staging", "branchProtectionRule": None,
        }}}}
        self.calls = []

    def api(self, argv, **kwargs):
        self.calls.append(argv)
        self.assertEqual(argv[:5], ["gh", "api", "--hostname", "github.com", "--method"])
        route = next(arg for arg in argv if arg == "graphql" or arg.startswith("repos/"))
        if route == "graphql":
            self.assertEqual(argv[5], "POST")
            self.assertIn("query=" + check.LEGACY_QUERY, argv)
            self.assertTrue(check.LEGACY_QUERY.startswith("query("))
            value = self.legacy
        else:
            self.assertEqual(argv[5], "GET")
            values = {
                f"repos/{REPO}/rulesets?includes_parents=true&per_page=100": [self.listed],
                f"repos/{REPO}/rules/branches/staging?per_page=100": [self.effective],
                f"repos/{REPO}/rulesets/42?includes_parents=true": self.detail,
            }
            self.assertIn(route, values)
            value = values[route]
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")

    def compare(self):
        with patch.object(check.subprocess, "run", side_effect=self.api):
            return check.compare(REPO, self.desired)

    def test_missing_installation_is_different_not_match(self):
        self.listed = []
        self.effective = []
        self.assertEqual(self.compare()["status"], "different")

    def test_exact_configuration_matches_using_only_read_operations(self):
        result = self.compare()
        self.assertEqual(result["status"], "match")
        self.assertEqual(result["differences"], [])
        self.assertEqual(len(self.calls), 4)

    def test_policy_changes_never_match(self):
        original = copy.deepcopy(self.detail)
        effective = copy.deepcopy(self.effective)
        for field, value in [
            ("enforcement", "disabled"), ("bypass_actors", [{"actor_type": "OrganizationAdmin"}]),
            ("conditions", {"ref_name": {"include": ["~ALL"], "exclude": ["refs/heads/staging"]}}),
            ("rules", self.detail["rules"][:-1]),
        ]:
            self.detail = copy.deepcopy(original)
            self.effective = copy.deepcopy(effective)
            self.listed[0]["enforcement"] = "active"
            self.detail[field] = value
            if field == "enforcement":
                self.effective = []
            if field in self.listed[0]:
                self.listed[0][field] = value
            with self.subTest(field=field):
                self.assertEqual(self.compare()["status"], "different")

    def test_overlapping_inherited_or_legacy_protection_does_not_match(self):
        self.effective.append({"type": "required_signatures", "ruleset_id": 99,
                               "ruleset_source_type": "Organization", "ruleset_source": "atomize-hq"})
        self.listed.append({"id": 99, "name": "org", "target": "branch", "enforcement": "active",
                            "source_type": "Organization", "source": "atomize-hq"})
        self.assertEqual(self.compare()["status"], "different")
        self.effective.pop()
        self.listed.pop()
        self.legacy["data"]["repository"]["ref"]["branchProtectionRule"] = {"id": "legacy"}
        self.assertEqual(self.compare()["status"], "different")

    def test_semantic_order_and_server_metadata_do_not_create_drift(self):
        self.detail.update(node_id="opaque", created_at="yesterday", updated_at="today", _links={})
        self.detail["rules"].reverse()
        self.detail["rules"][1]["parameters"]["required_status_checks"].reverse()
        self.detail["rules"][-1]["parameters"] = {}
        self.effective.reverse()
        self.assertEqual(self.compare()["status"], "match")

    def test_each_critical_policy_parameter_is_compared(self):
        original = copy.deepcopy(self.detail)
        mutations = [
            (2, "required_approving_review_count", 1),
            (2, "allowed_merge_methods", ["merge", "squash"]),
            (3, "strict_required_status_checks_policy", False),
            (3, "do_not_enforce_on_create", True),
            (3, "required_status_checks", original["rules"][3]["parameters"]["required_status_checks"][:-1]),
            (3, "required_status_checks", [{"context": "Staging integration gate", "integration_id": 1}]),
            (4, "merge_method", "SQUASH"), (4, "max_entries_to_build", 2),
            (4, "max_entries_to_merge", 2), (4, "grouping_strategy", "HEADGREEN"),
            (4, "check_response_timeout_minutes", 30),
        ]
        for index, key, value in mutations:
            self.detail = copy.deepcopy(original)
            self.detail["rules"][index]["parameters"][key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(self.compare()["status"], "different")
        self.detail = copy.deepcopy(original)
        self.detail["rules"][2]["parameters"]["dismiss_stale_reviews_on_push"] = 0
        self.assertEqual(self.compare()["status"], "different")  # false is not integer zero.

    def test_host_returned_review_defaults_remain_exact_policy(self):
        # Regression for isolated ruleset 25591182: compare every returned policy field,
        # both in the ruleset detail and independently in effective branch rules.
        original_detail = copy.deepcopy(self.detail)
        original_effective = copy.deepcopy(self.effective)
        changes = [
            ("required_reviewers", [{"reviewer": {"id": 1, "type": "Team"},
                                      "file_patterns": ["*"], "minimum_approvals": 1}]),
            ("dismissal_restriction", {"enabled": True, "allowed_actors": []}),
            ("require_extra_approval_for_unattributed_changes", False),
        ]
        for source in ("detail", "effective"):
            for key, value in changes:
                for variant in ("changed", "missing", "wrong_type"):
                    self.detail = copy.deepcopy(original_detail)
                    self.effective = copy.deepcopy(original_effective)
                    rules = self.detail["rules"] if source == "detail" else self.effective
                    parameters = rules[2]["parameters"]
                    if variant == "missing":
                        del parameters[key]
                    else:
                        parameters[key] = value if variant == "changed" else None
                    with self.subTest(source=source, key=key, variant=variant):
                        self.assertEqual(self.compare()["status"], "different")

    def test_effective_rules_must_independently_match_the_full_policy(self):
        original = copy.deepcopy(self.effective)
        for rules in [original[:-1], original + [original[0]],
                      original[:3] + [original[3] | {"parameters": {}}] + original[4:]]:
            self.effective = rules
            with self.subTest(rules=rules):
                self.assertEqual(self.compare()["status"], "different")

    def test_partial_hidden_unknown_and_contradictory_readback_is_unavailable(self):
        original = copy.deepcopy(self.detail)
        for key, value in [("bypass_actors", None), ("enforcement", "evaluate"),
                           ("source", "other/repo"), ("future_policy_field", True)]:
            self.detail = copy.deepcopy(original)
            if key == "bypass_actors":
                self.detail.pop(key)  # API can hide bypass actors from insufficiently privileged readers.
            else:
                self.detail[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.compare()

    def test_missing_ref_legacy_field_visibility_and_query_errors_are_unavailable(self):
        original = copy.deepcopy(self.legacy)
        variants = [None, {}, {"errors": [{"message": "not authorized"}], "data": original["data"]}]
        for mutate in [lambda r: r.update(ref=None), lambda r: r.update(viewerPermission="READ"),
                       lambda r: r["ref"].pop("branchProtectionRule"),
                       lambda r: r.update(nameWithOwner="other/repository")]:
            variant = copy.deepcopy(original)
            mutate(variant["data"]["repository"])
            variants.append(variant)
        for value in variants:
            self.legacy = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.compare()

    def test_pagination_keeps_later_inherited_effective_rules(self):
        self.listed.append({"id": 99, "name": "org", "target": "branch", "enforcement": "active",
                            "source_type": "Organization", "source": "atomize-hq"})
        self.effective.append({"type": "required_signatures", "ruleset_id": 99,
                               "ruleset_source_type": "Organization", "ruleset_source": "atomize-hq"})
        original_api = self.api

        def paginated(argv, **kwargs):
            result = original_api(argv, **kwargs)
            if "--paginate" in argv:
                self.assertIn("--slurp", argv)
                page = json.loads(result.stdout)[0]
                result.stdout = json.dumps([page[:-1], page[-1:]])
            return result

        with patch.object(check.subprocess, "run", side_effect=paginated):
            self.assertEqual(check.compare(REPO, self.desired)["status"], "different")

    def test_inventory_must_be_complete_unambiguous_and_supported(self):
        original = copy.deepcopy(self.listed)
        variants = [original * 2, original + [original[0] | {"id": 43}],
                    [original[0] | {"target": "push"}], [original[0] | {"enforcement": "future"}],
                    [original[0] | {"id": True}], []]
        for value in variants:
            self.listed = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.compare()

    def test_unrelated_main_ruleset_does_not_change_staging_match(self):
        self.listed.append({"id": 99, "name": "protect main", "target": "branch", "enforcement": "active",
                            "source_type": "Repository", "source": REPO})
        self.assertEqual(self.compare()["status"], "match")

    def run_main(self, side_effect=None):
        out = io.StringIO()
        with patch.object(check.subprocess, "run", side_effect=side_effect or self.api), redirect_stdout(out):
            code = check.main(["--repo", REPO])
        return code, json.loads(out.getvalue())

    def test_cli_reports_match_difference_and_unavailable_distinctly_without_secrets(self):
        code, report = self.run_main()
        self.assertEqual((code, report["status"]), (0, "match"))
        self.assertEqual(report["scope"], "configuration comparison only")
        self.assertIn("desired_sha256", report)
        self.listed = []
        self.effective = []
        code, report = self.run_main()
        self.assertEqual((code, report["status"]), (1, "different"))
        sentinel = "credential-sentinel-do-not-print"
        failures = [subprocess.CompletedProcess([], 1, "", sentinel),
                    subprocess.CompletedProcess([], 0, sentinel, "")]
        for failure in failures:
            code, report = self.run_main(lambda *args, **kwargs: failure)
            self.assertEqual((code, report["status"]), (2, "unavailable"))
            self.assertNotIn(sentinel, json.dumps(report))
        for failure in [OSError(sentinel), subprocess.TimeoutExpired([sentinel], 60)]:
            def fail(*args, **kwargs):
                raise failure
            code, report = self.run_main(fail)
            self.assertEqual((code, report["status"]), (2, "unavailable"))
            self.assertNotIn(sentinel, json.dumps(report))

    def test_malformed_or_empty_pagination_is_unavailable(self):
        for value in [[], {}, [None], [self.detail], None]:
            result = subprocess.CompletedProcess([], 0, json.dumps(value), "")
            code, report = self.run_main(lambda *args, **kwargs: result)
            with self.subTest(value=value):
                self.assertEqual((code, report["status"]), (2, "unavailable"))

    def test_invalid_repository_or_desired_scope_makes_no_network_request(self):
        for repo in ["../repo", "owner/repo/other", "-", "owner/..", "https://github.com/a/b"]:
            with patch.object(check.subprocess, "run") as run, self.assertRaises(ValueError):
                check.compare(repo, self.desired)
            run.assert_not_called()
        for conditions in [{"ref_name": {"include": ["~ALL"], "exclude": []}}, None]:
            with patch.object(check.subprocess, "run") as run, self.assertRaises(ValueError):
                check.compare(REPO, self.desired | {"conditions": conditions})
            run.assert_not_called()

    def test_committed_desired_policy_preserves_approved_choices(self):
        d = self.desired
        self.assertEqual(d["bypass_actors"], [])
        self.assertEqual(d["conditions"], {"ref_name": {"include": ["refs/heads/staging"], "exclude": []}})
        rules = {rule["type"]: rule.get("parameters", {}) for rule in d["rules"]}
        self.assertEqual(set(rules), {"deletion", "non_fast_forward", "pull_request", "required_status_checks", "merge_queue"})
        self.assertEqual(rules["pull_request"], {
            "allowed_merge_methods": ["merge"], "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False, "require_last_push_approval": False,
            "required_approving_review_count": 0, "required_review_thread_resolution": False,
            "required_reviewers": [], "dismissal_restriction": {"enabled": False, "allowed_actors": []},
            "require_extra_approval_for_unattributed_changes": True})
        self.assertFalse(rules["required_status_checks"]["do_not_enforce_on_create"])
        self.assertTrue(rules["required_status_checks"]["strict_required_status_checks_policy"])
        contexts = rules["required_status_checks"]["required_status_checks"]
        self.assertEqual({c["context"] for c in contexts}, {
            "Staging integration gate", "Preflight", "Capability matrix (fresh + audit)",
            "Validate Codex committed artifacts", "Validate Claude Code committed artifacts",
            "Validate OpenCode committed artifacts"})
        self.assertEqual([c["integration_id"] for c in contexts], [15368] * 6)
        self.assertEqual(rules["merge_queue"], {
            "check_response_timeout_minutes": 60, "grouping_strategy": "ALLGREEN",
            "max_entries_to_build": 1, "max_entries_to_merge": 1, "merge_method": "MERGE",
            "min_entries_to_merge": 1, "min_entries_to_merge_wait_minutes": 0})

    def test_current_viewer_bypass_metadata_only_accepts_explicit_never(self):
        self.detail["current_user_can_bypass"] = "never"
        code, report = self.run_main()
        self.assertEqual((code, report["status"]), (0, "match"))
        for value in ["always", "pull_requests_only", "unknown", None, False, [], {}]:
            self.detail["current_user_can_bypass"] = value
            code, report = self.run_main()
            with self.subTest(value=value):
                self.assertEqual((code, report["status"]), (2, "unavailable"))
        self.detail["current_user_can_bypass"] = "never"
        self.detail.pop("bypass_actors")
        code, report = self.run_main()
        self.assertEqual((code, report["status"]), (2, "unavailable"))
