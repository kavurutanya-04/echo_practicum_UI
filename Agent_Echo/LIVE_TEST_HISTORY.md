# Echo live-test history: runs 15-29

Current status, 2026-10-27: runs 27-29 below tested review-v4 and all failed. The subsequent
review-v5 correction removes literal reconstruction and adds full capture/phase resumption;
it is implemented but untested by user instruction. V4's literal coverage is no longer
active; its source assessment/withholding intent remains in v5. Runs 30-32 are pending.

Reviewed 2026-10-27 (America/New_York) from the saved JSON artifacts, matching execution
logs, current implementation and dated project change records. All rows use the same
question, manager M14, Recognition comments and 2026-07-01 through 2026-09-30 scope.
Model names below are the APInex profile's recorded identifiers, not independently
verified underlying model identities. Luna = free/gpt-6-luna; DeepSeek =
free/deepseek-v4.1-flash; Gemini = free/gemini-3.8-flash.

**Change timing:** the change column describes work applied **after** the indicated
run. That run therefore does not validate the change it motivated. Every run below
predates assertion-level review-v4. Retained status is checked against the current local
code, including user changes already present before this update.

**Improvement:** comparisons are qualitative judgments of observed delivery, review
behavior and content, with execution metrics reported separately. They are not accuracy
scores or causal estimates of a change's effect. There are no human reference labels
or repeated controlled trials establishing classification accuracy. An accept status
does not prove semantic correctness. Successful API calls mean adapter completion, not
accepted analysis; durations include request pacing and retries.

