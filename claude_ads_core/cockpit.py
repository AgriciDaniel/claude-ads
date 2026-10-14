"""Read-only, artifact-backed cockpit and three explicit local actions.

Unregistered files are never parsed. Evidence freshness is ledger evaluation,
not live verification. Authorization fingerprints bind exact registered bytes,
metadata, manifest, evaluation date and policy, excluding generated outputs.
"""
from __future__ import annotations

import csv
import io
import ipaddress
import re
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .cockpit_contracts import validate_cockpit_contract
from .cockpit_io import CockpitError, Directory, decode, digest, encode, require_safe_io
from .contracts import CONTRACT_NAMES, PLATFORMS, validate_contract
from . import control_registry as cr
from .report_policy import validate_report_bundle_policy
from .reporting import _redact_value, _render_html_layout, _render_markdown_layout

INTERFACE_VERSION = '1.0.0'
OPERATIONS = ('validate-input', 'validate-run', 'render-report')
POLICY_FILES = ('control-registry.json', 'scoring-profiles.json', 'claim-ledger.json',
                'source-ledger.json', 'data-lifecycle-policy.json')
ARTIFACT_CONTRACTS = {'report-bundle', 'audit-worker-result', 'orchestration-run',
                      'orchestration-task', 'orchestration-result', 'orchestration-gate'}
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
_PATH_TEXT = re.compile(r'(?<!\w)(?:[A-Za-z]:[\\/][^\s<>"\']+|/(?:[^\s<>"\']+))')
# Web addresses are display text, not filesystem paths. file: URLs are not matched.
_URL_TEXT = re.compile(r'(?i)\bhttps?://[^\s<>"\']+')
# Same redaction style as reporting._redact_text, for provider-style keys such as sk-...
_API_KEY = re.compile(r'(?<![\w-])sk-[A-Za-z0-9_-]{20,}')
_PHONE = re.compile(r'(?<!\w)(?:\d{4}-\d{2}-\d{2}(?!\d)|\+?\d[\d ()-]{7,}\d(?!\w))')
RENDER_TIMEOUT_SECONDS = 20


def _redact_paths(value):
    """Redact filesystem paths while leaving http and https addresses readable."""
    pieces, position = [], 0
    for url in _URL_TEXT.finditer(value):
        pieces.append(_PATH_TEXT.sub('[REDACTED PATH]', value[position:url.start()]))
        pieces.append(url[0])
        position = url.end()
    pieces.append(_PATH_TEXT.sub('[REDACTED PATH]', value[position:]))
    return ''.join(pieces)


def _safe_text(value):
    value = str(value)
    value = re.sub(r'[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]', ' ', value)
    value = _redact_value(value)
    value = _API_KEY.sub('[REDACTED]', value)
    value = _redact_paths(value)
    value = _PHONE.sub(lambda m: '[REDACTED NUMBER]' if len(re.sub(r'\D', '', m[0])) >= 10 else m[0], value)
    return value[:2048]


def _display(value, *, identities=()):
    if isinstance(value, dict):
        shown = {}
        for key, item in _redact_value(value).items():
            label = _display(str(key), identities=identities)
            # Distinct keys can redact to one label; never drop an entry.
            number = 2
            unique = label
            while unique in shown:
                unique = f'{label} ({number})'
                number += 1
            shown[unique] = _display(item, identities=identities)
        return shown
    if isinstance(value, list):
        return [_display(v, identities=identities) for v in value]
    if isinstance(value, str):
        for identity in sorted((s for s in identities if s), key=len, reverse=True):
            value = value.replace(identity, '[REDACTED ACCOUNT]')
        return _safe_text(value)
    return value


def _run_id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise CockpitError('Invalid run ID')
    return value


def _now():
    return datetime.now(timezone.utc)


def _timestamp(instant):
    return instant.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def _instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('offset required')
    return result.astimezone(timezone.utc)


def _evaluation(as_of):
    if as_of is None:
        return _now(), False
    try:
        if isinstance(as_of, datetime):
            raise ValueError('date required')
        result = date.fromisoformat(str(as_of))
        if str(result) != str(as_of):
            raise ValueError('canonical date required')
        return datetime.combine(result, datetime.max.time(), tzinfo=timezone.utc), True
    except ValueError as exc:
        raise CockpitError('Evaluation override must be YYYY-MM-DD') from exc


def _validate(name, value):
    try:
        validate_contract(name, value)
    except ValueError as exc:
        # Contract messages can contain attacker-controlled IDs and input text.
        raise CockpitError('Registered document failed its declared contract') from exc


def _lifecycle(manifest, instant, lifecycle_policy):
    lifecycle = manifest['data_lifecycle']
    retention = lifecycle['retention']
    try:
        started = _instant(manifest['started_at'])
        deadline = _instant(retention['delete_after']) if retention['delete_after'] else None
        if deadline is not None and deadline < started + timedelta(seconds=retention['minimum_seconds']):
            raise CockpitError('Lifecycle retention deadline precedes the declared minimum')
        if started > instant:
            raise CockpitError('Run starts after the evaluation date')
        if deadline is not None and instant >= deadline:
            raise CockpitError('Lifecycle retention deadline has passed; operator review required')
        if lifecycle['deletion']['status'] == 'verified':
            raise CockpitError('Lifecycle records verified deletion; client processing is unavailable')
        if manifest['privacy_class'] == 'restricted':
            raise CockpitError('Restricted lifecycle prohibits persisted cockpit processing')
        if lifecycle['incident']['status'] in {'open', 'contained'}:
            raise CockpitError('Lifecycle incident requires owner review before client processing')
        rows = {r['id']: r for r in lifecycle_policy['classifications']}
        policy = rows[manifest['privacy_class']]
        if retention['minimum_seconds'] < policy['minimum_retention_seconds']:
            raise CockpitError('Lifecycle does not satisfy the policy minimum')
        for key, field in [('at_rest', 'encryption_at_rest_required'), ('in_transit', 'encryption_in_transit_required')]:
            if policy[field] and lifecycle['encryption'][key] != 'verified':
                raise CockpitError('Lifecycle lacks required encryption evidence')
    except (KeyError, ValueError, OverflowError, TypeError) as exc:
        if isinstance(exc, CockpitError):
            raise
        raise CockpitError('Invalid lifecycle policy or dates') from exc


