# Staging integration rules: desired configuration and verification

The [desired ruleset](staging-integration-ruleset.json) is a reviewed REST request body.
Committing it does not install protection. The [support-depth contract](../../specs/support-depth-contract.md#final-depth-admission)
remains normative; a configuration match does not establish actor authority, queue correctness
or production depth admission. Installation follows isolated host proof and explicit maintainer
authorization. Neither this document nor the comparison command supplies that authorization.

## Desired settings

Only `refs/heads/staging` is targeted, with active enforcement when installed, no exclusions or
bypass actors, deletion/force-push protection, PR delivery and merge commits. Native required
approval count remains zero; maintainer merge/enqueue authorization and agent reviews continue.

The PR parameters explicitly retain GitHub's observed empty `required_reviewers`, disabled
`dismissal_restriction` with no actors, and `require_extra_approval_for_unattributed_changes: true`.
The latter field is inferred to correspond to GitHub's default additional approval for unattributed
Copilot PRs; the REST reference does not currently describe the field. GitHub documents that the
Copilot setting has no effect when required approvals are zero. This artifact keeps that zero count
and adds no review requirement. Any later change to the count must revisit this setting together.
These are policy parameters and are compared exactly, never discarded as server metadata.
See [GitHub's approval-setting documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#additional-approval-for-unattributed-copilot-pull-requests).

Required checks are `Staging integration gate`, `Preflight`, `Capability matrix (fresh + audit)`,
and the three `Validate <agent> committed artifacts` contexts for Codex, Claude Code and OpenCode.
Each is pinned to GitHub Actions App **15368**. This is an App ID, not an installation ID.
App pinning identifies the producer, not a trusted workflow definition; authorized maintainers
still review changes to workflows, validators and this artifact.

The queue uses `ALLGREEN` and `MERGE`, one concurrent build and one PR per merge update, no minimum
wait, and a 60-minute check timeout. Strict required status checks stay enabled. Group limits do
not justify assuming a group's parent layout or validating only one member. A host rejection of
these settings requires a design correction, never a silent fallback to weaker policy.

## Read-only comparison

From the repository checkout, with Python 3.11+ and authenticated `gh`:

```bash
mkdir -p target
python3 scripts/check_staging_ruleset.py --repo atomize-hq/unified-agent-api > target/staging-ruleset-readback.json
```

For an authorized isolated test repository, pass its `OWNER/REPO` explicitly. The desired artifact
is always loaded from this checkout. The helper uses paginated REST GETs and one fixed GraphQL
**query**, submitted by HTTP POST, to read legacy branch protection. It never creates/updates a
ruleset, changes a branch, or enqueues a PR. It is a manual diagnostic, not a new CI job.

| Exit | JSON status | Meaning |
| --- | --- | --- |
| 0 | `match` | The observed configuration matches the artifact; this is not host-behavior proof. |
| 1 | `different` | Desired rules are absent/different, extra effective rules apply, or legacy protection overlaps. |
| 2 | `unavailable` | Access, malformed/incomplete readback, unsupported settings or inconsistent reads prevent comparison. |

Before installation, exit 1 with `desired repository ruleset is not installed` is expected.
Do not turn that into a passing installation check or install automatically to clear it.

The helper reads repository/inherited ruleset inventory and GitHub's effective rules for staging;
it does not implement branch-pattern matching. A match requires one named repository ruleset,
exact scope/enforcement/bypass/parameters, all desired effective rules, and no additional active
staging rules or legacy branch protection. Even a stronger overlapping policy is reported for
review rather than silently treated as equivalent. Unrelated main rules do not affect a match.
Active push rulesets require separate review and return unavailable.

Rules/contexts and other current policy arrays are compared without order sensitivity, retaining
duplicates and parameter types. Documented server metadata is ignored; missing policy fields or
unknown ruleset fields block verification. The known viewer-derived `current_user_can_bypass`
field is normalized only when it is `never`; positive or unknown values block a match. It never
substitutes for the explicit `bypass_actors` list. Full bypass visibility is required. For legacy-rule
visibility the helper requires an authenticated administrator user (`viewerPermission=ADMIN`);
limited users and GitHub App credentials with null viewer permission return unavailable. Use
existing authorized credentials; this command grants no permissions. Failed or empty readback,
including HTTP failures, must never be interpreted as an absent legacy rule. GraphQL must return
the existing staging ref and an explicit null legacy protection value for absence.

Inspect the JSON differences and observed policy. Retain its repository, observation time,
desired digest, ruleset IDs and readback with the related hosted run evidence. Separate API reads
are not atomic: rerun on inconsistent results and re-read after any configuration change. A
matching snapshot does not prove continued enforcement or rule-update serialization.

## Before any production installation

Use a separately authorized isolated GitHub repository with the same workflow, context/App
bindings and desired settings. Retain actor classes, configuration digest/rule IDs, checked
candidate/base/tree, hosted run, final parents/tree and observed accept/refuse results for:

- A valid PR through the queue to a merge commit, preserving checked tree and expected prior tip.
- A base advance after a passing PR, including an advanced base already contained in unchanged
  PR head: old success cannot authorize the new unchecked transition.
- Concurrent enqueues, reconstruction/reordering, moving base/head, failed/cancelled runs and
  retries: no stale result may update staging.
- Non-bypass human, automation PAT and ordinary-token direct/force pushes, deletion/recreation
  and direct merge API attempts outside the queue; unknown check producer and unexpected skips.

A local Git experiment or this comparator's exit 0 cannot replace those host scenarios. If exact
base/result correspondence cannot be proved, keep production depth disabled and correct the design.

Immediately before an authorized installation, obtain fresh successful observations of all six
exact check names from GitHub Actions App 15368; do not substitute any-source binding. Read both
repository/inherited rules and legacy protection, and preserve a baseline of main's configuration.
After explicit authorization, a maintainer applies the reviewed JSON using GitHub's ruleset API,
retains the returned rule ID, re-reads effective policy, runs this comparison and checks that main
is unchanged. Unavailable or differing readback blocks declaring installation verified. Queue
submission itself authorizes a later automatic merge; do not enqueue other PRs implicitly.

On a failed installation/proof, stop enqueueing and retain the actual readback. Do not add bypass
actors, exclusions or disable checks to make the comparison pass. Any rollback/restoration of
prior host settings is a separate authorized change, followed by readback and validation;
production depth stays disabled until the contract's prerequisites are met.

## API sources

- [REST rulesets, parameters and bypass visibility](https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset)
- [Effective branch rules, including inherited active rules](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)
- [GraphQL Ref branch protection](https://docs.github.com/en/graphql/reference/git#ref)
- [Viewer-derived bypass state](https://github.blog/changelog/2023-06-27-repository-rules-public-beta-updates/)
- [Repository viewer permission](https://docs.github.com/en/graphql/reference/repos#repository)

The REST reads pin API version `2026-03-10`. New schema/defaults that prevent an exact comparison
require review rather than dropping fields. No host setting is installed by this increment.