| Run / artifact | Recorded model | Observed delivery; successful calls; duration | Change applied after this run | Still retained? | Observed difference from preceding run |
| --- | --- | --- | --- | --- | --- |
| [15](reports/apinex_prueba_vanilla_15.json) | Luna | Failed; 13 calls; 248.766 s. Classification 13/13; support never completed. | Normalize optional review annotations; preserve invalid current-correction closures as pending; trusted scope in completeness; recovery within four drafts, with both reviews required. | Yes. Current v4 adds assertion review while retaining recovery and conservative legacy handling. | No delivery improvement versus run 14, which also failed. More precise diagnostics exposed the actual schema/lifecycle failures. The run-15 draft still omitted requested literal examples. |
| [16](reports/apinex_prueba_vanilla_16.json) | Luna | Complete; 15 calls; 291.531 s; two drafts. | Shared versioned sentiment rubric v2; literal request grounding for omissions; full released-group text/label/reason input to support; reassessment/challenge guidance. | Partly: full context, grounding and version history remain; active rubric v2 was replaced by v3 after run 17. | Clear delivery recovery: a verified package with literal examples was released. Semantic improvement unproven: review introduced incorrect reasoning about coverage/indeterminate and unnecessary requirements. |
| [17](reports/apinex_prueba_vanilla_17.json) | Luna | Complete; 9 calls; 171.109 s; one draft. | General rubric v3 and removal of case-specific live labeling guidance. | Yes. V1/v2 remain historical rubric identities. | More efficient than 16: 15 to 9 calls, two drafts to one. Output still had attribution limits and three team questions rather than the requested two; classifier quality unvalidated. |
| [18](reports/apinex_prueba_vanilla_18.json) | Luna | Complete; 27 calls; 530.453 s; four drafts. | Omit inactive numeric/correction assessment fields from each contextual support schema, preserving required active assessments. | Yes. V3/v4 use keyed correction judgments in place of the old state-list field where obligations exist. | No clear content gain versus 17; limited pattern synthesis and three times the calls. Demonstrated recovery after nine invalid support submissions across the first three drafts. |
| [19](reports/apinex_prueba_vanilla_19.json) | Luna | Partial; 23 calls; 451.875 s; four drafts. | Preserve explicitly supplied strict tool flags at the Chat adapter boundary; minimal/synthetic transport checks followed. | Yes. | Delivery regressed from complete to partial. Inactive fields were handled, but support/schema failures and growing correction obligations persisted. |
| [20](reports/apinex_prueba_vanilla_20.json) | Luna | Failed; 11 calls; 330.954 s; one draft. | Set parallel_tool_calls=false for one required Chat tool; add content-free rationale type/length diagnostics. | Yes. | Delivery regressed from partial to no released answer. Completeness first rejected a rationale and then received duplicate tool calls; support did not run. Fewer calls reflect early failure, not efficiency improvement. |
| [21](reports/apinex_prueba_vanilla_21.json) | Luna | Partial; 26 calls; 561.875 s; four drafts. | Review-v3 code-keyed mandatory/addressed judgments; derive correction states in code; remove duplicate obligation text from input. | Yes within review-v4. New assertions add evidence granularity without replacing correction judgments. | Recovered some delivery versus 20: all completeness phases completed on first attempts, with no duplicate calls. Only two support reviews completed; false/redundant objections still blocked completion. |
| [22](reports/apinex_prueba_vanilla_22.json) | Luna | Complete; 10 calls; 201.672 s; one draft. | Distinguish requested questions/counts from supplementary actions; preserve requested work and reason actions from findings. | Yes. | Operational improvement versus 21: complete in one draft and 10 versus 26 calls. Content remained incomplete: the reviewer accepted two actions in place of the requested team questions. |
| [23](reports/apinex_prueba_vanilla_23.json) | Luna | Partial; 26 calls; 562.578 s; four drafts. | Require at least one reasoned manager action for complete Original analysis; contextual policy_requirement support correction; simplify review instructions. | Yes. Action reasoning and factual premises remain distinct in v4. | Mixed: the requested two questions appeared in every draft, but delivery regressed to partial. Action content appeared then disappeared during repairs; false objections and a real unsupported attribution remained. |
| [24](reports/apinex_prueba_vanilla_24.json) | Luna | Partial; 22 calls; 499.937 s; three drafts. Released an earlier reviewed version after the newer draft failed completeness. | Additional DeepSeek/Gemini profiles were configured before runs 25/26. No separate runtime repair specifically following 24 is documented. | Profiles remain. No undocumented runtime repair is inferred. | No demonstrated answer-quality improvement versus 23. Fewer calls/time, but the prose called CMT27512 positive despite its stored mixed label. Questions were initially omitted, then restored; the newest draft remained unreviewed. |
| [25](reports/apinex_prueba_deepseek_25.json) | DeepSeek | Failed; 21 successful / 22 attempted calls; 460.954 s; one draft. Classification validated 12/13; no completed review. | No separate runtime change between 25 and 26 is documented; the next run changed the selected profile to Gemini. | DeepSeek remains an optional profile. | Delivery regressed versus 24: no released answer and incomplete classification. Nonliteral quotes, duplicate source ID, attempted partial percentages and a later connection failure were observed. Changing models prevents attributing the difference solely to system code. |
| [26](reports/apinex_prueba_gemini_26.json) | Gemini | Complete; 14 calls; 306.156 s; two drafts. Classification 13/13 and both final phases complete. | Current user-selected option B: per-assertion evidence assessments, complete textual coverage, failed-assertion withholding/repair and technical UI details; review-v4. | Implemented now. Offline checks/build passed; no live validation yet. | Clear delivery improvement versus 25: corrected missing examples and finished both reviews with fewer calls/time. Accepted prose still generalized access/workload problems from one mixed comment to both. Neither classifier accuracy nor general model superiority is established. |

## Evidence and reading limits

Additional full runs after the original 15-26 comparison:

| Run / model | Result and cost counters | Observed issue and change afterward | Comparison with preceding run |
| --- | --- | --- | --- |
| [27 / Luna](reports/apinex_prueba_vanilla_27.json) | Failed; 11 successful calls; 226.735 s; one draft; 13/13 classified, 9 positive / 2 negative / 2 mixed. | Completeness accepted; support omitted findings once then failed literal assertion coverage twice. No isolated patch before 28. | No answer released versus 26's complete Gemini answer; different models and the new v4 contract prevent attributing this solely to model quality. |
| [28 / DeepSeek](reports/apinex_prueba_deepseek_28.json) | Failed; 25 successful calls; 558.000 s; three drafts; 13/13 classified, 8 positive / 2 negative / 3 mixed. | Two support phases failed (one missing-finding submission and five literal-coverage failures); final completeness failed exact request excerpts. Last prose listed nine positive IDs against eight positive labels. No isolated patch before 29. | Classification completed unlike DeepSeek 25, but delivery still failed. More calls/time than 27; no demonstrated semantic gain. |
| [29 / Gemini](reports/apinex_prueba_gemini_29.json) | Failed; 11 successful calls; 240.875 s; one draft; 13/13 classified, 9 positive / 2 negative / 2 mixed. | Completeness accepted actions instead of requested questions; support failed literal coverage three times. Unsupported mixed-comment attribution and respondent-specific actions remained. Current v5/capture/resume update follows this run. | Fewer calls/time than 28 but still no reviewed answer. Operational regression versus Gemini 26, not evidence that its analysis was entirely wrong. |

