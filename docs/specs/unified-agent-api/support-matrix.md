# Support Matrix Spec — Unified Agent API

Status: Approved
Approved (UTC): 2026-04-15
Canonical location: `docs/specs/unified-agent-api/support-matrix.md`

This document is the authoritative contract for support publication semantics in the Unified Agent API spec set.

Normative language: this spec uses RFC 2119 requirement keywords (`MUST`, `MUST NOT`, `SHOULD`).

## Purpose

This spec defines the meaning of published support truth for the Unified Agent API documentation layer.
It separates support publication from capability advertising so the two concerns do not drift together.

## Support layers

Support publication MUST distinguish the following four layers:

- `manifest support`: what the committed CLI manifest evidence says about a target or version.
- `backend support`: what the agent-specific wrapper/backend crate can safely support based on its implementation and manifest inputs.
- `UAA unified support`: what the Unified Agent API can claim as a deterministic cross-agent support statement.
- `passthrough visibility`: backend-specific surface area that remains visible but is not promoted into unified support.

These layers MUST NOT be conflated with workflow status fields, pointer files, or generated overview artifacts.

For onboarding and publication purposes, backend support is crate-first:

- a new agent MAY have committed manifest evidence before any wrapper crate exists
- manifest evidence alone MUST NOT be promoted into backend support
- backend support MUST remain `unsupported` until crate-owned wrapper evidence exists for that target

## Publication targets

The phase-1 publication targets are:

- `cli_manifests/support_matrix/current.json`
- `docs/specs/unified-agent-api/support-matrix.md`

The JSON artifact is the machine-readable publication surface.
This Markdown document is the normative human-readable projection.

Both publication targets MUST describe the same support model.
If they disagree, the repository is in an invalid publication state.

## Support debt inventory

Published support truth for enrolled automated-maintenance agents MUST stay aligned with:

- `docs/specs/unified-agent-api/non-tui-support-debt.md`

That inventory is the machine-checkable baseline for temporary non-TUI blockers and preexisting
unsupported surface. Publication rules:

- support publication MUST NOT normalize deliberate non-TUI unsupported posture as a permanent
  steady-state note
- any remaining enrolled non-TUI caveat MUST point to a concrete debt-inventory row or a concrete
  external blocker that would also qualify for the maintenance-request deferral taxonomy
- `evidence_notes` MAY explain partial support, but MUST NOT become a shadow debt ledger

## Target-first primacy

Support truth MUST be target-scoped first.
Per-target rows are the primary publication unit.
Per-version summaries, if present elsewhere in the repository, MUST be treated as projections derived from those rows.

Support publication MUST preserve these distinctions:

- a target can be supported even when another target is not.
- a version summary MUST NOT collapse partial target support into a version-global claim.
- pointer state MAY inform publication, but pointer state alone is not support truth.

## Shared support row model

