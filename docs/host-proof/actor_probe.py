"""Negative host-policy tests, restricted to the disposable proof repository."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "atomize-hq/unified-agent-api-integration-proof-20261021"
assert os.environ["GITHUB_REPOSITORY"] == REPO
credential = os.environ["PROOF_CREDENTIAL"]
token = os.environ["PROOF_PAT"] if credential == "pat" else os.environ["GH_TOKEN"]
transport_only = os.environ.get("PROOF_TRANSPORT_ONLY") == "true"
report = {"scope": "ref-transports-only" if transport_only else "ref-transports-and-direct-merge", "repository": REPO, "credential": credential, "run_id": os.environ["GITHUB_RUN_ID"],
          "workflow_source": os.environ["GITHUB_SHA"], "attempts": []}


def api(method, path, data=None, *, read_checks=False):
    assert path in ("user", "graphql") or path.startswith(f"repos/{REPO}/")
    if read_checks:
        assert method == "GET" and path.startswith(f"repos/{REPO}/commits/") and path.endswith("/check-runs?per_page=100")
    request_token = os.environ["GH_TOKEN"] if read_checks else token
    request = urllib.request.Request("https://api.github.com/" + path, method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Authorization": "Bearer " + request_token, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2026-03-10", "Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    content = response.read().decode()
    body = json.loads(content) if content else None
    return response.status, body


def get(path):
    status, body = api("GET", path)
    assert status == 200, f"GET failed ({status})"
    return body


prefix = f"repos/{REPO}"

def refused(name, method, path, data, before):
    status, body = api(method, path, data)
    after = get(prefix + "/git/ref/heads/staging")["object"]["sha"]
    text = json.dumps(body).lower()
    policy_reason = any(word in text for word in ("repository rule", "protected branch", "merge queue"))
    if name == "direct-merge-api":
        policy_reason = "merge queue" in text
    proved = status in (403, 405, 409, 422) and after == before and policy_reason
    report["attempts"].append(dict(name=name, status=status, body=body, before=before,
                                   after=after, policy_refusal_observed=proved))
    if after != before:
        raise AssertionError("staging changed during a supposed refused operation")
    return proved


try:
    if credential == "pat":
        assert token and token.startswith(("ghp_", "github_pat_")), "PAT unavailable or wrong credential class"
        report["principal"] = get("user")["login"]
        report["token_class"] = "fine-grained PAT" if token.startswith("github_pat_") else "classic PAT"
    elif credential == "human_oauth":
        assert token and token.startswith("gho_"), "human OAuth token unavailable or wrong credential class"
        report["principal"] = get("user")["login"]
        report["token_class"] = "human OAuth user token"
    else:
        assert credential == "github_token" and token, "workflow token unavailable"
        report["token_class"] = "workflow GITHUB_TOKEN (contents and pull requests write)"
    before = get(prefix + "/git/ref/heads/staging")["object"]["sha"]
    if not transport_only:
        number = int(os.environ["PROOF_PR"])
        pr = get(prefix + f"/pulls/{number}")
        assert pr["state"] == "open" and not pr["draft"] and pr["mergeable"] is True
        assert pr["base"]["repo"]["full_name"] == REPO and pr["base"]["ref"] == "staging"
        assert pr["head"]["repo"]["full_name"] == REPO
        head = pr["head"]["sha"]
        ancestry = get(prefix + f"/compare/{before}...{head}")
        assert ancestry["merge_base_commit"]["sha"] == before, "staging is not contained in PR head"
        # Fine-grained PAT setup does not expose Checks. Observe eligibility with
        # the workflow token; every mutation and the endpoint control still use PAT.
        status, checks = api("GET", prefix + f"/commits/{head}/check-runs?per_page=100", read_checks=True)
        assert status == 200, "workflow check-reader permission unavailable"
        report["check_reader"] = "workflow GITHUB_TOKEN; observation only"
        assert checks["total_count"] <= 100, "check pagination required"
        desired = json.loads(Path("docs/agents/lifecycle/staging-integration-ruleset.json").read_text())
        required = next(rule for rule in desired["rules"] if rule["type"] == "required_status_checks")["parameters"]["required_status_checks"]
        observed = []
        for required_check in required:
            matches = [check for check in checks["check_runs"] if check["name"] == required_check["context"]
                       and check["app"]["id"] == required_check["integration_id"]]
            latest = max(matches, key=lambda check: check["id"])
            assert latest["status"] == "completed" and latest["conclusion"] == "success"
            observed.append({key: latest[key] for key in ("id", "name", "head_sha", "conclusion", "details_url")})
        query = """query($number: Int!) { repository(owner: "atomize-hq", name: "unified-agent-api-integration-proof-20261021") {
          pullRequest(number: $number) { headRefOid baseRefOid state mergeQueueEntry { id } }
        } }"""
        status, result = api("POST", "graphql", {"query": query, "variables": {"number": number}})
        assert status == 200 and not result.get("errors"), "queue eligibility read unavailable"
        eligibility = result["data"]["repository"]["pullRequest"]
        # PR base metadata can retain the older event base after the branch advances.
        # Current staging is read separately above and must be an ancestor of head.
        assert eligibility["headRefOid"] == head and eligibility["state"] == "OPEN"
        assert eligibility["mergeQueueEntry"] is None
        report["direct_merge_pr"] = {"number": number, "head": head, "base": before, "pr_base_metadata": pr["base"]["sha"],
                                      "eligibility": eligibility, "required_checks": observed}
        # The caller supplies an unprotected control PR, so a successful merge proves endpoint
        # permission independently of the protected staging refusal. Never target staging here.
        control_number = int(os.environ["PROOF_CONTROL_PR"])
        control_pr = get(prefix + f"/pulls/{control_number}")
        assert control_pr["state"] == "open" and control_pr["mergeable"] is True
        assert control_pr["base"]["repo"]["full_name"] == REPO
        assert control_pr["head"]["repo"]["full_name"] == REPO
        assert control_pr["base"]["ref"].startswith("proof/control-target-")
        status, result = api("PUT", prefix + f"/pulls/{control_number}/merge",
                             {"sha": control_pr["head"]["sha"], "merge_method": "merge"})
        report["merge_endpoint_control"] = {"number": control_number, "status": status, "body": result,
                                            "base_ref": control_pr["base"]["ref"], "head": control_pr["head"]["sha"]}
        assert status == 200 and result["merged"] is True, "unprotected merge endpoint control failed"
        assert get(prefix + "/git/ref/heads/staging")["object"]["sha"] == before
    commit = get(prefix + "/git/commits/" + before)
    control = f"proof/control-{credential}-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    status, blob = api("POST", prefix + "/git/blobs", {"content": control, "encoding": "utf-8"})
    assert status == 201
    status, tree = api("POST", prefix + "/git/trees", {"base_tree": commit["tree"]["sha"], "tree": [
        {"path": "docs/host-proof/actor-attempt.txt", "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
    assert status == 201
    status, candidate = api("POST", prefix + "/git/commits", {"message": "test: isolated actor probe [skip ci]",
                                                           "tree": tree["sha"], "parents": [before]})
    assert status == 201
    status, result = api("POST", prefix + "/git/refs", {"ref": "refs/heads/" + control, "sha": candidate["sha"]})
    report["unprotected_control"] = {"status": status, "ref": control, "commit": candidate["sha"]}
    assert status == 201, "credential cannot write even an unprotected control branch"
    # A sibling with the exact current tree is a non-fast-forward target without
    # changing CI files. This isolates ref policy from workflow-edit permissions.
    status, force_candidate = api("POST", prefix + "/git/commits", {
        "message": "test: same-tree non-fast-forward probe [skip ci]",
        "tree": commit["tree"]["sha"], "parents": [commit["parents"][0]["sha"]]})
    assert status == 201 and force_candidate["sha"] != before
    assert force_candidate["tree"]["sha"] == commit["tree"]["sha"]
    status, result = api("POST", prefix + "/git/refs", {
        "ref": "refs/heads/" + control + "-force", "sha": force_candidate["sha"]})
    assert status == 201
    report["non_fast_forward_candidate"] = {
        "sha": force_candidate["sha"], "tree": force_candidate["tree"]["sha"],
        "parents": [parent["sha"] for parent in force_candidate["parents"]]}
    # Exercise Git receive-pack separately from the REST ref endpoints. Credentials
    # travel only through private child environment configuration, never a URL/argv.
    remote = f"https://github.com/{REPO}.git"
    auth = "AUTHORIZATION: basic " + base64.b64encode(("x-access-token:" + token).encode()).decode()
    git_env = {key: value for key, value in os.environ.items()
               if not key.startswith("GIT_TRACE") and not key.startswith("GIT_CONFIG_")}
    git_env.update(GIT_CONFIG_COUNT="3", GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_0="", GIT_CONFIG_KEY_1="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_1=auth, GIT_CONFIG_KEY_2="credential.helper", GIT_CONFIG_VALUE_2="",
                   GIT_TERMINAL_PROMPT="0", GIT_CURL_VERBOSE="0")
    report["git_transport"] = []

    def git_attempt(name, args, expect_success):
        operation = subprocess.run(["git", *args], env=git_env, capture_output=True, text=True, timeout=90)
        transcript = (operation.stdout + operation.stderr).replace(token, "[redacted]").replace(auth, "[redacted]").replace(auth.split()[-1], "[redacted]")
        after = get(prefix + "/git/ref/heads/staging")["object"]["sha"]
        policy_reason = "repository rule" in transcript.lower() or "protected branch" in transcript.lower()
        passed = (operation.returncode == 0 if expect_success else operation.returncode != 0 and policy_reason)
        report["git_transport"].append({"name": name, "exit": operation.returncode, "transcript": transcript,
                                         "before": before, "after": after, "expected_success": expect_success,
                                         "expected_result_observed": passed and after == before})
        assert after == before, "staging changed during Git transport probe"
        assert passed, "Git transport did not return the expected result"

    git_attempt("fetch-control-commit", ["fetch", "--no-tags", remote, "refs/heads/" + control, "refs/heads/" + control + "-force"], True)
    git_control = "refs/heads/" + control + "-git"
    git_attempt("unprotected-create", ["push", "--porcelain", remote, candidate["sha"] + ":" + git_control], True)
    git_attempt("unprotected-force", ["push", "--porcelain", "--force-with-lease=" + git_control + ":" + candidate["sha"],
                                      remote, force_candidate["sha"] + ":" + git_control], True)
    git_attempt("unprotected-delete", ["push", "--porcelain", "--force-with-lease=" + git_control + ":" + force_candidate["sha"],
                                       remote, ":" + git_control], True)
    git_attempt("unprotected-recreate", ["push", "--porcelain", remote, candidate["sha"] + ":" + git_control], True)
    git_attempt("protected-direct-push", ["push", "--porcelain", remote, candidate["sha"] + ":refs/heads/staging"], False)
    git_attempt("protected-force-push", ["push", "--porcelain", "--force-with-lease=refs/heads/staging:" + before,
                                         remote, force_candidate["sha"] + ":refs/heads/staging"], False)
    git_attempt("protected-delete", ["push", "--porcelain", "--force-with-lease=refs/heads/staging:" + before,
                                     remote, ":refs/heads/staging"], False)
    results = [refused("direct-update", "PATCH", prefix + "/git/refs/heads/staging",
                       {"sha": candidate["sha"], "force": False}, before)]
    results.append(refused("force-update", "PATCH", prefix + "/git/refs/heads/staging",
                           {"sha": force_candidate["sha"], "force": True}, before))
    results.append(refused("delete", "DELETE", prefix + "/git/refs/heads/staging", None, before))
    report["recreation"] = "not reachable after refused deletion; existing-ref errors are not recreation proof"
    if not transport_only:
        results.append(refused("direct-merge-api", "PUT", prefix + f"/pulls/{number}/merge",
                               {"sha": head, "merge_method": "merge"}, before))
    report["all_requested_policy_refusals_observed"] = all(results)
    assert all(results), "a refusal was missing or caused by something other than the tested policy"
except Exception as error:
    # Never echo credential values or HTTP request headers.
    report["error"] = str(error) if isinstance(error, AssertionError) else type(error).__name__
finally:
    Path("target").mkdir(exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True)
    Path("target/host-proof-actor.json").write_text(text + "\n")
    print(text)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("```json\n" + text + "\n```\n")
sys.exit(0 if report.get("all_requested_policy_refusals_observed") else 1)
