"""Negative host-policy tests, restricted to the disposable proof repository."""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

REPO = "atomize-hq/unified-agent-api-integration-proof-20261021"
assert os.environ["GITHUB_REPOSITORY"] == REPO
credential = os.environ["PROOF_CREDENTIAL"]
token = os.environ["PROOF_PAT"] if credential == "pat" else os.environ["GH_TOKEN"]
report = {"repository": REPO, "credential": credential, "run_id": os.environ["GITHUB_RUN_ID"],
          "workflow_source": os.environ["GITHUB_SHA"], "attempts": []}


def api(method, path, data=None):
    assert path == "user" or path.startswith(f"repos/{REPO}/")
    request = urllib.request.Request("https://api.github.com/" + path, method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
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
    else:
        assert credential == "github_token" and token, "workflow token unavailable"
        report["token_class"] = "workflow GITHUB_TOKEN (contents and pull requests write)"
    before = get(prefix + "/git/ref/heads/staging")["object"]["sha"]
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
    results = [refused("direct-update", "PATCH", prefix + "/git/refs/heads/staging",
                       {"sha": candidate["sha"], "force": False}, before)]
    results.append(refused("force-update", "PATCH", prefix + "/git/refs/heads/staging",
                           {"sha": commit["parents"][0]["sha"], "force": True}, before))
    results.append(refused("delete", "DELETE", prefix + "/git/refs/heads/staging", None, before))
    report["recreation"] = "not reachable after refused deletion; existing-ref errors are not recreation proof"
    number = int(os.environ.get("PROOF_PR", "0"))
    if number:
        pr = get(prefix + f"/pulls/{number}")
        report["direct_merge_pr"] = {"number": number, "head": pr["head"]["sha"], "state": pr["state"]}
        results.append(refused("direct-merge-api", "PUT", prefix + f"/pulls/{number}/merge",
                               {"sha": pr["head"]["sha"], "merge_method": "merge"}, before))
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