@contextmanager
def _policy(root):
    with Directory(root) as directory:
        raw = {name: directory.read('control-plane/manifests/' + name) for name in POLICY_FILES}
        payloads = {name: decode(data) for name, data in raw.items()}
        try:
            registry = payloads['control-registry.json']
            profiles = payloads['scoring-profiles.json']
            if registry['schema_version'] != '1.0.0' or registry['registry_version'] != '1.0.0' or profiles['schema_version'] != '1.0.0' or profiles['profile_version'] != '1.0.0':
                raise ValueError('version')
            claims = cr._verified_claims(payloads['claim-ledger.json'])
            sources = cr._known_sources(payloads['source-ledger.json'])
            entries = tuple(cr._validate_entry(item, i, claims, sources) for i, item in enumerate(registry['controls']))
            keys = {(e.platform, e.control_id): e for e in entries}
            if len(keys) != len(entries) or {e.platform for e in entries} != PLATFORMS:
                raise ValueError('coverage')
            typed_profiles = tuple(cr._validate_profile(p, i, keys) for i, p in enumerate(profiles['profiles']))
            if len(typed_profiles) != len(PLATFORMS) or {p.platform for p in typed_profiles} != PLATFORMS:
                raise ValueError('profiles')
            if payloads['data-lifecycle-policy.json']['schema_version'] != '1.0.0':
                raise ValueError('lifecycle version')
            for ledger in ('claim-ledger.json', 'source-ledger.json'):
                if payloads[ledger]['schema_version'] != '1.0.0':
                    raise ValueError('ledger version')
            state = {'registry': cr.ControlRegistry(entries, typed_profiles), 'payloads': payloads,
                     'fingerprint': digest(encode({name: digest(data) for name, data in raw.items()})),
                     'directory': directory}
        except (KeyError, ValueError, TypeError) as exc:
            raise CockpitError('Policy registry or ledger is invalid; repair trusted policy state') from exc
        yield state
        directory.verify()


def _source_state(row, today):
    try:
        retrieved = date.fromisoformat(row['retrieved_at'])
        due = date.fromisoformat(row['refresh_due'])
        if retrieved > today or due < retrieved:
            return 'provisional'
        return 'stale' if due < today else 'current'
    except (ValueError, TypeError, KeyError):
        return 'missing'


def _claim_state(row, sources, today):
    if row.get('verdict') == 'demoted':
        return 'demoted'
    if row.get('classification') == 'contested' or row.get('verdict') == 'contested':
        return 'contested'
    refs = row.get('source_ids')
    if not isinstance(refs, list) or not refs or any(ref not in sources for ref in refs):
        return 'missing'
    try:
        verified = date.fromisoformat(row['last_verified'])
        due = date.fromisoformat(row['refresh_due'])
        if verified > today or due < verified:
            return 'provisional'
    except (ValueError, TypeError, KeyError):
        return 'missing'
    states = [sources[ref] for ref in refs]
    if due < today or 'stale' in states:
        return 'stale'
    if 'missing' in states:
        return 'missing'
    if any(state != 'current' for state in states) or row.get('verdict') != 'verified':
        return 'provisional'
    return 'current'


def _public_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        url = urlsplit(value)
        host = url.hostname
        if url.scheme != 'https' or not host or url.username or url.password or url.query or url.fragment or url.port not in {None, 443}:
            return None
        if host.lower() in {'localhost', 'localhost.localdomain'} or host.lower().endswith(('.local', '.localhost', '.internal')):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            if '.' not in host:
                return None
        return value if _redact_value(value) == value and not re.search(r'[\x00-\x20\x7f-\x9f]', value) else None
    except ValueError:
        return None


def _evidence(policy, today):
    registry = policy['registry']
    raw_sources = policy['payloads']['source-ledger.json']['sources']
    raw_claims = policy['payloads']['claim-ledger.json']['claims']
    states = {r['id']: _source_state(r, today) for r in raw_sources}
    claims = []
    sources = []
    for row in raw_claims:
        controls = sorted({e.control_id for e in registry.entries if row['id'] in e.source_claim_ids})
        claims.append({'id': _safe_text(row['id']), 'statement': _safe_text(row.get('statement', '')),
                       'verdict': _safe_text(row.get('verdict', 'unknown')), 'classification': _safe_text(row.get('classification', 'unknown')),
                       'last_verified': _valid_date(row.get('last_verified')), 'refresh_due': _valid_date(row.get('refresh_due')),
                       'effective_status': _claim_state(row, states, today), 'source_ids': [_safe_text(s) for s in row.get('source_ids', [])], 'control_ids': controls})
    for row in raw_sources:
        claim_ids = sorted({r['id'] for r in raw_claims if row['id'] in r.get('source_ids', [])})
        controls = sorted({e.control_id for e in registry.entries if row['id'] in e.control_definition['source_ids'] or any(c in claim_ids for c in e.source_claim_ids)})
        sources.append({'id': _safe_text(row['id']), 'title': _safe_text(row.get('title', '')),
                        'locator': _public_url(row.get('locator')), 'retrieved_at': _valid_date(row.get('retrieved_at')),
                        'refresh_due': _valid_date(row.get('refresh_due')), 'confidence': _safe_text(row.get('confidence', 'unknown')),
                        'status': states[row['id']], 'claim_ids': claim_ids, 'control_ids': controls})
    return claims, sources


def _valid_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        return None


def _account_key(account):
    # Stable on purpose so compare can match the same account across runs, so it
    # is an unsalted SHA-256 of {platform, account_id}. It is not anonymization:
    # equal keys link the same account across runs, and a short or numeric
    # account ID can be recovered by brute force. Never persist or publish it as
    # an identifier; snapshots are not persisted by the core.
    return digest(encode({'platform': account['account']['platform'], 'account_id': account['account']['account_id']}))


