"""Original: coordinator with mandatory verification and bounded revision."""

from dataclasses import asdict
import json
import hashlib

from .cherry import CherryAgent
from .vanilla import VanillaAgent
from .zero_sugar import ZeroSugarAgent
from .lime import LimeAgent
from .runtime import RunBudget, Specialist, function_tool, AgentResult, AgentRunError, reject_calls
from .execution_log import record, error_summary, explain_failure
from .findings import safe_follow_up, clarification_question, unresolved_follow_up
from .policies import with_policies
from .validation import ValidationError, repair_feedback, planning_value

INSTRUCTIONS = """You are Original, Echo's coordinator. Keep ownership of the final
manager-facing answer. All answers are in English. Use ask_cherry for quantitative metrics, comparisons, recognition
counts, workload, program participation and priority records. Use ask_vanilla for anonymous
opinions, narrative contribution evidence, work descriptions and decision explanations.
The backend already supplies the authorized manager's roster and selected period. The
manager ID is not an Employee_ID; never infer missing team membership from such a lookup.
Survey text sentiment classification/counts/percentages belong to Vanilla's
analyze_survey_sentiment, which enumerates all eligible scoped comments. Request that
tool explicitly in the delegated question. Do not substitute numeric survey scores or
selected search examples. Disclose provisional model labels and comment denominators.
Counts/percentages computed from sentiment labels are Vanilla's work; they do not require
Cherry or survey-score metrics. A specialist can return declined or incomplete. Correct
an incompatible delegation, never switch to Cherry to obtain raw comments. Reuse validated
classification progress; do not restart the same task to bypass its attempt limit.
Delegate a bounded question to one or both specialists as needed, preserving the original
manager/date scope. Combine their evidence, acknowledge disagreement and missing coverage,
and explain findings with the exact source IDs returned by the tools. Top-k examples do not
measure prevalence. Synthetic associations do not establish causality or actual impact.
Recommend practical actions for human review with a measurable follow-up when warranted.
An independent verifier will check your candidate before release.
When revision feedback is supplied, correct the specified issues using the supplied evidence
or ask a specialist for additional evidence. Do not merely hide limitations.
The supplied request_deliverables are a planning checklist, not proof of completeness.
Delegate every relevant requested component to its specialist, including interpretation,
examples and limits when requested; you still own the complete final answer. A specialist's
answer and its evidence are different: usable excerpts can already be in evidence.examples
or canonical response text even when absent from the specialist's prose. Include requested
examples in the final answer using the existing literal quote field and source IDs.
Before submission, check each requested deliverable against the visible answer, not merely
against evidence collected. Use the original question to catch omissions in the checklist.
During repair, address every pending_correction explicitly while preserving other requested
content. Reuse supplied evidence for presentation omissions; ask a specialist only for
missing or disputed analysis/evidence. A concise supported synthesis can replace repeated
prose; removing a requested interpretation or example does not resolve redundancy.
Workflow examples:
- A quarterly Recognition trend with anonymous context: ask Cherry for Survey_Date,
  Team, Responses and Mean_Score, then Vanilla for supportive and critical passages.
- Cross-team work without recorded recognition: ask Cherry for distinct contribution
  counts and their denominator; ask Vanilla for documented deliverables and feedback.
- Recorded workload conflicts: Cherry compares employee/week demand with capacity;
  Vanilla retrieves the recorded priority explanations. Do not reconstruct unrecorded history.
- A request for another manager's employees or anonymous identities: do not delegate a
  scope-expanding task. Explain why the authorized evidence cannot answer it.
Output should connect finding -> cited evidence -> limitation -> proposed human action
and a measurable follow-up where warranted. Do not force both specialists when one suffices.
For a purely numerical count, do not request textual examples unless they are needed to
answer the actual question. Prefer Cherry's validated metrics for recurring calculations.
During repairs preserve supported facts, their meaning and provenance. You may reorganize,
combine qualitative evidence, rephrase and remove duplicate presentation to address review
feedback. The revised candidate is reviewed again; do not hide contrary evidence or limits.
If a chart is planned, obtain appropriately aggregated numeric rows through Cherry.
Lime is invoked only for a planned chart; ZeroSugar reviews the released package.
Do not invent numerical targets. Any suggested target must be explicitly a proposal,
not a measurement or source-derived threshold. Write short cited finding blocks so each
can be reviewed independently. If evidence is incomplete, state which requested part remains open.
Numeric task status is supplied by code in numeric_coverage. A pending/error request is
not evidence of absent data. Ask Cherry only for missing work and reuse completed results.
You coordinate these tasks and synthesize their evidence; do not repeat Cherry's calculations
or replace ZeroSugar's independent review. Cite each substantive block using [citation_id].
In live mode select numeric facts through submit_grounded_answer; synthesize text through
its interpretations field and proposed follow-up through proposals. Interpretations of
cited text or source rows use quote=null, with one or several sources; illustrative
examples require literal quotes. Narrative quantities/quantifiers receive semantic review,
not automatic rejection. Keep values, units, dates and denominators tied to evidence;
prefer catalog tables/comparisons instead of duplicating arithmetic in prose. Write
requested team questions as direct questions. Use task_type=numeric for Cherry and task_type=text
or sentiment for Vanilla. A numerical survey comparison does not require comment
classification; do not delegate sentiment to Cherry or substitute scores for text labels.
Include source tables when asked. Select code-computed differences/comparison coverage
instead of inventing terms such as improved, declined, always or every quarter in prose.
Prefer the combined survey comparison table when available; do not duplicate it with
the individual source tables. Select the relevant date-to-date changes and cross-dimension
coverage facts needed for the question rather than repeating every numeric cell.
For any source table, do not also select its individual cells unless a distinct calculation
adds needed information. Explain the main qualitative patterns, not merely a list of examples.
"""


