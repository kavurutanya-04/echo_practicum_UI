"""Full local execution capture and explicit phase checkpoints; never credentials."""

from contextvars import ContextVar
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
import traceback


_active_capture = ContextVar('echo_full_capture', default=None)
_secrets = set()
CHECKPOINT_VERSION = 'echo-checkpoint-v1'


def register_secret(value):
    if isinstance(value, str) and value:
        _secrets.add(value)


def exception_context(error):
    return {'error_type': type(error).__name__, 'message': str(error),
            'traceback': ''.join(traceback.format_exception(type(error), error, error.__traceback__))}


def json_value(value):
    if hasattr(value, 'model_dump'):
        return json_value(value.model_dump())
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Path, datetime)):
        return str(value)
    return str(value)


def redact_credentials(value):
    if isinstance(value, dict):
        fields = {'api_key', 'authorization', 'access_token', 'refresh_token', 'password',
                  'client_secret', 'secret_key', 'cookie', 'set-cookie'}
        return {key: '[credential omitted]' if key.lower() in fields else redact_credentials(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact_credentials(item) for item in value]
    if isinstance(value, str):
        if value.lstrip().startswith(('{', '[')):
            try:
                parsed = json.loads(value)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, (dict, list)):
                cleaned = redact_credentials(parsed)
                if cleaned != parsed:
                    return json.dumps(cleaned, ensure_ascii=False)
        for secret in sorted(_secrets, key=len, reverse=True):
            value = value.replace(secret, '[credential omitted]')
        return re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [credential omitted]', value)
    return value


def digest(value):
    return hashlib.sha256(json.dumps(json_value(value), sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def source_versions():
    root = Path(__file__).resolve().parents[1]
    files = [root / 'run_agent.py', *sorted((root / 'agents').glob('*.py'))]
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def database_identity(path):
    if path is None:
        return None
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(event, **fields):
    capture = _active_capture.get()
    if capture is not None:
        capture.write(event, **fields)


def checkpoint(kind, role, scope, payload):
    capture = _active_capture.get()
    return capture.checkpoint(kind, role, scope, payload) if capture else None


def checkpoint_progress(path, **progress):
    capture = _active_capture.get()
    if capture and path:
        capture.progress(path, **progress)


def capture_summary():
    capture = _active_capture.get()
    return capture.summary() if capture else {}


class FullCapture:
    def __init__(self, directory, run_id, metadata):
        self.directory = Path(directory).resolve() / 'details' / run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.run_id, self.latest = run_id, None
        self.checkpoints = []
        self.connections = {}
        self.versions = source_versions()
        self.stream = (self.directory / 'exchanges.jsonl').open('x', encoding='utf-8')
        self.token = _active_capture.set(self)
        self.write('capture_started', metadata=metadata, code_versions=self.versions)

    def write(self, event, **fields):
        if event == 'execution_configuration':
            self.connections = fields.get('connections', {})
        body = redact_credentials(json_value({'time_utc': datetime.now(timezone.utc).isoformat(),
            'run_id': self.run_id, 'event': event, **fields}))
        self.stream.write(json.dumps(body, ensure_ascii=False) + '\n')
        self.stream.flush()

    @staticmethod
    def save(path, data):
        temporary = path.with_suffix('.tmp')
        body = redact_credentials(json_value(data))
        if body.get('version') == CHECKPOINT_VERSION and 'kind' in body:
            body['checkpoint_hash'] = digest({key: value for key, value in body.items() if key != 'checkpoint_hash'})
        temporary.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(path)

    def checkpoint(self, kind, role, scope, payload):
        previous_points = []
        for previous in self.checkpoints:
            old = json.loads(Path(previous).read_text(encoding='utf-8'))
            if old['kind'] == kind and old['role'] == role and old['progress']['status'] in {'started', 'failed'}:
                previous_points.append(previous)
        path = self.directory / ('checkpoint_' + uuid.uuid4().hex + '.json')
        body = redact_credentials(json_value({**payload, 'connection': self.connections.get(role)}))
        self.save(path, {'version': CHECKPOINT_VERSION, 'run_id': self.run_id, 'kind': kind,
            'role': role, 'scope': scope, 'payload': body, 'payload_hash': digest(body),
            'code_versions': self.versions, 'progress': {'status': 'started'}})
        self.latest = str(path)
        self.checkpoints.append(self.latest)
        for previous in previous_points:
            self.progress(previous, status='superseded')
        self.write('checkpoint_saved', path=self.latest, kind=kind, role=role)
        return self.latest

    def progress(self, path, **progress):
        target = Path(path)
        if target.parent != self.directory:
            raise ValueError('Checkpoint progress must belong to this execution.')
        data = json.loads(target.read_text(encoding='utf-8'))
        data['progress'].update(progress)
        self.save(target, data)

    def summary(self):
        pending = [path for path in self.checkpoints if json.loads(Path(path).read_text(encoding='utf-8'))['progress']['status'] in {'started', 'failed'}]
        return {'version': CHECKPOINT_VERSION, 'run_id': self.run_id,
            'exchanges': str(self.directory / 'exchanges.jsonl'), 'resume_checkpoint': pending[-1] if pending else None,
            'checkpoints': self.checkpoints,
            'code_versions': self.versions}

    def close(self):
        try:
            self.save(self.directory / 'manifest.json', self.summary())
        finally:
            _active_capture.reset(self.token)
            self.stream.close()


def load_checkpoint(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(data, dict) and data.get('version') != CHECKPOINT_VERSION:
        target = data.get('capture', {}).get('resume_checkpoint')
        if not target:
            raise ValueError('This artifact has no phase checkpoint. Earlier artifacts need an explicit saved-candidate review, never an automatic full rerun.')
        path = Path(target).resolve()
        data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('version') != CHECKPOINT_VERSION or data.get('kind') not in {
            'review', 'specialist', 'planning', 'sentiment', 'visual'}:
        raise ValueError('Unsupported phase checkpoint.')
    if data.get('payload_hash') != digest(data.get('payload')):
        raise ValueError('Checkpoint payload has changed; its input identity cannot be verified.')
    if data.get('checkpoint_hash') != digest({key: value for key, value in data.items() if key != 'checkpoint_hash'}):
        raise ValueError('Checkpoint scope or progress has changed; its identity cannot be verified.')
    if data.get('progress', {}).get('status') not in {'started', 'failed'}:
        raise ValueError('This checkpoint completed or was superseded. Select the failed phase checkpoint explicitly.')
    data['source_path'] = str(path)
    return data