def _input_validation(row, data, registry):
    if data is None:
        return 'missing', ['Registered input is missing'], None
    if row['kind'] == 'json':
        if row['contract'] is None:
            return 'unchecked', ['No input contract declared'], None
        if row['contract'] not in CONTRACT_NAMES:
            return 'invalid', ['Unknown declared input contract'], None
        try:
            value = decode(data)
            _validate(row['contract'], value)
            if row['contract'] == 'account-snapshot':
                if value['account']['platform'] != row['platform']:
                    raise CockpitError('Input platform conflicts with its index')
            if row['contract'] == 'report-bundle':
                validate_report_bundle_policy(value, registry)
            return 'valid', ['Declared contract validated locally'], value
        except (ValueError, TypeError):
            return 'invalid', ['Input does not satisfy its declared contract'], None
    if row['contract'] != 'account-snapshot' or row['platform'] not in PLATFORMS:
        return 'unchecked', ['CSV requires explicit account-snapshot contract and platform'], None
    try:
        from .adapters.csv_export import GenericCSVExportAdapter, REQUIRED_COLUMNS, MAX_EXPORT_COLUMNS, MAX_EXPORT_ROWS
        adapter = GenericCSVExportAdapter(row['platform'])
        reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')), strict=True)
        headers = reader.fieldnames or []
        if len(headers) > MAX_EXPORT_COLUMNS or len(headers) != len(set(headers)) or not set(REQUIRED_COLUMNS) <= set(headers):
            raise ValueError('headers')
        rows = []
        for number, record in enumerate(reader, 2):
            if number > MAX_EXPORT_ROWS + 1 or None in record:
                raise ValueError('bounds')
            rows.append(adapter._normalize_row(record, number))
        if not rows:
            raise ValueError('empty')
        value = adapter._build_snapshot(rows)
        return 'valid', ['Portable CSV normalized and validated locally'], value
    except (ValueError, UnicodeError, csv.Error):
        return 'invalid', ['CSV failed the declared portable export contract'], None


def _chains(packets, run_id, instant):
    runs = [p for kind, p in packets if kind == 'orchestration-run']
    tasks = [p for kind, p in packets if kind == 'orchestration-task']
    results = [p for kind, p in packets if kind == 'orchestration-result']
    gates = [p for kind, p in packets if kind == 'orchestration-gate']
    if not packets:
        return {}
    if len(runs) != 1 or runs[0]['run_id'] != run_id:
        raise CockpitError('Orchestration requires exactly one matching run packet')
    if any(p['run_id'] != run_id for _, p in packets):
        raise CockpitError('Orchestration subject does not match the selected run')
    for _, packet in packets:
        timestamp = packet.get('created_at', packet.get('evaluated_at'))
        if timestamp is not None and _instant(timestamp) > instant:
            raise CockpitError('Orchestration evidence is future dated')
    by_task = {t['task_id']: t for t in tasks}
    by_result = {r['result_id']: r for r in results}
    if len(by_task) != len(tasks) or len(by_result) != len(results):
        raise CockpitError('Duplicate orchestration identities')
    child = {}
    for result in results:
        task = by_task.get(result['task_id'])
        if not task or task['role'] != result['role']:
            raise CockpitError('Orchestration result does not match a declared task and role')
        previous = result['supersedes']
        if previous is not None:
            prior = by_result.get(previous)
            if not prior or prior['task_id'] != result['task_id'] or prior['run_id'] != result['run_id'] or prior['role'] != result['role'] or _instant(prior['created_at']) >= _instant(result['created_at']) or previous in child:
                raise CockpitError('Invalid orchestration supersedes chain')
            child[previous] = result['result_id']
    latest = {}
    for result in results:
        if result['result_id'] not in child:
            if result['task_id'] in latest:
                raise CockpitError('Orchestration task has multiple current results')
            latest[result['task_id']] = result
    for task in tasks:
        if any(dependency not in by_task or dependency == task['task_id'] for dependency in task['depends_on']):
            raise CockpitError('Orchestration task dependency is missing or self-referential')
    for gate in gates:
        if any(t not in by_task for t in gate['required_task_ids']) or any(r not in by_result for r in gate['evaluated_result_ids']):
            raise CockpitError('Orchestration gate references missing evidence')
    from .orchestration import evaluate_artifact_gate
    for gate in gates:
        expected = evaluate_artifact_gate(runs[0], tasks, results, gate_id=gate['gate_id'], stage=gate['stage'], required_task_ids=gate['required_task_ids'], evaluated_at=gate['evaluated_at'])
        if gate != expected:
            raise CockpitError('Orchestration gate disagrees with canonical artifact evaluation')
    return latest


_HISTORY_BOUNDS = ('Generated history exceeds its bounds (at most 1000 listed artifacts including registered ones, 64 MiB); '
                   'archive older receipts from cockpit/receipts and their reports from cockpit/reports outside the run, then refresh')