Matching logs: [27](reports/logs/20261027_194004_ea1aa08547e2.jsonl),
[28](reports/logs/20261027_194351_3d7632003cb3.jsonl),
[29](reports/logs/20261027_195309_7ddc619fb788.jsonl).
Across these runs all stored source hashes, label coverage, aggregates and source-fact
claim replay matched. These checks do not establish semantic accuracy. Ten of twelve
support submissions failed the literal reconstruction gate; two omitted findings.
No full rejected arguments were retained by v4, so exact text mismatches cannot be
recovered. Full private capture begins with [the current update](RESUME_AND_CAPTURE.md).

The first attempt numbered 15 failed during planning with HTTP 504, one attempted call
and zero successful calls; its JSON was overwritten by the user's repeat. Its original
log remains [20261026_185354_9256ff04815d.jsonl](reports/logs/20261026_185354_9256ff04815d.jsonl).
The table's row 15 refers to the retained repeat JSON and matching log below. Run 14
is used only as run 15's preceding baseline: failed, 12 successful Luna calls, no released
answer; [artifact](reports/apinex_prueba_vanilla_14.json).

Read-only checks found identical current-source hashes and complete unique 13-comment
label coverage for every saved complete sentiment report in runs 15-24 and 26. All
structured excerpts in those reports and visible claims matched source text. Run 25
has no complete sentiment report; its retained progress records 12 validated comments
and pending CMT27512. Its top-12 supplementary retrieval omitted CMT27502, and the
unreviewed draft mixed validation status with sentiment categories and partial ratios.

Changing positive/mixed counts across runs does not establish improvement. CMT27512
varies on unchanged text, and the rubric itself changed between some runs. In run 26,
CMT27508 discusses inconsistent access/workload; CMT27511 states only frustration despite
some useful support. The published two-comment attribution is therefore broader than
its sources. The current v4 regression uses generic paired sources to check containment
of a scripted failed assertion; it does not prove a live reviewer will recognize that error.

Matching logs were located by candidate identity and successful model-response count:

| Run | Log |
| --- | --- |
| 15 | [20261026_185739_726c29abd0f2.jsonl](reports/logs/20261026_185739_726c29abd0f2.jsonl) |
| 16 | [20261026_205443_d0fc0454b26f.jsonl](reports/logs/20261026_205443_d0fc0454b26f.jsonl) |
| 17 | [20261026_231553_53fb1a92e8d9.jsonl](reports/logs/20261026_231553_53fb1a92e8d9.jsonl) |
| 18 | [20261027_004732_89cb24d6210d.jsonl](reports/logs/20261027_004732_89cb24d6210d.jsonl) |
| 19 | [20261027_032755_f2ceaabffd0a.jsonl](reports/logs/20261027_032755_f2ceaabffd0a.jsonl) |
| 20 | [20261027_062221_57dfa3d3395a.jsonl](reports/logs/20261027_062221_57dfa3d3395a.jsonl) |
| 21 | [20261027_064047_02fb051f8f2a.jsonl](reports/logs/20261027_064047_02fb051f8f2a.jsonl) |
| 22 | [20261027_145931_e5dbda537716.jsonl](reports/logs/20261027_145931_e5dbda537716.jsonl) |
| 23 | [20261027_162408_6c809611fed3.jsonl](reports/logs/20261027_162408_6c809611fed3.jsonl) |
| 24 | [20261027_170709_bd52e7cc87b7.jsonl](reports/logs/20261027_170709_bd52e7cc87b7.jsonl) |
| 25 | [20261027_183712_1c9339e6fd45.jsonl](reports/logs/20261027_183712_1c9339e6fd45.jsonl) |
| 26 | [20261027_184453_9ed9fe698167.jsonl](reports/logs/20261027_184453_9ed9fe698167.jsonl) |

Change history is grounded in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md),
[WORKFLOW_RELIABILITY.md](WORKFLOW_RELIABILITY.md) and [TESTING_AND_RAG.md](TESTING_AND_RAG.md),
then checked against current code. Saved artifacts/logs are local ignored evidence and
may be absent in another checkout. Review-v4 software validation is recorded separately
in the [testing guide](TESTING_AND_RAG.md#assertion-level-support-review-2026-10-27).
