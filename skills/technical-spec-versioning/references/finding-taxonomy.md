# Finding taxonomy

The classes of defect that recur across technical specifications, with a real example of each. Use this as a checklist during the review passes; a specification with none of these is unusual, and one with three or more needs a version.

## 1. Domain mismatch

Two correct numbers expressed in different spaces, never joined.

**Example.** A spec says ingest conforms every asset to the project rate and that the renderer never converts rate. Later it computes source consumption in *native* frames. Nothing converts one to the other. For same-rate media the domains coincide and the defect is invisible; for mixed-rate media they differ by the rate ratio.

**Detection.** For every quantity, ask *which space?* — frames/seconds/samples, native/conformed/record, per-stream/per-GPU, bytes/pixels. Then find the conversion function and check that it is named, stored and called once.

**Severity.** Usually critical, and usually silent: the output is a valid file of the wrong length.

## 2. Double rounding

A value is rounded, converted, and rounded again. Each rounding is defensible; the composition is off by one.

**Example.** 300 record frames at 2× speed consume 500.5 native frames → 501. Conforming 501 native frames to the project rate gives 600.6 → 601. The correct answer is 600. One extra rounding, one frame wrong.

**Detection.** Count the roundings along each path. A path with more than one is a bug unless the intermediate value is genuinely required.

## 3. Contract without mechanism

A promise with no artefact that makes it true.

**Examples.** "The API reports a deadline" when the job table has no deadline column. "Every op has an inverse" when three ops carry no data to invert. "Deterministic given the manifest" when the manifest does not pin thread count, encoder build or driver.

**Detection.** Grep for *guarantees, identical, always, never, exact, free, reproducible, reported, enforced*. For each, name the column, file, flag or test that makes it true. If you cannot name it, it is a finding.

## 4. Rule violated by the document's own listing

The prose states a universal rule; the DDL, schema or example in the same document breaks it.

**Example.** "Every tenant-scoped table exposes `UNIQUE (tenant_id, id)`" followed by a table listing where two of sixteen do not.

**Detection.** For every universal quantifier ("every", "all", "no tool", "each"), enumerate the members and check each. This is the highest-yield pass per minute spent, and the evidence is inside the file, so the finding cannot be argued with.

## 5. Count drift

The same quantity stated as several different numbers.

**Examples.** Seventeen, eighteen and nineteen tools. Three different preview resolutions (quarter, 480p, 0.11×) where the arithmetic implies 360p. A cost per minute that assumes one job per GPU while the capacity model packs 2.77.

**Detection.** Grep each count and each repeated figure; collect every occurrence; compare. Then check whether the *consequence* of the figure is also consistent — a corrected frame size usually invalidates a bandwidth, a stream count and a cost downstream.

## 6. Enum or schema promising an unimplemented capability

A value exists in the schema that no compiler, handler or migration supports — often because the schema was written ahead of the implementation.

**Example.** A `speed_curve` effect in the IR's effect union while the document lists speed ramps as a non-goal. A planner reading the schema will use it, because the schema is the contract.

**Detection.** Every enum value and every optional field needs an implementation and a test. Compare the schema against the dispatch table.

## 7. Claim too strong

A property stated more absolutely than the system can deliver, usually because the qualifier lives in a different section.

**Examples.** "Preview and final are pixel-identical" when the preview decodes a lossy proxy. "Frame-identical output from an identical manifest" when a hardware encoder varies across driver minor versions. "Audio is exact" when the sample count is a rounding.

**Detection.** For each strong claim, ask what varies between two runs. If anything varies that the manifest does not pin, the claim needs splitting into the part that holds and the part that does not.

## 8. Silent degradation

A flow where an unresolved condition proceeds anyway, with the deviation reported only in a log.

**Example.** A hard constraint ("no footage of the CEO") that, if the user does not answer, proceeds without the filter and reports the limitation. That is a failure of the one thing the system was asked to do.

**Detection.** For every "if unknown, then…" path, ask whether the output is still what the user asked for. If not, the path must block, not degrade.

## 9. Unenforceable policy

A rule stated as guidance that no validator applies, so its absence is indistinguishable from its satisfaction.

**Example.** A fallback expressed as prose the planner writes, rather than a closed set of operations the validator can apply. A planner that omits the prose produces a result that passes every check.

**Detection.** For each policy, ask: what code rejects a violation, and what test proves it? Guidance with no gate is not a policy.

## 10. Evidence presented as fact

A derived or assumed figure written in the same register as a measured one.

**Examples.** Encoder throughput quoted as vendor specification when it is a published indicative figure multiplied by an assumed pipeline allowance. A target presented as a result.

**Detection.** Tag every performance figure: measured, vendor-specified, derived, assumed, target. Any figure that cannot be tagged is a finding. An evidence-status column is the cheap fix and it survives scrutiny better than confident prose.

## 11. Version-boundary defect

A change that is additive in appearance but breaking in fact: a field that changes meaning, a required field added, an enum value removed.

**Detection.** For each schema change, ask whether an existing stored document still validates and still means the same thing. If not, it needs a version bump and an upgrade path, not an edit.

## 12. Worked example that does not add up

The example is the part readers check first, and it is usually hand-assembled.

**Detection.** Recompute it end to end from its own stated inputs. Check that every intermediate value is consistent with the others, that rates match the manifest, and that planned and actual positions are not mixed in one column. Then make the example generated rather than typed, so it cannot drift again.