def _history(directory, run_id, slots=1000):
    """Project only canonical receipts and their hash-bound generated outputs.

    Receipts are schema, subject and time checked local records and are not
    hash-bound. Report outputs named by a receipt are hash and size bound.
    `slots` is what remains of the snapshot artifact limit after registered ones.
    """
    receipts, artifacts, action_ids, output_paths = [], [], set(), set()
    total_bytes = 0
    for name in directory.list_files('cockpit/receipts'):
        if not name.endswith('.json') or not _ID.fullmatch(name[:-5]):
            raise CockpitError('Generated receipt filename is invalid')
        path = 'cockpit/receipts/' + name
        data = directory.read(path)
        receipt = decode(data)
        try:
            validate_cockpit_contract('cockpit-action-receipt', receipt)
        except ValueError as exc:
            raise CockpitError('Generated receipt failed its canonical contract') from exc
        action_id = receipt['action_id']
        if receipt['run_id'] != run_id or name != action_id + '.json' or action_id in action_ids:
            raise CockpitError('Generated receipt subject or identity is invalid')
        if _instant(receipt['finished_at']) > _now():
            raise CockpitError('Generated receipt is future dated')
        if any(_safe_text(text) != text for text in receipt['diagnostics']):
            raise CockpitError('Generated receipt diagnostic contains unsafe display text')
        action_ids.add(action_id)
        total_bytes += len(data)
        if total_bytes > 64 * 1024 * 1024:
            raise CockpitError(_HISTORY_BOUNDS)
        for output in receipt['outputs']:
            prefix = 'cockpit/reports/' + action_id + '/'
            tail = output['path'].removeprefix(prefix)
            if receipt['operation'] != 'render-report' or not output['path'].startswith(prefix) or not re.fullmatch(r'report-[1-9][0-9]{0,3}\.(md|html|pdf)', tail) or output['path'] in output_paths:
                raise CockpitError('Generated output subject or path is invalid')
            contents = directory.read(output['path'])
            if len(contents) != output['size'] or digest(contents) != output['sha256']:
                raise CockpitError('Generated report hash or byte size mismatch')
            total_bytes += len(contents)
            if total_bytes > 64 * 1024 * 1024 or len(artifacts) >= slots:
                raise CockpitError(_HISTORY_BOUNDS)
            output_paths.add(output['path'])
            artifacts.append({**output, 'kind': 'rendered-report'})
        # Receipts already appear once in artifacts below; count them only there.
        if total_bytes > 64 * 1024 * 1024 or len(artifacts) >= slots:
            raise CockpitError(_HISTORY_BOUNDS)
        row = {'path': path, 'sha256': digest(data), 'size': len(data)}
        receipts.append({**row, 'receipt': receipt})
        artifacts.append({**row, 'kind': 'cockpit-action-receipt'})
    return receipts, artifacts