class OriginalAgent(Specialist):
    source_grounding = True
    def __init__(self, database, scope, model_factory, mode="live", retrieval="lexical", embedding_model=None, cache_root=None, connections=None, model_call_limit=32, run_seconds=300):
        self.database, self.model_factory = database, model_factory
        self.retrieval, self.embedding_model, self.cache_root = retrieval, embedding_model, cache_root
        self.specialists, self.child_results = {}, []
        self.connection_summary = connections or {}
        self.model_call_limit, self.run_seconds = model_call_limit, run_seconds
        definitions = [function_tool(name, description, {"question": {"type": "string"},
            **({"task_type": {"type": "string", "enum": ["numeric"] if name == "ask_cherry" else ["text", "sentiment"]}}
               if mode == "live" else {})}) for name, description in (
            ("ask_cherry", "Ask Cherry a bounded question about structured evidence and calculations."),
            ("ask_vanilla", "Ask Vanilla for relevant textual evidence and a cited interpretation."))]
        super().__init__("Original", INSTRUCTIONS, model_factory("Original"), scope, definitions,
            {"ask_cherry": lambda question, task_type=None: self.delegate("Cherry", question, task_type),
             "ask_vanilla": lambda question, task_type=None: self.delegate("Vanilla", question, task_type)}, mode)
        self.all_definitions = definitions
        self.allowed_delegations = {"Cherry", "Vanilla"}
        self.declined_requests = {}

    def plan(self, question):
        self.planning_diagnostics = []
        tools = [function_tool("submit_plan", "Choose only the specialists needed by this question.", {
            "needs_numbers": {"type": "boolean"}, "needs_text": {"type": "boolean"},
            "needs_sentiment": {"type": "boolean", "description": "Full comment sentiment classification by Vanilla, including its counts/percentages; not survey ratings."},
            "include_chart": {"type": "boolean"}, "clarification_question": {"type": ["string", "null"]},
            "clarification_basis": {"type": ["object", "null"], "properties": {
                "missing_field": {"type": "string", "enum": ["manager_id", "start_date", "end_date", "metric", "task", "other"]},
                "missing_detail": {"type": "string", "minLength": 1, "maxLength": 240},
                "blocking_reason": {"type": "string", "minLength": 1, "maxLength": 500},
                "request_excerpt": {"type": "string", "minLength": 1, "maxLength": 400}},
                "required": ["missing_field", "missing_detail", "blocking_reason", "request_excerpt"],
                "additionalProperties": False,
                "description": "Null without a clarification. Otherwise identify the missing detail and quote the ambiguous part of the original request exactly."},
            "metrics": {"type": "array", "maxItems": 32, "items": {"type": "object", "properties": {
                "metric": {"type": "string", "enum": ["cross_team_contributions", "survey_trend"]},
                "dimension": {"type": ["string", "null"], "description":
                    "Exact survey topic for survey_trend; null for cross-team counts. Never a time grouping."}},
                "required": ["metric", "dimension"], "additionalProperties": False}},
            "deliverables": {"type": "array", "maxItems": 16, "description":
                "All explicitly requested output components, quoted from the original question; no added requirements. Owner supplies the analysis, Original owns final presentation.",
                "items": {"type": "object", "properties": {
                    "request_excerpt": {"type": "string", "minLength": 1, "maxLength": 400},
                    "owner": {"type": "string", "enum": ["Original", "Cherry", "Vanilla", "Lime"]}},
                    "required": ["request_excerpt", "owner"], "additionalProperties": False}},
        })]
        history = [{"role": "user", "content": json.dumps({"question": question, "scope": self.scope.__dict__})}]
        reconsidered_clarification = False
        for attempt in range(1, 3):
            self.budget.consume("model")
            turn = self.model.respond(with_policies("Plan Echo's scoped analysis. Return submit_plan only. Structured SQL counts need Cherry; "
                "full comment sentiment classification and its counts/percentages need Vanilla ONLY: set needs_sentiment=true, "
                "needs_text=true, needs_numbers=false and metrics=[] unless the user separately requests SQL/rating metrics. "
                "For Recognition comment percentages with literal examples, do not add Manager support, survey scores or Cherry. "
                "use Vanilla for requested narrative/source interpretation as well as sentiment classification. A structured SQL count alone does not need "
                "Vanilla. Requests to cite SQL results or explain survey-score limitations do not "
                "require text retrieval. Use Vanilla for actual narrative examples or qualitative interpretation. "
                "For example, a quarterly numeric Recognition survey trend with dates, response counts, mean "
                "scores and metric limitations needs Cherry only; it does not request comment sentiment. "
                "The backend already restricts the data to the supplied manager's roster and dates; those details "
                "do not need clarification. Charts are optional; request one only if asked for or useful to compare indicators. "
                "Return metrics as a list of ALL needed catalog requests. Include one survey_trend entry per exact "
                "dimension explicitly needed by the user's rating question. Never copy example dimensions or add unrequested metrics. Cross-team counts use "
                "cross_team_contributions with dimension=null. Use metrics=[] for custom SQL or no numeric work. "
                "The application prepares these metrics; Cherry keeps tools to complete additional calculations. "
                "List all explicitly requested output components in deliverables, using exact contiguous excerpts "
                "from the question and the role supplying the analysis. Include requested examples, synthesis, "
                "limitations and follow-up questions, not only calculations. Original owns final integration. "
                "Do not invent output requirements or select additional roles just to fill the checklist. "
                "All output is English. Use clarification_question=null and clarification_basis=null unless a necessary "
                "task detail prevents proceeding. Otherwise supply a concrete missing_detail, blocking_reason and exact "
                "request_excerpt after reading the COMPLETE request. Your proposed clarification will be returned once "
                "for reconsideration within the existing two-attempt planning limit. Remove it if the full request, "
                "scope or permitted tools already answer it; never ask for credentials, anonymous identities or wider access."), history, tools, True)
            history.extend(turn.output_items)
            if len(turn.calls) != 1 or turn.calls[0].name != "submit_plan":
                feedback = {"error": "Return exactly one submit_plan call."}
                self.record_planning_attempt(attempt, "rejected", {}, feedback,
                                             attempt < 2, "invalid_plan_call")
                reject_calls(history, turn, json.dumps(feedback))
                continue
            call = turn.calls[0]
            received = {}
            try:
                plan = json.loads(call.arguments)
                if isinstance(plan, dict):
                    received = {key: planning_value(plan[key]) for key in
                                ("clarification_question", "clarification_basis") if key in plan}
                if isinstance(plan, dict) and "metrics" not in plan and self.mode != "live":
                    # Read older scripted fixtures; live plans must use the current schema.
                    metric, dimension = plan.pop("metric", "none"), plan.pop("dimension", "")
                    plan["metrics"] = [] if metric == "none" else [{"metric": metric, "dimension": dimension or None}]
                if isinstance(plan, dict) and self.mode != "live":
                    plan.setdefault("clarification_basis", None)
                    plan.setdefault("needs_sentiment", False)
                if isinstance(plan, dict):
                    # Older submissions did not carry a checklist; the full question
                    # remains authoritative and must still receive independent review.
                    plan.setdefault("deliverables", [])
                if not isinstance(plan, dict) or set(plan) != {"needs_numbers", "needs_text", "needs_sentiment", "include_chart", "clarification_question", "clarification_basis", "metrics", "deliverables"}:
                    raise ValueError("Plan fields differ from the required schema.")
                if any(type(plan[k]) is not bool for k in ("needs_numbers", "needs_text", "needs_sentiment", "include_chart")):
                    raise ValueError("Plan flags must be booleans.")
                if plan["needs_sentiment"] and not plan["needs_text"]:
                    raise ValueError("Sentiment classification requires Vanilla (needs_text=true).")
                if plan["include_chart"] and not plan["needs_numbers"]:
                    raise ValueError("A chart requires numeric evidence.")
                if not isinstance(plan["metrics"], list) or len(plan["metrics"]) > 32:
                    raise ValueError("metrics must be a list of at most 32 catalog requests.")
                if plan["metrics"] and not plan["needs_numbers"]:
                    raise ValueError("A metric requires the numeric specialist.")
                for request in plan["metrics"]:
                    if not isinstance(request, dict) or set(request) != {"metric", "dimension"} \
                            or request["metric"] not in {"cross_team_contributions", "survey_trend"}:
                        raise ValueError("Invalid planned metric request.")
                    if request["metric"] == "survey_trend":
                        if not isinstance(request["dimension"], str) or not 1 <= len(request["dimension"].strip()) <= 100:
                            raise ValueError("A survey trend needs one exact dimension per request.")
                    elif request["dimension"] is not None:
                        raise ValueError("Cross-team counts require dimension=null.")
                q = clarification_question(plan["clarification_question"])
                plan["clarification_question"] = q
                if q is not None:
                    self.validate_clarification_basis(plan["clarification_basis"], question)
                    if not reconsidered_clarification:
                        reconsidered_clarification = True
                        raise ValidationError("clarification_recheck", "clarification_basis",
                            "Before asking the user, reconsider the COMPLETE original question and supplied scope. "
                            "Check whether the allegedly missing detail is already present or can be obtained with "
                            "permitted tools. Return a corrected plan with both clarification fields null if so; "
                            "otherwise return a justified necessary clarification. Do not guess missing facts.")
                elif plan["clarification_basis"] is not None:
                    plan["clarification_basis"] = None
                    self.record_planning_attempt(attempt, "normalized", received,
                        {"correction": "No clarification question; unused clarification_basis normalized to null."},
                        False, "unused_clarification_basis")
                if any(r["metric"] == "survey_trend" for r in plan["metrics"]) and q is None:
                    self.budget.consume("tool")
                    dimensions = self.specialist("Cherry").reader.describe()["survey_dimensions"]
                    for request in plan["metrics"]:
                        if request["metric"] != "survey_trend":
                            continue
                        matches = [d for d in dimensions if d.casefold() == request["dimension"].strip().casefold()]
                        if dimensions and not matches:
                            raise ValueError("Unknown survey dimension. Choose the topic requested by the user from: " +
                                             ", ".join(dimensions) + ". A quarter is a time grouping, not a survey dimension.")
                        request["dimension"] = matches[0] if matches else request["dimension"].strip()
                plan["metrics"] = list({(r["metric"], r["dimension"]): r for r in plan["metrics"]}.values())
                plan["deliverables"] = self.validate_deliverables(plan["deliverables"], question)
                record("workflow_plan", agent="Original", needs_numbers=plan["needs_numbers"],
                       needs_text=plan["needs_text"], needs_sentiment=plan["needs_sentiment"], include_chart=plan["include_chart"], needs_clarification=q is not None,
                       metric_count=len(plan["metrics"]))
                return plan
            except (ValueError, TypeError) as error:
                feedback = repair_feedback(error) if isinstance(error, ValidationError) else {"error": str(error)}
                self.record_planning_attempt(attempt, "rejected", received, feedback,
                                             attempt < 2, **error_summary(error))
                history.append({"type": "function_call_output", "call_id": call.call_id,
                                "output": json.dumps(feedback)})
        raise RuntimeError("Original did not return a valid bounded analysis plan.")

    @staticmethod
    def validate_deliverables(items, question):
        """Validate source/structure only; the reviewer still judges task meaning."""
        if not isinstance(items, list) or len(items) > 16:
            raise ValidationError("deliverables_list", "deliverables", "Return at most 16 requested deliverables.")
        result = []
        for index, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"request_excerpt", "owner"}:
                raise ValidationError("deliverable_fields", "deliverables", "Each deliverable needs request_excerpt and owner only.", item_index=index)
            excerpt, owner = item["request_excerpt"], item["owner"]
            if not isinstance(excerpt, str) or not 1 <= len(excerpt) <= 400 or not excerpt.strip() or excerpt not in question:
                raise ValidationError("deliverable_excerpt", "deliverables.request_excerpt", "Copy a nonempty exact excerpt from the original question, up to 400 characters.", item_index=index)
            if not isinstance(owner, str) or owner not in {"Original", "Cherry", "Vanilla", "Lime"}:
                raise ValidationError("deliverable_owner", "deliverables.owner", "Choose an existing analysis role.", item_index=index)
            result.append({"deliverable_id": f"D{index + 1}", **item})
        return result

    def record_planning_attempt(self, attempt, status, received, feedback, feedback_sent,
                                validation_code=None, **details):
        """Keep the same sanitized planning diagnostic in JSONL and the result artifact."""
        entry = {"attempt": attempt, "status": status, "received": received,
                 "feedback": {key: planning_value(value) if isinstance(value, str) else value
                              for key, value in feedback.items()},
                 "feedback_retry_available": feedback_sent, **details}
        if validation_code is not None:
            entry["validation_code"] = validation_code
        self.planning_diagnostics.append(entry)
        record("structured_response_repair" if status == "rejected" else "planning_normalization",
               agent="Original", stage="planning", **entry)

    def validate_clarification_basis(self, basis, question):
        """Check observable contradictions; prompt reconsideration handles semantic ambiguity."""
        fields = {"missing_field", "missing_detail", "blocking_reason", "request_excerpt"}
        if not isinstance(basis, dict) or set(basis) != fields:
            raise ValidationError("clarification_basis_required", "clarification_basis",
                                  "Identify missing_field, missing_detail, blocking_reason and request_excerpt.")
        if not isinstance(basis["missing_field"], str) or basis["missing_field"] not in {
                "manager_id", "start_date", "end_date", "metric", "task", "other"}:
            raise ValidationError("clarification_field", "clarification_basis.missing_field",
                                  "Choose a field from the declared clarification schema.")
        for field, maximum in (("missing_detail", 240), ("blocking_reason", 500), ("request_excerpt", 400)):
            if not isinstance(basis[field], str) or not 1 <= len(basis[field].strip()) <= maximum or len(basis[field]) > maximum:
                raise ValidationError("clarification_basis_text", "clarification_basis." + field,
                                      "Clarification details must be nonempty bounded strings.")
        if basis["request_excerpt"] not in question:
            raise ValidationError("clarification_excerpt_not_literal", "clarification_basis.request_excerpt",
                                  "Quote the original request exactly; do not invent a truncated or altered request.")
        if basis["missing_field"] in self.scope.__dict__ and self.scope.__dict__[basis["missing_field"]]:
            raise ValidationError("clarification_already_supplied", "clarification_basis.missing_field",
                                  "The application already supplies this scope field. Use it; do not ask for it again.")

    def set_delegations(self, names):
        self.allowed_delegations = set(names)
        self.definitions = [tool for tool in self.all_definitions
            if {"ask_cherry": "Cherry", "ask_vanilla": "Vanilla"}[tool["name"]] in self.allowed_delegations]

    def specialist(self, name):
        if name not in self.specialists:
            if name == "Cherry":
                child = CherryAgent(self.database, self.scope, self.model_factory(name), self.mode, budget=self.budget)
            else:
                child = VanillaAgent(self.database, self.scope, self.model_factory(name), self.mode,
                    retrieval=self.retrieval, embedding_model=self.embedding_model, cache_root=self.cache_root, budget=self.budget)
                child.workflow_reuse = True
            self.specialists[name] = child
        return self.specialists[name]

    def delegate(self, name, question, task_type=None):
        if name not in self.allowed_delegations:
            raise ValueError("This repair/plan does not require that specialist. Use the supplied evidence.")
        if self.mode == "live" and task_type not in ({"numeric"} if name == "Cherry" else {"text", "sentiment"}):
            raise ValueError("Delegation task_type must match the specialist: Cherry=numeric, Vanilla=text/sentiment.")
        declined_key = (name, question.strip(), task_type)
        if declined_key in getattr(self, "declined_requests", {}):
            return self.declined_requests[declined_key]
        try:
            child = self.specialist(name)
            prepared = []
            if name == "Cherry":
                child.required_metrics = self.planned_metrics
                if self.repair_round == 0:
                    for request in self.planned_metrics:
                        key = (request["metric"], request["dimension"])
                        if key not in self.prepared_metrics:
                            self.budget.consume("tool")
                            try:
                                self.prepared_metrics[key] = child.handlers["run_metric"](**request)
                            except (ValueError, TypeError) as error:
                                record("prepared_metric_failed", agent="Cherry", **error_summary(error))
                                continue
                            record("prepared_metric", agent="Cherry", metric_id=request["metric"], remaining=self.budget.remaining())
                prepared = list(self.prepared_metrics.values())
            previous = next((item for item in reversed(self.child_results) if item["agent"] == name), None)
            if previous and previous.get("scope") == self.scope.__dict__:
                # Context reuse within this workflow, not a claim that the new task is done.
                retained = {item["citation_id"]: item for item in previous.get("evidence", [])}
                retained.update({item["citation_id"]: item for item in prepared})
                prepared = list(retained.values())
            context = ([{"role": "user", "content": json.dumps({"original_request": self.original_request,
                        "assigned_deliverables": [item for item in getattr(self, "request_deliverables", []) if item["owner"] == name],
                        "note": "Address the assigned analytical components within your role and fixed scope. Return the existing answer/evidence format. Original owns final integration; distinguish analysis, source examples and unavailable evidence."})}]
                       if getattr(self, "original_request", None) else [])
            result = child.run(question, initial_evidence=prepared, context=context)
        except AgentRunError as error:
            result = error.result
            result.diagnostics["numeric_coverage"] = child.numeric_coverage(result.evidence) if name == "Cherry" else []
            self.child_results.append(asdict(result))
            return {"agent": name, "status": "failed", "error": "Specialist execution did not finish; see failure.stage. Retained evidence is available, not independently approved. Reuse it, resolve missing work and submit a candidate for review.",
                    "task_outcome": result.task_outcome,
                    "evidence": result.evidence, "failure": result.failure,
                    "numeric_coverage": child.numeric_coverage(result.evidence) if name == "Cherry" else []}
        self.child_results.append(asdict(result))
        response = {"agent": name, "status": result.status, "task_outcome": result.task_outcome,
                "answer": result.answer, "scope": result.scope, "evidence": result.evidence,
                "claims": result.claims,
                "numeric_coverage": child.numeric_coverage(result.evidence) if name == "Cherry" else []}
        if result.status == "declined":
            self.declined_requests[declined_key] = response
            if result.task_outcome.get("reason_code") == "out_of_role":
                self.set_delegations({"Cherry", "Vanilla"})
        elif result.status == "incomplete":
            self.declined_requests[declined_key] = response
        return response

    def run(self, question):
        # A fresh workflow prevents artifacts from earlier questions entering the answer.
        self.close()
        self.specialists, self.child_results = {}, []
        self.original_request = question
        self.budget = RunBudget(model_limit=self.model_call_limit,
            tool_limit=48 + 2 * max(0, self.model_call_limit - 32), seconds=self.run_seconds)
        self.last_result, self.last_verdict = None, None
        self.planned_metrics, self.prepared_metrics, self.repair_round = [], {}, 0
        self.request_deliverables = []
        self.coordinator_diagnostics = {}
        self.planning_diagnostics = []
        self.declined_requests = {}
        self.attempt_reviews, self.drafts = [], []
        self.active_stage, self.verification_diagnostics = "planning", {}
        try:
            return self.workflow(question)
        except (RuntimeError, ValueError) as error:
            candidate = self.last_result or AgentResult("Original", question, "", self.scope.__dict__, mode=self.mode)
            candidate.failure = error_summary(error)
            candidate.failure["stage"] = candidate.diagnostics.get("stage", self.active_stage) if self.active_stage == "coordination" else self.active_stage
            candidate.diagnostics["verification"] = self.verification_diagnostics
            candidate.diagnostics["planning_attempts"] = self.planning_diagnostics
            candidate.delegations = self.child_results
            candidate.sentiment = {key: value for child in self.child_results for key, value in child.get("sentiment", {}).items()}
            candidate.connections = self.connection_summary
            candidate.verification = {"decision": "revise", "status": "failed" if self.active_stage == "verification" else
                                      "completed" if self.attempt_reviews else "not_run", "reviews": self.attempt_reviews,
                                      "drafts_checked": len(self.drafts), "rejected_drafts": self.drafts}
            record("workflow_failed", agent="Original", **candidate.failure, remaining=self.budget.remaining())
            return self.incomplete(candidate, self.last_verdict)

    def incomplete(self, candidate, verdict):
        candidate.findings = verdict.findings if verdict else []
        targets = verdict.repair_targets if verdict else ["Original"]
        candidate.limitations = (unresolved_follow_up(verdict) if verdict else []) or safe_follow_up(targets) or ["The requested analysis could not be fully verified."]
        if candidate.failure:
            candidate.limitations.insert(0, explain_failure(candidate.failure))
        candidate.next_steps = ["Address the listed unresolved items using retained evidence where available, then review the complete revised answer."]
        supported = [f["text"] for f in candidate.findings if f["status"] == "supported"]
        if verdict and (verdict.deterministic_issues or verdict.ratings["Safety / Appropriateness"]["score"] < 3):
            supported = []
            candidate.findings = [{**f, "status": "withheld"} for f in candidate.findings]
        question = verdict.clarification_question if verdict and "clarify" in targets and not verdict.deterministic_issues \
            and verdict.ratings["Safety / Appropriateness"]["score"] == 3 else None
        if question and verdict.ratings["Safety / Appropriateness"]["score"] == 3:
            candidate.status = "needs_clarification"
            candidate.clarification_questions = [question]
        else:
            candidate.status = "partial" if supported else "failed"
        candidate.answer = ("Partial analysis — independently supported findings:\n\n"+"\n\n".join(supported)) if supported else "No verified answer was produced in this run."
        if supported and any(f["status"] == "supported" and f.get("kind") in {"interpretation", "proposal"} for f in candidate.findings):
            candidate.answer += "\n\nInterpretations remain provisional. Proposed actions/questions are for manager review, not observed outcomes."
        candidate.answer += "\n\nUnresolved: " + " ".join(candidate.limitations)
        if question:
            candidate.answer += "\n\nClarification needed: " + question
        candidate.answer += "\n\nNext step: " + candidate.next_steps[0]
        candidate.visualization = {"charts": [], "reason": "Charts withheld while the package requires review.", "mode": self.mode, "tool_trace": []}
        return candidate

    def workflow(self, question):
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError("Question must contain 1 to 4,000 characters.")
        plan = self.plan(question)
        self.coordinator_diagnostics["planning_attempts"] = self.planning_diagnostics
        self.request_deliverables = plan.get("deliverables", [])
        self.coordinator_diagnostics["request_deliverables"] = self.request_deliverables
        self.numeric_requested = plan["needs_numbers"] or plan["needs_sentiment"]
        self.planned_metrics = plan["metrics"]
        if "Cherry" in self.specialists:
            self.specialists["Cherry"].required_metrics = self.planned_metrics
        if plan["clarification_question"]:
            q = plan["clarification_question"]
            return AgentResult("Original", question, "Clarification needed: " + q, self.scope.__dict__,
                mode=self.mode, status="needs_clarification", clarification_questions=[q],
                verification={"decision": "needs_clarification", "reviews": [], "drafts_checked": 0},
                diagnostics={"clarification_basis": plan["clarification_basis"], "planning_reconsidered": True,
                             "planning_attempts": self.planning_diagnostics})
        self.set_delegations([name for name, needed in (("Cherry", plan["needs_numbers"]), ("Vanilla", plan["needs_text"])) if needed])
        for name, needed in (("Cherry", plan["needs_numbers"]), ("Vanilla", plan["needs_text"]), ("Lime", plan["include_chart"])):
            if not needed:
                record("role_skipped", agent=name, reason="not_needed_by_plan")
        context, evidence = [], []
        candidates, reviews, coordinator_trace = [], [], []
        prior_visuals, prior_fingerprint, targets = None, None, set()
        pending_corrections = []
        for attempt in range(2):
            self.repair_round = attempt
            if attempt and targets == {"Lime"}:
                record("repair_reuse", agent="Original", reason="chart_only_repair")
            else:
                numeric_child = self.specialists.get("Cherry")
                pending_coverage = numeric_child.numeric_coverage(evidence) if numeric_child else [
                    {**request, "status": "pending", "citation_id": None} for request in self.planned_metrics]
                task_context = [{"role": "user", "content": json.dumps({
                    "numeric_coverage": pending_coverage, "request_deliverables": self.request_deliverables,
                    "pending_corrections": pending_corrections,
                    "completion_check": "Before submitting, account for every requested component in the visible answer or explain unavailable evidence. Evidence existing internally does not make a requested example visible. Checklist and prior support do not establish semantic correctness."})}]
                self.active_stage = "coordination"
                candidate = super().run(question, initial_evidence=evidence, context=context + task_context,
                                        diagnostics=self.coordinator_diagnostics)
                coordinator_trace.extend(candidate.tool_trace)
            candidates.append(candidate.answer)
            self.drafts = candidates
            self.last_result = candidate
            cherry = self.specialists.get("Cherry")
            vanilla = self.specialists.get("Vanilla")
            lookup = {doc["citation_id"]: doc for doc in vanilla.searcher.documents} if vanilla else None
            candidate.sentiment = {key: value for child in self.child_results
                                   for key, value in child.get("sentiment", {}).items()}
            verifier = ZeroSugarAgent(self.scope, self.model_factory("ZeroSugar"), self.mode,
                budget=self.budget, sql_reader=cherry.reader if cherry else None, document_lookup=lookup,
                sentiment_reports=candidate.sentiment,
                sentiment_documents=vanilla.sentiment_documents if vanilla else None)
            numeric_evidence = [item for item in candidate.evidence if item.get("producer") == "Cherry" and "sql" in item]
            fingerprint = hashlib.sha256(json.dumps(numeric_evidence, sort_keys=True).encode()).hexdigest()
            chart_failure = None
            if plan["include_chart"]:
                if prior_visuals is not None and prior_fingerprint == fingerprint and ("Lime" not in targets or
                        (prior_visuals.get("task_outcome") or {}).get("status") == "declined"):
                    candidate.visualization = prior_visuals
                    record("repair_reuse", agent="Lime", reason="unchanged_numeric_evidence")
                else:
                    lime = LimeAgent(self.scope, self.model_factory("Lime"), self.mode, self.budget)
                    try:
                        self.active_stage = "chart_planning"
                        candidate.visualization = asdict(lime.plan(question, candidate.answer, candidate.evidence,
                                                  feedback=reviews[-1] if reviews else None))
                        prior_visuals, prior_fingerprint = candidate.visualization, fingerprint
                    except (RuntimeError, ValueError) as error:
                        chart_failure = error_summary(error)
                        chart_failure["stage"] = "chart_planning"
                        candidate.diagnostics["Lime"] = lime.diagnostics
                        record("chart_planning_failed", agent="Lime", **chart_failure)
                        candidate.visualization = {"charts": [], "reason": "The planned chart could not be completed.", "mode": self.mode, "tool_trace": []}
                if (candidate.visualization.get("task_outcome") or {}).get("status") == "declined":
                    chart_failure = {"error_category": "task_declined"}
            else:
                candidate.visualization = {"charts": [], "reason": "No chart needed by the analysis plan.", "mode": self.mode, "tool_trace": []}
            candidate.rag = {"specialist_runs": [child["rag"] for child in self.child_results if child.get("rag")],
                "note": "RAG is recorded only when Vanilla runs; numerical-only questions may use Cherry alone."}
            coverage = cherry.numeric_coverage(candidate.evidence) if cherry else [
                {**request, "status": "pending", "citation_id": None} for request in self.planned_metrics]
            candidate.diagnostics["numeric_coverage"] = coverage
            candidate.diagnostics["requires_sentiment"] = plan["needs_sentiment"]
            self.active_stage = "verification"
            self.verification_diagnostics = verifier.diagnostics
            verdict = verifier.review(question, candidate.answer, candidate.evidence, candidate.visualization,
                                      numeric_coverage=coverage, claims=candidate.claims or None,
                                      grounding=candidate.grounding or None,
                                      task_outcomes=[{"agent": c["agent"], "status": c["status"], "task_outcome": c.get("task_outcome", {})}
                                                     for c in self.child_results], require_sentiment=plan["needs_sentiment"],
                                      request_deliverables=self.request_deliverables, previous_corrections=pending_corrections)
            if chart_failure:
                verdict.decision = "revise"
                verdict.repair_targets = sorted(set(verdict.repair_targets) | {"Lime"})
                verdict.issues.append("The planned chart could not be completed.")
                verdict.corrections.append({"correction_id": f"C{len(verdict.issues)}",
                    "issue_index": len(verdict.issues) - 1, "issue": verdict.issues[-1], "kind": "coverage",
                    "owner": "Lime", "requested_change": verdict.issues[-1], "citation_ids": [], "request_excerpt": None})
                candidate.failure = chart_failure
            reviews.append(asdict(verdict))
            candidate.diagnostics["verification"] = verifier.diagnostics
            self.last_verdict, self.attempt_reviews = verdict, reviews
            self.active_stage = "release"
            candidate.findings = verdict.findings
            candidate.diagnostics["pending_corrections"] = verdict.corrections
            if verdict.decision == "accept":
                candidate.verification = {"decision": "accept", "status": "completed", "reviews": reviews, "drafts_checked": len(candidates)}
                candidate.delegations = self.child_results
                candidate.tool_trace = coordinator_trace
                candidate.connections = self.connection_summary
                latest_children = {c["agent"]: c for c in self.child_results}
                unresolved_child = any(c.get("status") == "incomplete" or
                    (c.get("status") == "failed" and not c.get("task_outcome", {}).get("evidence_retained")) or
                    (c.get("status") == "declined" and c.get("task_outcome", {}).get("reason_code") != "out_of_role")
                    for c in latest_children.values())
                if unresolved_child:
                    candidate.verification["decision"] = "revise"
                    verdict.repair_targets = [name for name, child in latest_children.items() if child.get("status") in {"failed", "incomplete", "declined"}]
                    candidate.failure = next((child.get("failure") for child in latest_children.values() if child.get("status") == "failed" and child.get("failure")), {})
                    return self.incomplete(candidate, verdict)
                recovered = [name for name, child in latest_children.items() if child.get("status") == "failed"]
                if recovered:
                    candidate.diagnostics["recovered_specialists"] = recovered
                    record("specialist_evidence_recovered", agents=recovered, review_status="completed")
                candidate.status = "complete"
                return candidate
            evidence = candidate.evidence
            targets = set(verdict.repair_targets)
            pending_corrections = verdict.corrections
            record("repair_requested", agent="Original", targets=sorted(targets),
                   supported_findings=sum(f["status"] == "supported" for f in verdict.findings))
            if "clarify" in targets and verdict.clarification_question:
                break
            if targets == {"Lime"} and (candidate.visualization.get("task_outcome") or {}).get("status") == "declined":
                break
            self.set_delegations(targets & {"Cherry", "Vanilla"})
            context = [{"role": "assistant", "content": candidate.answer},
                {"role": "user", "content": "Repair the specified mandatory issues. Preserve supported facts, meaning and sources, "
                 "while allowing rephrasing, reordering, qualitative synthesis and removal of redundant presentation. "
                 "Reuse existing evidence; the revised candidate will be reviewed again. Answer in English. " +
                 json.dumps({"review": asdict(verdict), "pending_corrections": pending_corrections,
                             "request_deliverables": self.request_deliverables, "evidence": evidence}, ensure_ascii=False)}]
        # Rejected drafts are preserved in the local artifact, never released as findings.
        candidate.verification = {"decision": "revise", "status": "completed", "reviews": reviews, "drafts_checked": len(candidates), "rejected_drafts": candidates}
        candidate.delegations, candidate.tool_trace = self.child_results, coordinator_trace
        candidate.connections = self.connection_summary
        return self.incomplete(candidate, verdict)

    def close(self):
        for child in self.specialists.values():
            child.close()
        self.specialists = {}