Both publication targets MUST be derived in a single pass from one shared support row model.
Each published row MUST describe exactly one `(agent, version, target)` tuple.
Publication MUST contain exactly one row for every `(agent, version, target)` tuple implied by the committed root set, each root's `current.json.expected_targets`, and each root's committed `versions/*.json` metadata, and for every tuple that [Support depth](#support-depth) rule 4 implies.

The publication row set is exact:

- omitting an implied tuple is invalid publication state
- duplicating a tuple is invalid publication state
- publishing a tuple implied neither by committed manifest metadata nor by Support depth rule 4 is invalid publication state

The canonical row field order is:

- `agent`
- `version`
- `target`
- `manifest_support`
- `backend_support`
- `uaa_support`
- `pointer_promotion`
- `evidence_notes`

These fields have the following meanings:

- `agent`: the manifest-root identifier whose committed evidence produced the row.
- `version`: the semantic version associated with the committed version metadata and reports.
- `target`: the root-native target identifier for the published row.
- `manifest_support`: the support state claimed by committed manifest evidence for that target.
- `backend_support`: the backend support state derived from implementation and manifest inputs for that target.
- `uaa_support`: the Unified Agent API support state published for that target after applying the support semantics in this spec.
- `pointer_promotion`: the pointer-derived promotion posture relevant to the row's target.
- `evidence_notes`: deterministic notes that explain intentional partial support or other non-contradictory caveats grounded in committed evidence.

For phase 1, `backend_support` is specifically the support posture proven by the agent-specific wrapper crate and the committed wrapper-derived reports under `cli_manifests/<agent>/reports/**`.
A manifest root without wrapper-derived report evidence MUST publish `backend_support` as `unsupported`.

The shared row model MUST preserve target-scoped truth even when multiple rows share the same version.
Publication code MUST NOT collapse multiple target rows into one version-global support claim.

The canonical row ordering MUST be deterministic:

- rows MUST sort by `agent` ascending
- within an agent, rows MUST sort by `target` ascending
- within an `(agent, target)` grouping, rows MUST sort by semantic `version` descending

`evidence_notes` rules are:

- notes MUST be derived from committed evidence and MUST NOT be speculative
- notes MAY explain intentional partial support, passthrough visibility, or other non-contradictory caveats visible in committed evidence
- notes MUST NOT redefine `validated` or `supported`, and MUST NOT stand in for contradiction policy
- for enrolled automated-maintenance agents, notes MUST NOT be the only place a non-TUI blocker is
  recorded; the blocker MUST also exist in `non-tui-support-debt.md`
- when no such caveat exists, publication MUST treat `evidence_notes` as empty rather than inventing explanatory prose

## Markdown projection boundary

`docs/specs/unified-agent-api/support-matrix.md` is the human-readable Markdown projection of the shared support row model.
It MUST render the same support truth as `cli_manifests/support_matrix/current.json`.

The Markdown projection MAY:

- group rows for readability
- add stable headings and table structure
- restate this spec's already-approved semantics

The Markdown projection MUST NOT:

- derive support truth independently from manifest roots
- introduce row fields or support states that are absent from the shared row model
- collapse target-scoped rows into version-global claims
- become a second mutable support ledger separate from the JSON artifact

## Authority rules

Published support rows MUST be derived from committed repository evidence.

For this spec set:

- manifest evidence is authoritative for manifest support.
- backend implementation evidence is authoritative for backend support.
- Unified Agent API publication text is authoritative for unified support semantics.
- passthrough visibility MUST remain explicit when a backend exposes behavior that is not part of unified support.

For phase 1, backend implementation evidence means wrapper-crate-owned evidence materialized into committed coverage reports.
Manifest metadata by itself MUST NOT be treated as backend support evidence.

The following MUST remain separate from published support truth:

- `validated` and `supported` status fields in version metadata
- generated capability inventory
- runtime backend capability checks

## Neutral root intake

The support-matrix pipeline MUST consume committed evidence from each agent root through one neutral root-intake contract.

For phase 1, that intake contract MUST be limited to these evidence categories under `cli_manifests/<agent>/`:

- `versions/*.json` version metadata
- `pointers/latest_supported/*.txt` and `pointers/latest_validated/*.txt`
- `current.json`
- `reports/**`

This intake contract MUST remain shape-driven rather than agent-name-driven:

- the pipeline MUST reason about root-local evidence categories and paths, not special-case Codex or Claude by name inside shared intake logic.
- the contract MAY preserve root-native target identifiers as loaded evidence; later derivation decides how publication rows compare or project them.
- the contract MUST NOT introduce a second support evidence store outside the committed manifest roots.

This intake contract governs evidence loading only. It MUST NOT change publication targets, support-layer meanings, or the distinction between `validated` and `supported`.

## Validated versus supported

`validated` and `supported` are distinct workflow states.

- `validated` means a version passed the validation matrix and is promotion-grade for the version pointer flow.
- `supported` means wrapper coverage satisfies the stronger support policy for the version and target surface.

A version MAY be manifest-supported before it is backend-supported.
A version MAY be backend-supported before it is promoted into UAA unified support.

The repository MUST NOT treat `validated` as equivalent to `supported`.
The repository MUST NOT treat workflow status as a published support row.
The repository MUST NOT use workflow status as a substitute for target-scoped support evidence.

## Separation from the capability matrix

The support matrix MUST remain separate from `docs/specs/unified-agent-api/capability-matrix.md`.

- The capability matrix documents backend capability advertising.
- The support matrix documents published support truth.
- The two artifacts MAY share source evidence, but they MUST NOT share meaning.
- A change to one artifact MUST NOT be assumed to update the other.

If a reader needs backend capability coverage, they SHOULD use the capability matrix.
If a reader needs published support truth, they MUST use the support matrix.

## Support depth

The [support-depth contract](../support-depth-contract.md) owns the rules for support depth: what a
depth record states, when a result is published as `verified` or as `unverified`, when a promise is
qualified and a capability depth-qualified, and which changes to a published row need depth
admission. This section states only what this spec owns: which rows carry depth facts, where those
facts are read from, what such a row states, how its `uaa_support` is derived, and the revision of
the JSON artifact that carries them. It uses that contract's terms and redefines none of them.

Rules:

1. A row is **depth-enrolled** when, in the tree being published, either of these holds: the depth
   record of the row's agent and version covers an invocation mode on the row's target, or the
   agent's registry entry declares a depth enrollment of the row's version that lists the row's
   target. Every other row is a **row without depth facts**. It keeps the fields, the meanings and
   the derivation it has under revision 1 of the JSON artifact, and it carries no marker.
2. Whether a row is depth-enrolled is a matter of scope and is read as rule 1 states. The depth
   facts a row states are read from depth records. A depth record is committed evidence under
   `reports/**`, which [Neutral root intake](#neutral-root-intake) already lists, and this section
   adds no evidence category. Publication MUST NOT decide a result, a qualification or a
   capability's depth qualification from the generated capability inventory, from a backend's
   advertised capability set, from a registry declaration, from a working file or from the
   lifecycle record. A capability id reaches a row only through the capability mappings of the
   row's depth record. Where the support-depth contract has a published result depend on evidence
   the record binds, publication reads that evidence to establish its content identity and for
   nothing else. Such a file may lie outside the intake categories. Reading it for its content
   identity loads no support evidence, and it is the one evidence read this section makes outside
   those categories.
3. A depth record is invalid publication state when it cannot be read, states a schema revision other than the current one or does not follow
   Annex B of the support-depth contract. Publication MUST fail. It MUST NOT publish that
   version's rows as rows without depth facts.
4. A target that a version's depth record covers implies a row for that agent, version and
   target, whether or not the version has committed version metadata and whether or not
   `current.json.expected_targets` still lists the target. For a version that has committed
   version metadata, a target that a registry declaration of the version lists implies one as
   well. These rows extend the row set of
   [Shared support row model](#shared-support-row-model), and on them:
   - a row whose version has no committed version metadata states `manifest_support` as
     `unsupported`, derives `backend_support` and its evidence notes as for any row, which gives
     `unsupported` and no report note where there is no coverage report for the target, and the
     note that the current root snapshot omits the target where the version is the one that
     snapshot records and it has no input for the target, and derives `uaa_support` from them.
     Its depth facts state the scope as the support-depth contract requires, which for
     obligations not yet frozen is insufficient depth; and
   - `pointer_promotion` is derived from the target's pointer files as it is for an expected
     target, whether or not `expected_targets` lists the target, and a target with no pointer
     file has no pointer.
5. In revision 2 of the JSON artifact the row model includes, for a depth-enrolled row and
   its target:
   - each promise of the record's selection that serves a covered mode on the target, with every
     obligation of that promise and the obligation's published result;
   - for each such promise, whether it is published as qualified, and each outcome that applies to
     it among those the support-depth contract's Publication section requires reports to keep
     distinguishable. More than one of them can apply to a promise, and it can be that none does.
     The qualified forwarding outcome is stated only for a promise that is published as qualified;
   - each covered mode that the record's policy excludes, as a mode exclusion with the published
     result of its obligation; and
   - each capability that the record's mappings claim, and whether it is published as
     depth-qualified for the target.

   The support-depth contract's record invariants and depth admission predicate decide each of
   these values, and this spec adds no case to them. The JSON artifact and the Markdown projection
   both state every obligation's result. That contract says what may not stand in for them. A
   depth-enrolled row for which no record states anything yet, because no generation has frozen
   its policy for the row's target, states that it is depth-enrolled and that its obligations are
   not yet frozen, which that contract reports as insufficient depth.
6. For a depth-enrolled row whose record claims at least one capability, `uaa_support` is derived
   as it is for a row without depth facts, with one further condition: the row is `supported` only
   when, in addition, every capability the record claims is published as depth-qualified for the
   row's target. Where that derivation yields `supported` and the condition does not hold, the row
   is `partial`. Depth facts never raise `uaa_support` above what that derivation yields, and they
   lower no state other than `supported`. A capability the record does not claim is not assessed,
   and the state says nothing about it. Every other depth-enrolled row derives `uaa_support` as a
   row without depth facts does, and every other field of every row keeps its derivation.
7. A change that makes a depth-enrolled row `supported` because a capability comes to be published
   as depth-qualified is part of that publication. The support-depth contract makes it an
   acceptance effect and governs it. This spec adds no condition of its own.
8. `evidence_notes` MUST NOT carry a depth fact, and authorized debt stays where
   [Support debt inventory](#support-debt-inventory) puts it. Neither is a second place for the
   facts of rule 5.
9. `schema_version` 1 of the JSON artifact is the row model of the sections above. The facts of
   rule 5 and the derivation of rule 6 belong to revision 2, which
   [Revision 2 of the JSON artifact](#revision-2-of-the-json-artifact) defines. That revision is
   an executable schema revision of this spec, among those the support-depth contract's path
   enablement requires to be adopted. In it, the exact row set and the row model are those of
   the sections above as rules 4 and 5 extend them, and a row without depth facts has exactly
   the fields and the values it has in revision 1. A reader of the artifact MUST require the
   revision it supports, and it MUST NOT read an artifact of another revision as one that holds
   no depth-enrolled row.
10. [Separation from the capability matrix](#separation-from-the-capability-matrix) holds for
    depth-enrolled rows as well. A row's capability-level fact says whether a capability is
    depth-qualified. It never says that a backend advertises the capability, and the capability
    matrix never says that a capability is depth-qualified. A change to one artifact is still not
    assumed to update the other.

The support-depth contract's minimum machinery rule requires the failure a new field or mechanism
prevents to be named. Without the row facts of rule 5, the `supported` state of a depth-enrolled
row would not say which capabilities were assessed, and that contract requires a qualified subset
to be named by its exact scope. Without the condition of rule 6, a row would stay `supported` on
name coverage alone while a capability its depth enrollment claims is unverified. Without rule 4,
removing a target from `expected_targets` would remove a depth-enrolled row, and with it the
published results of that target, and a depth record written before its version's metadata, or
kept after the metadata is removed, would be published nowhere, although the support-depth
contract's Bindings rule 7 has its scope reported as insufficient depth. Without the revision of rule 9, a reader written for revision 1
would take a `uaa_support` that depends on depth facts for one derived from manifest and backend
support alone.

### Revision 2 of the JSON artifact

Revision 2 writes `schema_version` 2. A depth-enrolled row has one member after the eight of
revision 1, `depth`, and a row without depth facts has none. The artifact is written as revision 2
when any row carries depth facts and as revision 1 otherwise, so the two agree on every row
without depth facts. A reader that supports revision 2 therefore also reads revision 1, as an
artifact in which no row carries depth facts. Every object below takes exactly the
members listed, and a reader MUST reject any other.

`depth`:

| Member | Value |
| --- | --- |
| `obligations_frozen` | `true` when the version's depth record selects a mode on the row's target and states an obligations part frozen for that target, otherwise `false`. A row whose version has no depth record has `false` and the three lists `[]`. A row whose record covers no mode on its target has no promises and no mode exclusions, and still lists the record's capabilities. |
| `promises` | One entry for each operation of the record's selection that is not a mode exclusion and serves a mode selected on the row's target, in ascending order of `operation`. |
| `mode_exclusions` | One `{ "mode", "operation", "result" }` for each mode selected on the row's target that a mode exclusion serves: the mode's selector, the exclusion's operation id and the published result of its `EX1` obligation. In ascending order of `operation`. |
| `capabilities` | One `{ "id", "depth_qualified" }` for each capability the record's mappings claim, in ascending order of `id`. |

A promise:

| Member | Value |
| --- | --- |
| `operation` | The operation id. |
| `templates` | The obligation templates its declaration selects, in the declaration's order. |
| `qualified` | Whether the promise is published as qualified. |
| `outcomes` | Each of `"qualified_forwarding"`, `"insufficient_depth"`, `"authorized_debt"` and `"classification_required"` that applies, in that order. |
| `obligations` | `[]` while `obligations_frozen` is `false`. Otherwise one `{ "id", "result" }` for each obligation id the obligations part states for the operation, which is the set the policy part resolves for it, in the order `R1`, `V1`, `G1`, `E1`, `A1`, `X1` to `X4`, `OUT1` to `OUT4`, `LC1` to `LC4`, `FX1`, `S1`, `N1`, `B1`, `MCP1`, `EX1`, then one `{ "capability", "result" }` for each capability mapping that names the operation, its `M` obligation, in ascending order of `capability`. |

A `result` is `"verified"`, `"unverified"`, `"failed"` or `"not_applicable"`, the published result
that the support-depth contract's record invariant 3 decides:

1. A result is `unverified` unless the record's obligations part is frozen for the row's target,
   its execution part references the policy and obligations identities that the record states,
   and it states a result for the obligation on the row's target.
2. A stated `verified` result is `unverified` unless it binds at least one file and each file it
   binds is in the revision with the content identity the record states.
3. A stated `not_applicable` result is `unverified` unless the promise's `not_applicable_permitted`
   names the obligation. No promise permits it for an `M` obligation.
4. Any other stated result is published as stated.

The other values:

- A promise is qualified when `obligations_frozen` is `true`, every obligation in its
  `obligations` is `verified` or `not_applicable`, no unit of its operation is
  `classification_required`, and the record lists an acceptance entry made for what the record
  states now, as the support-depth contract's record invariant 4 requires.
- `qualified_forwarding` applies when the promise is qualified, its declaration states
  `forwarding = true`, and every obligation in its `obligations` is `verified`. A permitted
  `not_applicable` result qualifies a promise but not as qualified forwarding.
- `insufficient_depth` applies when `obligations_frozen` is `false` or an obligation's result is
  `unverified` or `failed`. `classification_required` applies when the obligations part lists a
  unit of the operation as `classification_required`. `authorized_debt` applies when a debt row in
  force authorizes the record's version, lists the row's target and has as its name identity a
  surface the obligations part assigns to the operation. The rows in force are the policy part's
  `debt_baseline`, in which, while the execution part references the identities the record
  states, each row it grants is replaced by its grant and each row it retires is removed.
- A capability is depth-qualified when every operation its mapping names is a promise of the row
  that is qualified. Each such operation carries the capability's `M` obligation, so the
  shared mapping rule's requirement that one of them be `verified` is then met.
- A mode exclusion is stated by `mode_exclusions`, a row that is not depth-enrolled by the
  absence of `depth`, and an unresolved depth enrollment by the failure of publication.

Publication MUST fail when the record's obligations part is frozen for the row's target and, for
an operation that serves a mode selected on the target, states no obligation set or one other than
the set the policy part resolves: its `base` and the obligations its `templates` state for the
operation's templates, or for a mode exclusion those of `EXCLUDED` alone. Such a row would have no
truthful `obligations`, and a promise could qualify on a shorter list than its own.

These values are what the record and the evidence it binds decide. Whether a route may publish a
change to them is depth admission, which the support-depth contract owns: in particular, a result
that its reuse and invalidation rules invalidate through a dependency outside the bound evidence
is not visible here.

The Markdown projection states the same facts. After an agent's table, each depth-enrolled row of
that agent has a level-four heading `Depth facts:` followed by the agent, the version and the
target, each in backticks, then a line
`Obligations frozen: yes` or `no`, and, for each list that is not empty, a table: promises with
their templates, `qualified`, outcomes and every obligation's result; mode exclusions with their
operation and `EX1` result; and capabilities with `depth_qualified`.

### Present behavior

The generator writes revision 2 when a row carries depth facts. No manifest root holds a depth
record, so the committed artifact is revision 1. Today:

- The generator reads each published root's `reports/<version>/depth-record.json` through Annex
  B's reader (`crates/xtask/src/depth_record.rs`). It fails publication on a record that does not
  read; on one in a root whose `RULES.json` does not name
  `<manifest root>/reports/<version>/depth-record.json` as `storage.committed.reports.depth_record`,
  which is how a root adopts Annex B (aider and gemini_cli have no `RULES.json` and adopt nothing);
  and on one in a registry root the support matrix does not publish.
  It derives rule 4's rows from what a record covers and reads pointer files for those targets
  whether or not `expected_targets` lists them. It derives each row's depth facts and applies
  rule 6 in `crates/xtask/src/support_matrix/depth.rs`. A bound file is in the revision when git
  tracks a regular file at its path, and only such a file is read, for its SHA-256 only. An
  untracked or ignored file, git's own files and a symlink are not in the revision whatever they
  hold, so a result bound to one is `unverified`, and evidence a change adds counts once it is
  staged. Where a record binds evidence and git cannot list the files it tracks in the workspace,
  because it is not a git checkout or git cannot run, publication fails.
- It reads no registry declaration: the registry loader refuses a `support_depth` table until
  route wiring admits one. So no row is depth-enrolled by declaration, and rule 4 implies no row
  from a declaration.
- `support-matrix --check` requires the committed artifacts to equal a fresh generation. The
  consistency check behind it and behind `manifest-validate` compares every published row with
  the derived one, depth facts included (`SUPPORT_MATRIX_DEPTH_MISMATCH`). So a change to a record,
  or to a file it binds, regenerates the publication in the same change.
- Every reader of the JSON artifact requires the revision its rows are written in
  (`SupportMatrixArtifact::revision_error`): `manifest-validate` and the drift check's publication
  comparison. The drift check renders the Markdown it compares with the generator's renderer. The
  `markdown_support_claim` governance check compares a claim with the derived rows, which carry
  rule 6.
- The generator decides what a record decides. Whether a route may publish a change it derives is
  depth admission, which no route evaluates yet.

## Verification checklist

Before downstream work consumes this contract, reviewers MUST confirm:

- the canonical support publication targets are named exactly once and without ambiguity.
- the four support layers have distinct meanings and no overlap with workflow metadata.
- target-scoped rows are described as primary and per-version summaries as derived projections.
- the neutral root-intake contract is limited to committed root evidence and does not introduce agent-name-specific loading semantics.
- backend support is explicitly crate-first and cannot be claimed from manifest metadata alone.
- `validated` is not treated as equivalent to `supported`.
- the support matrix is explicitly separate from the capability matrix.
- the spec is sufficient for downstream implementation without reopening authority or output-path decisions.

## Change control

Any future update to support publication semantics MUST update this spec first.
If the publication model changes, the README index and any dependent publication docs MUST be updated in the same change.

## Published support matrix

This section is generated by `cargo run -p xtask -- support-matrix`.
Do not edit this section by hand.

<!-- support-matrix-published:start -->
### `aider`

| agent | version | target | manifest_support | backend_support | uaa_support | pointer_promotion | evidence_notes |
|---|---|---|---|---|---|---|---|
| `aider` | `0.0.0` | `darwin-arm64` | `supported` | `unsupported` | `unsupported` | `latest_supported_and_validated` | — |

### `claude_code`

| agent | version | target | manifest_support | backend_support | uaa_support | pointer_promotion | evidence_notes |
|---|---|---|---|---|---|---|---|
| `claude_code` | `2.1.274` | `darwin-arm64` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `claude_code` | `2.1.29` | `darwin-arm64` | `supported` | `supported` | `supported` | `none` | — |
| `claude_code` | `2.1.274` | `linux-x64` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `claude_code` | `2.1.29` | `linux-x64` | `supported` | `supported` | `supported` | `none` | — |
| `claude_code` | `2.1.274` | `win32-x64` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `claude_code` | `2.1.29` | `win32-x64` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support |

### `codex`

| agent | version | target | manifest_support | backend_support | uaa_support | pointer_promotion | evidence_notes |
|---|---|---|---|---|---|---|---|
| `codex` | `0.156.1` | `aarch64-apple-darwin` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.155.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.144.6` | `aarch64-apple-darwin` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.129.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.125.0` | `aarch64-apple-darwin` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.97.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.92.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.91.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.61.0` | `aarch64-apple-darwin` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.156.1` | `aarch64-unknown-linux-musl` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.155.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.144.6` | `aarch64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.129.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.125.0` | `aarch64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.97.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.92.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.91.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.61.0` | `aarch64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.156.1` | `x86_64-pc-windows-msvc` | `supported` | `partial` | `partial` | `latest_supported_and_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.155.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.144.6` | `x86_64-pc-windows-msvc` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.129.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.125.0` | `x86_64-pc-windows-msvc` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.97.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.92.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.91.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.61.0` | `x86_64-pc-windows-msvc` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `codex` | `0.156.1` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `latest_validated` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.155.0` | `x86_64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.144.6` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes passthrough surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.129.0` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.125.0` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.97.0` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.92.0` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.91.0` | `x86_64-unknown-linux-musl` | `unsupported` | `unsupported` | `unsupported` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |
| `codex` | `0.61.0` | `x86_64-unknown-linux-musl` | `supported` | `partial` | `partial` | `none` | backend report includes intentionally unsupported surface outside unified support; backend report includes backend-only surface outside unified support |

#### Depth facts: `codex` `0.156.1` `x86_64-unknown-linux-musl`

Obligations frozen: no

| promise | templates | qualified | outcomes | obligations |
|---|---|---|---|---|
| `exec` | `CORE` | no | insufficient_depth | — |

### `gemini_cli`

| agent | version | target | manifest_support | backend_support | uaa_support | pointer_promotion | evidence_notes |
|---|---|---|---|---|---|---|---|
| `gemini_cli` | `0.38.2` | `darwin-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |

### `opencode`

| agent | version | target | manifest_support | backend_support | uaa_support | pointer_promotion | evidence_notes |
|---|---|---|---|---|---|---|---|
| `opencode` | `1.14.47` | `darwin-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `darwin-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | current root snapshot omits this target |
| `opencode` | `1.4.9` | `darwin-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.14.47` | `darwin-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `darwin-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | current root snapshot omits this target |
| `opencode` | `1.4.9` | `darwin-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.14.47` | `linux-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `linux-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | current root snapshot omits this target |
| `opencode` | `1.4.9` | `linux-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.14.47` | `linux-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `linux-x64` | `supported` | `unsupported` | `unsupported` | `latest_validated` | — |
| `opencode` | `1.4.9` | `linux-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.14.47` | `win32-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `win32-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | current root snapshot omits this target |
| `opencode` | `1.4.9` | `win32-arm64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.14.47` | `win32-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
| `opencode` | `1.4.11` | `win32-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | current root snapshot omits this target |
| `opencode` | `1.4.9` | `win32-x64` | `unsupported` | `unsupported` | `unsupported` | `none` | — |
<!-- support-matrix-published:end -->