def _collect(directory, run_id, policy, instant, override=False, *, documents=None):
    if documents is None and directory.read('.cockpit-publishing', missing=True) is not None:
        raise CockpitError('Interrupted publication requires recovery from preserved producer metadata')
    raw_manifest = directory.read('manifest.json') if documents is None else encode(documents[0])
    try:
        raw_index = directory.read('cockpit.json') if documents is None else encode(documents[1])
    except CockpitError as exc:
        raise CockpitError('Incompatible run: cockpit.json is required and must be safe') from exc
    manifest, index = decode(raw_manifest), decode(raw_index)
    _validate('run-manifest', manifest)
    try:
        validate_cockpit_contract('cockpit-index', index)
    except ValueError as exc:
        raise CockpitError('Invalid strict cockpit index') from exc
    for row in index['inputs'] + index['artifacts']:
        for field in ('id', 'path', 'contract'):
            if row.get(field) is not None and _safe_text(row[field]) != row[field]:
                raise CockpitError('Index metadata contains unsafe display text')
    if manifest['run_id'] != run_id or index['run_id'] != run_id:
        raise CockpitError('Run identity does not match selected directory')
    if manifest['completeness'] == 'complete' and (not manifest['worker_status'] or any(s not in {'completed', 'skipped'} for s in manifest['worker_status'].values())):
        raise CockpitError('Complete run has unfinished or failed required workers')
    for worker in manifest['worker_status']:
        _run_id(worker)
    _lifecycle(manifest, instant, policy['payloads']['data-lifecycle-policy.json'])
    registry = policy['registry']
    inputs, artifacts, reports, worker_results, packets, identities, accounts = [], [], [], {}, [], [], {}
    exact_refs = {}
    total_bytes = len(raw_manifest) + len(raw_index)
    for row in index['inputs']:
        data = directory.read(row['path'], missing=True)
        total_bytes += len(data) if data is not None else 0
        if total_bytes > 64 * 1024 * 1024:
            raise CockpitError('Registered run exceeds the aggregate byte limit')
        if data is not None and digest(data) != row['sha256']:
            raise CockpitError('Registered input hash mismatch; refresh producer evidence')
        exact_refs[row['path']] = None if data is None else digest(data)
        state, details, value = _input_validation(row, data, registry)
        inputs.append({**row, 'validation': state, 'details': details})
        if value and row['contract'] == 'account-snapshot':
            platform = value['account']['platform']
            key = _account_key(value)
            candidate = {'platform': platform, 'account_key': key, 'window': value['window'], 'currency': value['currency']}
            if platform in accounts and accounts[platform] != candidate:
                raise CockpitError('Multiple input account identities, windows or currencies conflict')
            accounts[platform] = candidate
            identities.append(value['account']['account_id'])
    for row in index['artifacts']:
        if row['contract'] not in ARTIFACT_CONTRACTS:
            raise CockpitError('Unsupported registered artifact contract')
        data = directory.read(row['path'])
        total_bytes += len(data)
        if total_bytes > 64 * 1024 * 1024:
            raise CockpitError('Registered run exceeds the aggregate byte limit')
        if digest(data) != row['sha256']:
            raise CockpitError('Registered artifact hash mismatch; refresh producer evidence')
        exact_refs[row['path']] = digest(data)
        value = decode(data)
        _validate(row['contract'], value)
        artifacts.append({'path': row['path'], 'kind': row['contract'], 'sha256': row['sha256'], 'size': len(data)})
        if row['contract'] == 'report-bundle':
            try:
                validate_report_bundle_policy(value, registry)
            except ValueError as exc:
                raise CockpitError('Report disagrees with canonical registry policy') from exc
            if value['run_manifest'] != manifest:
                raise CockpitError('Report manifest differs from the selected run manifest')
            account = value['account_snapshot']
            platform, key = account['account']['platform'], _account_key(account)
            candidate = {'platform': platform, 'account_key': key, 'window': account['window'], 'currency': account['currency']}
            if platform in accounts and accounts[platform] != candidate:
                raise CockpitError('Report and input account identities or windows differ')
            if any(r['account_snapshot']['account']['platform'] == platform for r in reports):
                raise CockpitError('Multiple reports for one platform are ambiguous')
            accounts[platform] = candidate
            identities.append(account['account']['account_id'])
            reports.append(value)
        elif row['contract'] == 'audit-worker-result':
            platform = value['platform']
            if platform in worker_results:
                raise CockpitError('Multiple worker results for one platform are ambiguous')
            try:
                registry.validate_findings(platform, value['findings'])
            except ValueError as exc:
                raise CockpitError('Worker findings disagree with canonical registry') from exc
            worker_results[platform] = value
        else:
            packets.append((row['contract'], value))
    latest = _chains(packets, run_id, instant)
    indexed_by_id = {r['id']: r for r in index['inputs'] + index['artifacts']}
    for kind, packet in packets:
        if kind == 'orchestration-run' and (packet['privacy_class'] != manifest['privacy_class'] or packet['data_lifecycle'] != manifest['data_lifecycle']):
            raise CockpitError('Orchestration lifecycle differs from the selected manifest')
        if kind == 'orchestration-task':
            for reference in packet['inputs']:
                declared = indexed_by_id.get(reference['artifact_id'])
                if declared is None or declared['sha256'] != reference['sha256'] or exact_refs.get(declared['path']) != reference['sha256']:
                    raise CockpitError('Orchestration task input does not match registered evidence')
    for _, packet in packets:
        if packet.get('artifact_type') == 'orchestration-result':
            for output in packet['output_artifacts']:
                declared = next((r for r in index['inputs'] + index['artifacts'] if r['path'] == output['path']), None)
                if output['path'] not in exact_refs or exact_refs[output['path']] != output['sha256'] or declared is None or declared['contract'] != output['contract']:
                    raise CockpitError('Orchestration output does not match an indexed artifact')
    claims, sources = _evidence(policy, instant.date())
    claim_by_id = {c['id']: c for c in claims}
    source_by_id = {s['id']: s for s in sources}
    entries = {(e.platform, e.control_id): e for e in registry.entries}
    canonical_findings = {}
    for report in reports:
        platform = report['account_snapshot']['account']['platform']
        for finding in report['findings']:
            canonical_findings[(platform, finding['control_id'])] = finding
    for platform, result in worker_results.items():
        if platform not in manifest['worker_status']:
            raise CockpitError('Worker result has no declared manifest worker')
        status = manifest['worker_status'][platform]
        if status == 'completed' and result['status'] != 'ok':
            raise CockpitError('Completed worker conflicts with its registered result')
        if status == 'failed' and result['status'] == 'ok':
            raise CockpitError('Failed worker conflicts with its registered result')
        for finding in result['findings']:
            key = (platform, finding['control_id'])
            if key in canonical_findings and canonical_findings[key] != finding:
                raise CockpitError('Report and worker findings disagree')
            canonical_findings[key] = finding
    findings = []
    for (platform, control_id), finding in sorted(canonical_findings.items()):
        entry = entries[(platform, control_id)]
        claim_ids = list(entry.source_claim_ids)
        source_ids = sorted(set(entry.control_definition['source_ids']) | {s for c in claim_ids for s in claim_by_id.get(c, {}).get('source_ids', [])})
        states = [claim_by_id.get(c, {}).get('effective_status', 'missing') for c in claim_ids] + [source_by_id.get(s, {}).get('status', 'missing') for s in source_ids]
        state = next((s for s in ('missing', 'demoted', 'contested', 'stale', 'provisional') if s in states), 'current') if claim_ids and source_ids else 'missing'
        if finding.get('source_classification') == 'contested':
            state = 'contested'
        findings.append({'platform': platform, 'account_key': accounts.get(platform, {}).get('account_key'),
                         'finding': _display(finding, identities=identities), 'control_title': _safe_text(entry.intent)[:200], 'severity': entry.control_definition['severity'],
                         'claim_ids': claim_ids, 'source_ids': source_ids, 'evidence_status': state})
    workers = []
    missing_results = []
    for worker, status in sorted(manifest['worker_status'].items()):
        result = worker_results.get(worker) or latest.get(worker)
        if status == 'completed' and result is None and not any(r['account_snapshot']['account']['platform'] == worker for r in reports):
            missing_results.append(worker)
        workers.append({'id': worker, 'platform': worker if worker in PLATFORMS else None, 'status': status,
                        'result_status': result.get('status') if result else None,
                        **{key: _display(result.get(key, []), identities=identities) if result else [] for key in ('missing_inputs', 'contradictions', 'stale_sources', 'recovery_hints')}})
    statuses = {w['status'] for w in workers}
    result_statuses = {w['result_status'] for w in workers}
    if 'running' in statuses:
        workflow = 'running'
    elif 'pending' in statuses:
        workflow = 'pending'
    elif 'failed' in statuses or 'failed' in result_statuses:
        workflow = 'failed'
    elif result_statuses & {'blocked', 'needs_input'}:
        workflow = 'blocked'
    elif missing_results or not workers:
        workflow = 'unknown'
    else:
        workflow = 'completed'
    limitations = ['Evidence freshness evaluates dated ledgers; no live verification was performed',
                   'Local checks do not establish advertising truth or release readiness']
    if override:
        limitations.append('Evaluation-date override: ' + instant.date().isoformat())
    if missing_results:
        limitations.append('Completed worker declarations lack registered result evidence')
    if any(i['validation'] in {'invalid', 'missing', 'unchecked'} for i in inputs):
        limitations.append('Some indexed inputs are invalid, missing or unchecked')
    scoring = []
    for platform in sorted(set(accounts) | set(worker_results)):
        values = [f for (p, _), f in canonical_findings.items() if p == platform]
        score = registry.score_platform(platform, values)
        scoring.append({'platform': platform, 'health_score': score.health_score, 'evidence_coverage': score.evidence_coverage, 'status': score.status, 'profile_status': registry.profile_for(platform).status})
    fingerprint = digest(encode({'manifest': digest(raw_manifest), 'index': digest(raw_index), 'registered': exact_refs,
                                 'policy': policy['fingerprint'], 'evaluation_date': instant.date().isoformat()}))
    permitted = ['validate-run']
    if any(i['contract'] is not None for i in inputs):
        permitted.insert(0, 'validate-input')
    if reports:
        permitted.append('render-report')
    completeness = manifest['completeness']
    if completeness == 'complete' and (missing_results or result_statuses & {'failed', 'blocked', 'needs_input'} or any(row['validation'] != 'valid' for row in inputs)):
        completeness = 'partial'
    receipts, generated = _history(directory, run_id, 1000 - len(artifacts))
    artifacts.extend(generated)
    result = {'schema_version': '1.0.0', 'artifact_type': 'cockpit-snapshot', 'run_id': run_id,
              'evaluated_at': _timestamp(instant), 'fingerprint': fingerprint, 'policy_fingerprint': policy['fingerprint'],
              'privacy_class': manifest['privacy_class'], 'phase': _safe_text(index['phase']) if index['phase'] is not None else None,
              'completeness': completeness, 'workflow_status': workflow, 'workers': workers, 'accounts': list(accounts.values()),
              'findings': findings, 'claims': claims, 'sources': sources, 'inputs': inputs, 'artifacts': artifacts, 'receipts': receipts,
              'scoring': scoring, 'permitted_actions': permitted, 'limitations': limitations, 'comparison': None}
    validate_cockpit_contract('cockpit-snapshot', result)
    return result, reports, manifest, index


