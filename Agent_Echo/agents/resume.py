"""Resume one failed phase with retained inputs; never restart the coordinator workflow."""

from dataclasses import asdict
import re

from .capture import database_identity, source_versions, trace
from .data_access import AccessScope, ScopedData
from .runtime import AgentResult, RunBudget, Specialist
from .original import OriginalAgent
from .cherry import CherryAgent
from .vanilla import VanillaAgent
from .lime import LimeAgent
from .zero_sugar import ZeroSugarAgent
from .tools import SQLReader
from .sentiment_rubric import SENTIMENT_RUBRIC_VERSION


def resume_phase(saved, registry, database, model_limit=32, seconds=300):
    scope = AccessScope(**saved['scope'])
    payload, kind, role = saved['payload'], saved['kind'], saved['role']
    if payload.get('mode') != 'live':
        raise ValueError('Only a live checkpoint can be resumed with live models.')
    expected = payload.get('database_hash')
    if expected is not None and database_identity(database) != expected:
        raise ValueError('The source database changed. Retained work cannot be silently reused against different sources.')
    profile = payload.get('profile')
    if profile and registry.profile_for(role) != profile:
        raise ValueError('Resume must preserve the failed phase model profile; use a separate full test to change models.')
    connection = payload.get('connection')
    if connection:
        current = registry.describe()[role]
        fields = ('provider', 'api', 'endpoint', 'model', 'max_output_tokens', 'timeout_seconds',
                  'max_retries', 'request_interval_seconds', 'rate_limit_retries', 'reasoning_effort', 'clear_thinking')
        if any(current.get(key) != connection.get(key) for key in fields):
            raise ValueError('The retained model/transport configuration changed. Use a separate test rather than mixing checkpoints.')
    budget = RunBudget(model_limit=model_limit, tool_limit=48 + 2 * max(0, model_limit - 32), seconds=seconds)
    question = payload.get('question', 'Resume the retained sentiment classification phase.')
    trace('phase_resume', parent_run_id=saved['run_id'], source_checkpoint=saved['source_path'],
          kind=kind, role=role, prior_code_versions=saved['code_versions'], code_versions=source_versions(),
          model_call_limit=model_limit, run_seconds=seconds)
    agent = None
    try:
        if kind == 'review':
            if role != 'ZeroSugar':
                raise ValueError('Review checkpoints belong to ZeroSugar.')
            backend = ScopedData(database, scope)
            try:
                reader = SQLReader(backend.structured_tables(), scope)
                documents = {doc['citation_id']: doc for doc in backend.text_documents()}
                sentiment_documents, teams = backend.sentiment_documents(), list(backend.teams)
            finally:
                backend.close()
            agent = ZeroSugarAgent(scope, registry.get(role), 'live', budget=budget, sql_reader=reader,
                document_lookup=documents, database=database, sentiment_reports=payload['sentiment_reports'],
                sentiment_documents=sentiment_documents, authorized_teams=teams)
            agent.owned_reader = reader
            review = agent.review(question, payload['answer'], payload['evidence'], **payload['arguments'],
                resume_completeness=saved['progress'].get('completed_completeness'))
            result = AgentResult(role, question, 'Review decision: ' + review.decision,
                scope.__dict__, evidence=payload['evidence'], mode='live',
                verification={**asdict(review), 'status': 'completed'},
                status='unverified' if review.decision == 'accept' else 'partial',
                findings=review.findings, diagnostics={'verification': agent.diagnostics,
                    'phase_only': True, 'candidate_answer': payload['answer'], 'candidate_claims': payload['arguments'].get('claims'),
                    'note': 'Only review was resumed. No Original/Vanilla calls or automatic correction loop ran.'},
                sentiment=payload['sentiment_reports'])
            return result
        if kind == 'planning':
            if role != 'Original':
                raise ValueError('Planning checkpoints belong to Original.')
            agent = OriginalAgent(database, scope, registry.get, 'live', model_call_limit=model_limit, run_seconds=seconds)
            agent.budget = budget
            plan = agent.plan(question)
            return AgentResult(role, question, 'Planning phase completed; no analytical answer was released.',
                scope.__dict__, mode='live', diagnostics={'phase_only': True, 'plan': plan})
        if kind == 'visual':
            if role != 'Lime':
                raise ValueError('Visualization checkpoints belong to Lime.')
            agent = LimeAgent(scope, registry.get(role), 'live', budget)
            result = agent.plan(question, payload['answer'], payload['evidence'], payload.get('feedback'))
            return AgentResult(role, question, 'Visualization phase completed; independent review is still required.',
                scope.__dict__, evidence=payload['evidence'], mode='live', visualization=asdict(result),
                diagnostics={'phase_only': True})
        if role == 'Vanilla':
            agent = VanillaAgent(database, scope, registry.get(role), 'live', budget=budget)
            agent.workflow_reuse = True
            agent.sentiment_reports = payload.get('sentiment_reports', {})
            agent.sentiment_counter = max([int(key[9:]) for key in agent.sentiment_reports if re.fullmatch(r'SENTIMENT\d+', key)] or [0])
        elif role == 'Cherry' and kind == 'specialist':
            agent = CherryAgent(database, scope, registry.get(role), 'live', budget=budget)
        elif role == 'Original' and kind == 'specialist':
            agent = OriginalAgent(database, scope, registry.get, 'live', model_call_limit=model_limit, run_seconds=seconds)
            agent.set_delegations(set())
            agent.handlers = {}  # A focused synthesis retry cannot delegate again.
            agent.budget = budget
        else:
            raise ValueError('Unsupported role for this retained phase.')
        if kind == 'sentiment':
            if role != 'Vanilla' or payload['rubric_version'] != SENTIMENT_RUBRIC_VERSION:
                raise ValueError('Retained classification rubric/role differs; existing labels cannot be silently reused.')
            agent.resume_sentiment = saved['progress'].get('sentiment_state', payload['state'])
            summary = agent.analyze_sentiment(payload['dimension'])
            evidence = [summary] if summary.get('complete') else []
            return AgentResult(role, question, 'Classification phase completed; independent review is still required.'
                if summary.get('complete') else 'Classification remains incomplete; no partial percentages released.',
                scope.__dict__, evidence=evidence, mode='live', sentiment=agent.sentiment_reports,
                status='unverified' if summary.get('complete') else 'incomplete',
                diagnostics={'phase_only': True, 'sentiment_progress': summary})
        agent.resume_state = payload
        if role == 'Vanilla':
            agent.retained_sentiment_progress = list(payload.get('sentiment_progress', {}).values())
        if role == 'Cherry':
            agent.required_metrics = payload.get('required_metrics', [])
            agent.metric_cache = {tuple(item['key']): item['result'] for item in payload.get('metric_cache', [])}
            agent.metric_errors = {tuple(key) for key in payload.get('metric_errors', [])}
            agent.reader.counter = max([int(item['citation_id'][3:]) for item in payload['evidence']
                if re.fullmatch(r'SQL\d+', item.get('citation_id', ''))] or [0])
        raw = Specialist.run(agent, question, diagnostics=payload.get('diagnostics'))
        if role == 'Vanilla':
            agent.attach_sentiment(raw)
        return AgentResult(role, question, 'Retained generation phase completed; independent review is still required.',
            scope.__dict__, evidence=raw.evidence, mode='live', sentiment=raw.sentiment,
            status=raw.status, diagnostics={'phase_only': True, 'phase_result': asdict(raw)})
    finally:
        if agent and hasattr(agent, 'close'):
            agent.close()