def snapshot(runs_root, run_id, policy_root, *, as_of=None):
    """Read only registered, hashed evidence beneath the selected run."""
    _run_id(run_id)
    instant, override = _evaluation(as_of)
    try:
        with _policy(policy_root) as policy, Directory(Path(runs_root) / run_id) as directory, directory.lock():
            result, _, _, _ = _collect(directory, run_id, policy, instant, override)
            directory.verify()
            return result
    except CockpitError:
        raise
    except (ValueError, TypeError, KeyError, OSError, RecursionError, OverflowError) as exc:
        raise CockpitError('Snapshot validation failed; repair registered run evidence') from exc


def compare(runs_root, run_id, baseline_id, policy_root, *, as_of=None):
    """Compare statuses only after proving identical actual account identities."""
    instant, override = _evaluation(as_of)
    _run_id(run_id)
    _run_id(baseline_id)
    try:
        with _policy(policy_root) as policy, Directory(Path(runs_root) / run_id) as current_dir, Directory(Path(runs_root) / baseline_id) as baseline_dir, current_dir.lock(), baseline_dir.lock():
            current, _, current_manifest, current_index = _collect(current_dir, run_id, policy, instant, override)
            baseline, _, baseline_manifest, baseline_index = _collect(baseline_dir, baseline_id, policy, instant, override)
            identities = lambda s: {(a['platform'], a['account_key']) for a in s['accounts']}
            if not identities(current) or identities(current) != identities(baseline):
                raise CockpitError('Comparison requires identical account and platform identities')
            for state in (current, baseline):
                known = {a['platform']: a['account_key'] for a in state['accounts']}
                compared_platforms = {f['platform'] for f in state['findings']} | {w['platform'] for w in state['workers'] if w['platform'] is not None}
                if compared_platforms - known.keys() or any(f['account_key'] != known.get(f['platform']) for f in state['findings']):
                    raise CockpitError('Comparison requires an established account identity for every finding and platform worker')
            differences = []
            if current_manifest['scopes'] != baseline_manifest['scopes']:
                differences.append('Run scope differs; absence does not mean resolved')
            if current['accounts'] != baseline['accounts']:
                differences.append('Data window or currency differs; outcomes are not directly comparable')
            if current_index['inputs'] != baseline_index['inputs']:
                differences.append('Input metadata or evidence hashes differ')
            if current_manifest['started_at'] != baseline_manifest['started_at']:
                differences.append('Runs were captured at different times')
            differences.append('Both runs evaluated against policy ' + current['policy_fingerprint'][:12] + ' on ' + instant.date().isoformat())
            differences.append('Historical capture policy is not recorded by this run index; policy drift cannot be excluded')
            if override:
                differences.append('Explicit evaluation-date override applies to both runs')
            old = {(f['platform'], f['finding']['control_id']): f for f in baseline['findings']}
            new = {(f['platform'], f['finding']['control_id']): f for f in current['findings']}
            changes = []
            for key in sorted(old.keys() | new.keys()):
                a, b = old.get(key), new.get(key)
                before, after = a['finding']['status'] if a else None, b['finding']['status'] if b else None
                if after is None:
                    change = 'not_retested'
                elif before != 'fail' and after == 'fail':
                    change = 'new_failure'
                elif before != 'unknown' and after == 'unknown':
                    change = 'newly_unknown'
                elif before is None:
                    change = 'new_finding'
                else:
                    change = 'unchanged' if before == after else 'status_changed'
                if a and b and (a['finding']['evidence'] != b['finding']['evidence'] or a['evidence_status'] != b['evidence_status']):
                    differences.append('Evidence differs for ' + key[0] + '/' + key[1])
                changes.append({'platform': key[0], 'control_id': key[1], 'change': change, 'baseline_status': before, 'current_status': after})
            current['comparison'] = {'baseline_run_id': baseline_id, 'comparable': current['accounts'] == baseline['accounts'] and current_manifest['scopes'] == baseline_manifest['scopes'], 'differences': differences, 'findings': changes}
            validate_cockpit_contract('cockpit-snapshot', current)
            current_dir.verify()
            baseline_dir.verify()
            return current
    except CockpitError:
        raise
    except (ValueError, TypeError, KeyError, OSError, RecursionError, OverflowError) as exc:
        raise CockpitError('Comparison validation failed') from exc


def _chooser_status(run, name):
    """Chooser status for one run: None when no manifest exists, else completeness or blocked."""
    try:
        if run.read('manifest.json', missing=True) is None:
            return None
        with run.lock():
            manifest = decode(run.read('manifest.json'))
            _validate('run-manifest', manifest)
            if manifest['run_id'] != name:
                raise CockpitError('Run subject mismatch')
            run.verify()
        return manifest['completeness']
    except CockpitError:
        # A directory that holds a manifest is a recognized run. Show it as
        # blocked without any data, so it never looks like "no runs".
        return 'blocked'


def doctor(policy_root, runs_root=None):
    """Probe trusted policy and safe chooser metadata without installing code."""
    from . import __version__
    result = {'interface_version': INTERFACE_VERSION, 'status': 'ok', 'core_version': __version__, 'profiles': [], 'runs': [], 'diagnostics': []}
    try:
        require_safe_io()
    except CockpitError as exc:
        result['status'] = 'blocked'
        result['diagnostics'] = [str(exc)]
        return result
    try:
        with _policy(policy_root) as policy:
            result['profiles'] = [{'platform': p.platform, 'status': p.status, 'disabled_reason': _safe_text(p.disabled_reason) if p.disabled_reason else None} for p in policy['registry'].profiles]
        if runs_root is not None:
            with Directory(runs_root) as root:
                import os
                names = sorted(os.listdir(root.fd))
                if len(names) > 1000:
                    raise CockpitError('Runs chooser exceeds directory limit')
                for name in names:
                    if not _ID.fullmatch(name):
                        continue
                    try:
                        run = Directory(Path(runs_root) / name)
                    except CockpitError:
                        # Not a safely readable directory, so not a run.
                        continue
                    with run:
                        status = _chooser_status(run, name)
                    if status is not None:
                        result['runs'].append({'id': name, 'status': status})
            blocked = sum(1 for row in result['runs'] if row['status'] == 'blocked')
            if blocked:
                result['diagnostics'] = [f'{blocked} run director{"y" if blocked == 1 else "ies"} could not be read safely or failed validation; listed as blocked']
    except (CockpitError, ValueError, OSError, OverflowError, RecursionError):
        result['status'] = 'blocked'
        result['diagnostics'] = ['Trusted policy or runs root is unavailable or invalid']
    return result


def _render_local(report, format, *, close_fds=(), timeout_seconds=None):
    """Run the local renderer in a bounded, disposable POSIX child process."""
    import multiprocessing
    from .cockpit_io import MAX_BYTES
    context = multiprocessing.get_context('fork')
    receiver, sender = context.Pipe(duplex=False)
    def render():
        receiver.close()
        import os
        # A renderer receives a redacted in-memory bundle, never a client root
        # or an inherited action lock that could survive a killed parent.
        for descriptor in close_fds:
            os.close(descriptor)
        try:
            if format == 'pdf':
                from .reporting import _render_pdf_layout, PDFDependencyError
                try:
                    contents = _render_pdf_layout(report)
                except PDFDependencyError:
                    sender.send_bytes(b'blocked')
                    return
            else:
                contents = (_render_markdown_layout(report) if format == 'markdown' else _render_html_layout(report)).encode('utf-8')
            if not isinstance(contents, bytes) or len(contents) > MAX_BYTES:
                sender.send_bytes(b'failed')
            else:
                sender.send_bytes(b'ok:' + contents)
        except KeyboardInterrupt:
            sender.send_bytes(b'interrupted')
        except BaseException:
            sender.send_bytes(b'failed')
        finally:
            sender.close()
    child = context.Process(target=render, daemon=True)
    try:
        child.start()
        sender.close()
        if not receiver.poll(RENDER_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds):
            raise CockpitError('Local renderer exceeded its time limit')
        try:
            message = receiver.recv_bytes(MAX_BYTES + 3)
        except (EOFError, OSError):
            raise CockpitError('Local renderer exited without a complete result') from None
        if message == b'blocked':
            raise CockpitError('Optional PDF renderer or native libraries are unavailable')
        if message == b'interrupted':
            raise KeyboardInterrupt
        if not message.startswith(b'ok:'):
            raise ValueError('Local renderer failed')
        return message[3:]
    finally:
        sender.close()
        receiver.close()
        if child.pid is not None:
            child.join(timeout=0.1)
            if child.is_alive():
                child.terminate()
                child.join(timeout=0.2)
            if child.is_alive():
                child.kill()
                child.join(timeout=0.2)
            child.close()


def action(runs_root, run_id, policy_root, operation, *, expected_fingerprint, input_id=None, format='markdown'):
    """Serialize a fixed local operation and preserve a redacted receipt."""
    _run_id(run_id)
    if operation not in OPERATIONS:
        raise CockpitError('Unsupported cockpit action')
    if not isinstance(expected_fingerprint, str) or not re.fullmatch('[a-f0-9]{64}', expected_fingerprint):
        raise CockpitError('An exact snapshot fingerprint is required')
    if input_id is not None and (not isinstance(input_id, str) or not _ID.fullmatch(input_id)):
        raise CockpitError('Invalid selected input ID')
    action_id = uuid.uuid4().hex
    started = _now()
    with _policy(policy_root) as policy, Directory(Path(runs_root) / run_id) as directory:
        # Evaluate lifecycle before any write. Taking the exclusive lock creates
        # a file, and a refused run (expired, deleted, restricted, incident)
        # must never be written to, not even by a blocked receipt.
        _lifecycle_gate(directory, policy, started)
        with directory.lock(exclusive=True):
            # Close the window between the read above and holding the lock.
            _lifecycle_gate(directory, policy, started)
            return _act(directory, policy, run_id, operation, action_id, started, expected_fingerprint, input_id, format)


def _lifecycle_gate(directory, policy, instant):
    """Raise the read path's lifecycle diagnostic, using only the run manifest."""
    manifest = decode(directory.read('manifest.json'))
    _validate('run-manifest', manifest)
    _lifecycle(manifest, instant, policy['payloads']['data-lifecycle-policy.json'])


def _act(directory, policy, run_id, operation, action_id, started, expected_fingerprint, input_id, format):
    """Run one fixed operation under the exclusive lock and persist its receipt."""
    receipt = {'schema_version': '1.0.0', 'artifact_type': 'cockpit-action-receipt', 'action_id': action_id,
               'run_id': run_id, 'operation': operation, 'started_at': _timestamp(started), 'finished_at': _timestamp(started),
               'outcome': 'blocked', 'input_fingerprint': expected_fingerprint, 'policy_fingerprint': policy['fingerprint'], 'outputs': [], 'diagnostics': []}
    try:
        state, reports, _, _ = _collect(directory, run_id, policy, started)
        if state['fingerprint'] != expected_fingerprint:
            raise CockpitError('Snapshot fingerprint is stale; refresh before acting')
        if operation not in state['permitted_actions']:
            raise CockpitError('Selected action is unavailable for this run')
        directory.verify()
        policy['directory'].verify()
        if operation == 'validate-input':
            selected = [r for r in state['inputs'] if r['id'] == input_id]
            if len(selected) != 1:
                raise CockpitError('Select one indexed input before validation')
            valid = selected[0]['validation'] == 'valid'
            receipt['outcome'] = 'succeeded' if valid else 'failed'
            receipt['diagnostics'] = selected[0]['details']
        elif operation == 'validate-run':
            valid = all(r['validation'] == 'valid' for r in state['inputs']) and state['workflow_status'] not in {'unknown', 'blocked', 'failed'}
            receipt['outcome'] = 'succeeded' if valid else 'failed'
            receipt['diagnostics'] = ['Run contracts, hashes and policy validated locally' if valid else 'Run is structurally readable but contains invalid, missing or incomplete evidence']
        else:
            if format not in {'markdown', 'html', 'pdf'}:
                raise CockpitError('Cockpit render format must be markdown, html or pdf')
            outputs = []
            render_deadline = time.monotonic() + RENDER_TIMEOUT_SECONDS
            for number, report in enumerate(reports):
                # Canonical validation happens before display redaction. The
                # renderer consumes only the validated in-memory bundle and
                # never rereads policy or unregistered client files.
                report = _display(report, identities=[report['account_snapshot']['account']['account_id']])
                report['account_snapshot']['account']['account_id'] = '[REDACTED ACCOUNT]'
                report['account_snapshot']['account']['name'] = 'Account ' + _account_key(reports[number]['account_snapshot'])[:12]
                remaining = render_deadline - time.monotonic()
                if remaining <= 0:
                    raise CockpitError('Local renderer exceeded its time limit')
                rendered = _render_local(report, format, close_fds=(directory.fd, policy['directory'].fd, *directory.lock_fds), timeout_seconds=remaining)
                relative = f'cockpit/reports/{action_id}/report-{number + 1}.' + {'markdown': 'md', 'html': 'html', 'pdf': 'pdf'}[format]
                outputs.append((relative, rendered))
            # Verify all authorization inputs immediately before publication.
            directory.verify()
            policy['directory'].verify()
            for relative, rendered in outputs:
                directory.write(relative, rendered)
                receipt['outputs'].append({'path': relative, 'sha256': digest(rendered), 'size': len(rendered)})
            receipt['outcome'] = 'succeeded'
            receipt['diagnostics'] = ['Rendered from canonical validated JSON; no advertising truth is implied']
        directory.verify()
        policy['directory'].verify()
    except KeyboardInterrupt:
        receipt['outcome'] = 'failed'
        receipt['diagnostics'] = ['Local operation interrupted; completed outputs are recorded without implying success']
    except (ValueError, TypeError, KeyError, OSError, RecursionError, OverflowError) as exc:
        receipt['outcome'] = 'blocked' if isinstance(exc, CockpitError) else 'failed'
        receipt['diagnostics'] = [str(exc) if isinstance(exc, CockpitError) else 'Local operation failed; review registered evidence and retry']
    receipt['finished_at'] = _timestamp(_now())
    receipt['diagnostics'] = [_safe_text(s) for s in receipt['diagnostics']]
    validate_cockpit_contract('cockpit-action-receipt', receipt)
    directory.write(f'cockpit/receipts/{action_id}.json', encode(receipt))
    return receipt


def publish(runs_root, run_id, policy_root, manifest, index, *, expected_fingerprint=None):
    """Atomically publish actual producer metadata under the action lock.

    Producers must have already created immutable indexed artifacts. Both JSON
    documents are validated together before either is replaced. Readers use the
    same advisory lock and reverify every registered byte. Existing manifest
    bytes are preserved in a unique recovery artifact, never overwritten.
    """
    _run_id(run_id)
    with _policy(policy_root) as policy, Directory(Path(runs_root) / run_id) as directory, directory.lock(exclusive=True):
        now = _now()
        old_manifest = directory.read('manifest.json', missing=True)
        old_index = directory.read('cockpit.json', missing=True)
        if old_manifest is not None and old_index is not None:
            current, _, _, _ = _collect(directory, run_id, policy, now)
            if expected_fingerprint is None or current['fingerprint'] != expected_fingerprint:
                raise CockpitError('Publisher requires the current run fingerprint')
        elif expected_fingerprint is not None:
            raise CockpitError('Publisher fingerprint supplied for an uninitialized run')
        result, _, _, _ = _collect(directory, run_id, policy, now, documents=(manifest, index))
        directory.verify()
        policy['directory'].verify()
        identifier = uuid.uuid4().hex
        if old_manifest is not None:
            directory.write(f'cockpit/recovery/{identifier}/manifest.json', old_manifest)
        if old_index is not None:
            directory.write(f'cockpit/recovery/{identifier}/cockpit.json', old_index)
        directory.write('.cockpit-publishing', encode({'publication_id': identifier, 'recovery': f'cockpit/recovery/{identifier}', 'manifest_sha256': digest(encode(manifest)), 'index_sha256': digest(encode(index))}))
        try:
            directory.write('manifest.json', encode(manifest), replace=True)
            directory.write('cockpit.json', encode(index), replace=True)
        except Exception:
            # A failed second rename restores the exact previous pair while
            # retaining recovery bytes. An interrupted process leaves recovery
            # evidence and later validation fails closed on inconsistent pairs.
            if old_manifest is not None:
                directory.write('manifest.json', old_manifest, replace=True)
            if old_index is not None:
                directory.write('cockpit.json', old_index, replace=True)
            if old_manifest is not None and old_index is not None:
                with directory.parent('.cockpit-publishing') as (parent, name):
                    import os
                    os.unlink(name, dir_fd=parent)
            raise
        with directory.parent('.cockpit-publishing') as (parent, name):
            import os
            os.unlink(name, dir_fd=parent)
            os.fsync(parent)
        return {'interface_version': INTERFACE_VERSION, 'run_id': run_id, 'fingerprint': result['fingerprint']}


def create_demo(runs_root, policy_root):
    """Explicitly create isolated synthetic runs and a disabled policy copy."""
    from .cockpit_demo import create_demo as build
    return build(runs_root, policy_root)
