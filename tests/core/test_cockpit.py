"""Local cockpit security, contracts and real artifact-flow checks."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from claude_ads_core.cockpit import (CockpitError, action, compare, create_demo, doctor,
                                     publish, snapshot, _source_state, _claim_state)
from claude_ads_core.cockpit_contracts import (CockpitContractError, validate_cockpit_contract)
from claude_ads_core.cockpit_io import Directory, MAX_BYTES, decode, digest, encode
from claude_ads_core.contracts import PLATFORMS, validate_contract

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Descriptor IO intentionally fails closed on non-POSIX hosts')


@pytest.fixture
def demo(tmp_path, repo_root):
    result = create_demo(tmp_path / 'runs', repo_root)
    return Path(result['runs_root']), Path(result['policy_root'])


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_bytes(encode(value))


def reindex(root, run='demo-current'):
    index = read(root / run / 'cockpit.json')
    for row in index['inputs'] + index['artifacts']:
        path = root / run / row['path']
        if path.exists():
            row['sha256'] = digest(path.read_bytes())
    write(root / run / 'cockpit.json', index)


def change_manifest(root, function, run='demo-current'):
    manifest = read(root / run / 'manifest.json')
    function(manifest)
    write(root / run / 'manifest.json', manifest)
    report = read(root / run / 'report.json')
    report['run_manifest'] = manifest
    write(root / run / 'report.json', report)
    reindex(root, run)


def test_demo_isolated_and_profiles_disabled(demo, repo_root):
    root, policy = demo
    assert policy != repo_root
    result = doctor(policy, root)
    assert result['status'] == 'ok'
    assert {p['platform'] for p in result['profiles']} == PLATFORMS
    assert all(p['status'] == 'disabled' for p in result['profiles'])
    assert {r['id'] for r in result['runs']} == {'demo-current', 'demo-baseline', 'demo-corrected', 'demo-stale', 'demo-needs-input', 'demo-partial', 'demo-showcase'}
    assert snapshot(root, 'demo-current', policy)['workflow_status'] == 'completed'
    assert snapshot(root, 'demo-needs-input', policy)['workflow_status'] == 'running'
    assert snapshot(root, 'demo-stale', policy)['findings'][0]['evidence_status'] == 'stale'
    assert snapshot(root, 'demo-partial', policy)['workflow_status'] == 'failed'
    with pytest.raises(CockpitError, match='fresh'):
        create_demo(root, repo_root)


def test_demo_policy_does_not_change_source(tmp_path, repo_root):
    policy = repo_root / 'control-plane/manifests/scoring-profiles.json'
    before = policy.read_bytes()
    create_demo(tmp_path / 'runs', repo_root)
    assert before == policy.read_bytes()


def test_registered_hash_tampering_is_fatal(demo):
    root, policy = demo
    (root / 'demo-current/account.json').write_text('{}')
    with pytest.raises(CockpitError, match='hash mismatch'):
        snapshot(root, 'demo-current', policy)


def test_artifact_hash_tampering_is_fatal(demo):
    root, policy = demo
    (root / 'demo-current/worker.json').write_text('{}')
    with pytest.raises(CockpitError, match='hash mismatch'):
        snapshot(root, 'demo-current', policy)


def test_missing_input_is_disclosed_and_not_validated(demo):
    root, policy = demo
    (root / 'demo-current/account.json').unlink()
    state = snapshot(root, 'demo-current', policy)
    assert state['inputs'][0]['validation'] == 'missing'
    receipt = action(root, 'demo-current', policy, 'validate-input', input_id='account', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'failed'


def test_missing_artifact_is_fatal(demo):
    root, policy = demo
    (root / 'demo-current/worker.json').unlink()
    with pytest.raises(CockpitError, match='missing'):
        snapshot(root, 'demo-current', policy)


def test_index_is_required(demo):
    root, policy = demo
    (root / 'demo-current/cockpit.json').unlink()
    with pytest.raises(CockpitError, match='Incompatible'):
        snapshot(root, 'demo-current', policy)


@pytest.mark.parametrize('relative', ['../account.json', '/absolute.json', 'a//b.json', 'a/./b.json', 'a/../b.json', 'a\\b.json', 'C:evil.json', 'cockpit/reports/x.json', 'manifest.json'])
def test_unsafe_index_paths_rejected(demo, relative):
    root, policy = demo
    index = read(root / 'demo-current/cockpit.json')
    index['inputs'][0]['path'] = relative
    write(root / 'demo-current/cockpit.json', index)
    with pytest.raises(CockpitError):
        snapshot(root, 'demo-current', policy)


@pytest.mark.parametrize('target', ['account.json', 'worker.json', 'manifest.json', 'cockpit.json'])
def test_symlink_files_rejected(demo, tmp_path, target):
    root, policy = demo
    selected = root / 'demo-current' / target
    outside = tmp_path / 'outside.json'
    outside.write_bytes(selected.read_bytes())
    selected.unlink()
    selected.symlink_to(outside)
    with pytest.raises(CockpitError):
        snapshot(root, 'demo-current', policy)


def test_fifo_and_hardlinks_are_rejected_without_blocking(demo, tmp_path):
    root, policy = demo
    target = root / 'demo-current/account.json'
    target.unlink()
    os.mkfifo(target)
    with pytest.raises(CockpitError, match='regular'):
        snapshot(root, 'demo-current', policy)
    target.unlink()
    source = tmp_path / 'outside'
    source.write_bytes(b'{}')
    os.link(source, target)
    with pytest.raises(CockpitError, match='one link'):
        snapshot(root, 'demo-current', policy)


def test_symlink_root_and_policy_component_rejected(demo, tmp_path):
    root, policy = demo
    link = tmp_path / 'linked'
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(CockpitError):
        snapshot(link, 'demo-current', policy)
    manifest = policy / 'control-plane/manifests/claim-ledger.json'
    outside = tmp_path / 'claims.json'
    outside.write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(outside)
    assert doctor(policy)['status'] == 'blocked'


def test_duplicate_keys_nonfinite_and_size_bounds(demo):
    root, policy = demo
    for value in (b'{"schema_version":"1.0.0","schema_version":"9"}', b'{"bad":NaN}'):
        with pytest.raises(CockpitError):
            decode(value)
    (root / 'demo-current/account.json').write_bytes(b'x' * (MAX_BYTES + 1))
    with pytest.raises(CockpitError, match='bounded'):
        snapshot(root, 'demo-current', policy)


def test_file_substitution_after_read_is_rejected(tmp_path):
    p = tmp_path / 'file.json'
    p.write_bytes(b'{}')
    with Directory(tmp_path) as directory:
        directory.read('file.json')
        p.unlink()
        p.write_bytes(b'{}')
        with pytest.raises(CockpitError, match='changed'):
            directory.verify()


def test_unregistered_files_never_parsed_or_fingerprinted(demo):
    root, policy = demo
    before = snapshot(root, 'demo-current', policy)
    (root / 'demo-current/unregistered.json').write_text('{broken private input')
    after = snapshot(root, 'demo-current', policy)
    assert before['fingerprint'] == after['fingerprint']


def test_unknown_contract_not_inferred_from_valid_content(demo):
    root, policy = demo
    index = read(root / 'demo-current/cockpit.json')
    index['inputs'][0]['contract'] = None
    write(root / 'demo-current/cockpit.json', index)
    assert snapshot(root, 'demo-current', policy)['inputs'][0]['validation'] == 'unchecked'


def test_report_score_and_control_forgery_rejected(demo):
    root, policy = demo
    report = read(root / 'demo-current/report.json')
    report['scoring']['health_score'] = 100
    write(root / 'demo-current/report.json', report)
    reindex(root)
    with pytest.raises(CockpitError, match='canonical'):
        snapshot(root, 'demo-current', policy)


def test_worker_and_report_disagreement_rejected(demo):
    root, policy = demo
    worker = read(root / 'demo-current/worker.json')
    worker['findings'][0]['status'] = 'pass'
    write(root / 'demo-current/worker.json', worker)
    reindex(root)
    with pytest.raises(CockpitError, match='disagree'):
        snapshot(root, 'demo-current', policy)


def test_declared_completion_without_result_becomes_partial(demo):
    root, policy = demo
    change_manifest(root, lambda m: m['worker_status'].update(tracking='completed'))
    state = snapshot(root, 'demo-current', policy)
    assert state['completeness'] == 'partial'
    assert state['workflow_status'] == 'unknown'


def test_future_start_and_expired_retention_block(demo):
    root, policy = demo
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    change_manifest(root, lambda m: m['data_lifecycle']['retention'].update(delete_after=past))
    with pytest.raises(CockpitError, match='deadline'):
        snapshot(root, 'demo-current', policy)


def test_verified_deletion_blocks_without_deleting_client_files(demo):
    root, policy = demo
    change_manifest(root, lambda m: m['data_lifecycle']['deletion'].update(status='verified', verification_artifact_locator='deletion.json'))
    before = (root / 'demo-current/account.json').read_bytes()
    with pytest.raises(CockpitError, match='verified deletion'):
        snapshot(root, 'demo-current', policy)
    assert before == (root / 'demo-current/account.json').read_bytes()


def test_future_and_inverted_support_dates_cannot_be_current():
    today = datetime.now(timezone.utc).date()
    row = {'retrieved_at': today.isoformat(), 'refresh_due': today.isoformat()}
    assert _source_state(row, today) == 'current'
    row['retrieved_at'] = (today + timedelta(days=1)).isoformat()
    assert _source_state(row, today) == 'provisional'
    row['retrieved_at'] = today.isoformat()
    row['refresh_due'] = (today - timedelta(days=1)).isoformat()
    assert _source_state(row, today) == 'provisional'
    row = {'verdict': 'verified', 'source_ids': ['source'], 'last_verified': today.isoformat(), 'refresh_due': today.isoformat()}
    assert _claim_state(row, {'source': 'current'}, today) == 'current'
    assert _claim_state(row, {'source': 'stale'}, today) == 'stale'
    assert _claim_state(row, {}, today) == 'missing'
    row['verdict'] = 'demoted'
    assert _claim_state(row, {'source': 'current'}, today) == 'demoted'


def test_evaluation_override_disclosed_and_fingerprint_bound(demo):
    root, policy = demo
    today = datetime.now(timezone.utc).date()
    state = snapshot(root, 'demo-current', policy, as_of=(today + timedelta(days=1)).isoformat())
    assert any('Evaluation-date override' in s for s in state['limitations'])
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'blocked'
    assert 'stale' in receipt['diagnostics'][0]
    with pytest.raises(CockpitError):
        snapshot(root, 'demo-current', policy, as_of='invalid')


def test_policy_drift_invalidates_authorization(demo):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    p = policy / 'control-plane/manifests/source-ledger.json'
    payload = read(p)
    payload['generated_at'] = '2026-01-01'
    write(p, payload)
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'blocked'
    assert receipt['policy_fingerprint'] != state['policy_fingerprint']


@pytest.mark.parametrize('format', ['markdown', 'html'])
def test_render_outputs_and_receipts_preserved_excluded_from_fingerprint(demo, format):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    receipts = [action(root, 'demo-current', policy, 'render-report', format=format, expected_fingerprint=state['fingerprint']) for _ in range(2)]
    assert all(r['outcome'] == 'succeeded' for r in receipts)
    assert receipts[0]['outputs'][0]['path'] != receipts[1]['outputs'][0]['path']
    for receipt in receipts:
        saved = read(root / 'demo-current/cockpit/receipts' / (receipt['action_id'] + '.json'))
        assert saved == receipt
        output = receipt['outputs'][0]
        data = (root / 'demo-current' / output['path']).read_bytes()
        assert output['sha256'] == digest(data) and output['size'] == len(data)
        assert b'synthetic-demo-account' not in data
    assert snapshot(root, 'demo-current', policy)['fingerprint'] == state['fingerprint']


def test_pdf_missing_dependency_records_blocked_receipt(demo, monkeypatch):
    root, policy = demo
    import claude_ads_core.reporting as reporting
    original = reporting.importlib.import_module
    def missing(name):
        if name == 'weasyprint':
            raise ImportError('untrusted detail')
        return original(name)
    monkeypatch.setattr(reporting.importlib, 'import_module', missing)
    state = snapshot(root, 'demo-current', policy)
    receipt = action(root, 'demo-current', policy, 'render-report', format='pdf', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'blocked' and receipt['outputs'] == []
    assert 'untrusted detail' not in str(receipt)


def test_pdf_bytes_use_same_safe_writer(demo, monkeypatch):
    root, policy = demo
    import claude_ads_core.reporting as reporting
    monkeypatch.setattr(reporting, '_render_pdf_layout', lambda report: b'%PDF-1.7\nsynthetic\n')
    state = snapshot(root, 'demo-current', policy)
    receipt = action(root, 'demo-current', policy, 'render-report', format='pdf', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'succeeded'
    assert (root / 'demo-current' / receipt['outputs'][0]['path']).read_bytes().startswith(b'%PDF')


def test_render_failure_records_redacted_receipt(demo, monkeypatch):
    root, policy = demo
    import claude_ads_core.cockpit as cockpit
    def broken(_):
        raise ValueError('password=do-not-print /private/file user@example.com')
    monkeypatch.setattr(cockpit, '_render_markdown_layout', broken)
    state = snapshot(root, 'demo-current', policy)
    receipt = action(root, 'demo-current', policy, 'render-report', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'failed'
    assert 'do-not-print' not in str(receipt) and '/private' not in str(receipt)


def test_control_characters_paths_contacts_secrets_redacted(demo):
    root, policy = demo
    report = read(root / 'demo-current/report.json')
    worker = read(root / 'demo-current/worker.json')
    secret = '\x1b[31m password=private-token user@example.com /private/example +12345678910 synthetic-demo-account'
    for document in (report, worker):
        document['findings'][0]['observation'] = secret
    write(root / 'demo-current/report.json', report)
    write(root / 'demo-current/worker.json', worker)
    reindex(root)
    state = snapshot(root, 'demo-current', policy)
    text = json.dumps(state)
    assert all(s not in text for s in ('private-token', 'user@example.com', '/private/example', '+12345678910', 'synthetic-demo-account', '\\u001b'))


def test_three_action_allowlist_and_mandatory_fingerprint(demo):
    root, policy = demo
    with pytest.raises(CockpitError, match='Unsupported'):
        action(root, 'demo-current', policy, 'apply', expected_fingerprint='0' * 64)
    with pytest.raises(CockpitError, match='fingerprint'):
        action(root, 'demo-current', policy, 'validate-run', expected_fingerprint='')


def test_concurrent_action_is_refused_while_the_lock_is_held(demo):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    with Directory(root / 'demo-current') as directory, directory.lock(exclusive=True):
        with pytest.raises(CockpitError, match='busy'):
            action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'succeeded'


def test_action_lock_recovers_after_the_holding_process_crashes(demo, repo_root):
    root, policy = demo
    run = root / 'demo-current'
    state = snapshot(root, 'demo-current', policy)
    # The child takes the exclusive lock and dies with os._exit, so no context
    # manager or finalizer runs. Only the OS can release the advisory lock.
    code = ("import os,sys;sys.path.insert(0,sys.argv[1]);"
            "from claude_ads_core.cockpit_io import Directory;"
            "d=Directory(sys.argv[2]);c=d.lock(exclusive=True);c.__enter__();"
            "print('locked',flush=True);sys.stdin.readline();os._exit(3)")
    child = subprocess.Popen([sys.executable, '-I', '-c', code, str(repo_root), str(run)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'locked'
        with pytest.raises(CockpitError, match='busy'):
            action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
        assert not (run / 'cockpit').exists()
        child.stdin.write('\n')
        child.stdin.flush()
        assert child.wait(timeout=30) == 3
    finally:
        child.kill()
        child.wait()
        child.stdout.close()
        child.stdin.close()
    assert (run / '.cockpit.lock').is_file()
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'succeeded'


def test_unsafe_output_directory_fails_without_overwrite(demo, tmp_path):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    (root / 'demo-current/cockpit').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(CockpitError, match='history directory'):
        snapshot(root, 'demo-current', policy)
    with pytest.raises(CockpitError):
        action(root, 'demo-current', policy, 'render-report', expected_fingerprint=state['fingerprint'])
    assert not list(tmp_path.glob('reports/*'))


def test_compare_identity_windows_and_absence(demo):
    root, policy = demo
    state = compare(root, 'demo-current', 'demo-baseline', policy)
    assert state['comparison']['findings'][0]['change'] == 'new_failure'
    report = read(root / 'demo-current/report.json')
    worker = read(root / 'demo-current/worker.json')
    report['findings'] = []
    worker['findings'] = []
    write(root / 'demo-current/report.json', report)
    write(root / 'demo-current/worker.json', worker)
    reindex(root)
    state = compare(root, 'demo-current', 'demo-baseline', policy)
    assert state['comparison']['findings'][0]['change'] == 'not_retested'
    account = read(root / 'demo-current/account.json')
    account['account']['account_id'] = 'different-synthetic-account'
    report['account_snapshot'] = account
    write(root / 'demo-current/account.json', account)
    write(root / 'demo-current/report.json', report)
    reindex(root)
    with pytest.raises(CockpitError, match='identities'):
        compare(root, 'demo-current', 'demo-baseline', policy)


def test_compare_window_and_scope_differences_disclosed(demo):
    root, policy = demo
    account = read(root / 'demo-current/account.json')
    report = read(root / 'demo-current/report.json')
    account['window']['start'] = (datetime.now(timezone.utc).date() - timedelta(days=9)).isoformat()
    report['account_snapshot'] = account
    write(root / 'demo-current/account.json', account)
    write(root / 'demo-current/report.json', report)
    change_manifest(root, lambda m: m.update(scopes=['audit', 'google', 'tracking']))
    reindex(root)
    comparison = compare(root, 'demo-current', 'demo-baseline', policy)['comparison']
    assert comparison['comparable'] is False
    assert any('scope differs' in d for d in comparison['differences'])
    assert any('window or currency differs' in d for d in comparison['differences'])


def test_publisher_validates_then_preserves_prior_metadata(demo):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    manifest = read(root / 'demo-current/manifest.json')
    index = read(root / 'demo-current/cockpit.json')
    index['phase'] = 'Actual producer phase'
    result = publish(root, 'demo-current', policy, manifest, index, expected_fingerprint=state['fingerprint'])
    state = snapshot(root, 'demo-current', policy)
    assert result['fingerprint'] == state['fingerprint']
    assert state['phase'] == 'Actual producer phase'
    assert len(list((root / 'demo-current/cockpit/recovery').glob('*/manifest.json'))) == 1
    index['artifacts'][0]['sha256'] = '0' * 64
    before = (root / 'demo-current/cockpit.json').read_bytes()
    with pytest.raises(CockpitError):
        publish(root, 'demo-current', policy, manifest, index, expected_fingerprint=state['fingerprint'])
    assert (root / 'demo-current/cockpit.json').read_bytes() == before


def test_interrupted_publication_fails_closed(demo):
    root, policy = demo
    write(root / 'demo-current/.cockpit-publishing', {'publication_id': 'synthetic-interrupted'})
    with pytest.raises(CockpitError, match='Interrupted'):
        snapshot(root, 'demo-current', policy)


@pytest.mark.parametrize('platform', sorted(PLATFORMS))
def test_all_twelve_profiles_recompute_disabled_canonical_scores(demo, platform):
    root, policy = demo
    run = root / 'demo-current'
    account = read(run / 'account.json')
    account['account']['platform'] = platform
    manifest = read(run / 'manifest.json')
    manifest['adapters'] = [{'platform': platform, 'mode': 'export'}]
    manifest['worker_status'] = {platform: 'completed'}
    worker = read(run / 'worker.json')
    worker.update(platform=platform, findings=[])
    report = read(run / 'report.json')
    report.update(account_snapshot=account, run_manifest=manifest, control_definitions=[], findings=[])
    index = read(run / 'cockpit.json')
    index['inputs'][0]['platform'] = platform
    for name, value in [('account.json', account), ('manifest.json', manifest), ('worker.json', worker), ('report.json', report), ('cockpit.json', index)]:
        write(run / name, value)
    reindex(root)
    scoring = snapshot(root, 'demo-current', policy)['scoring']
    assert scoring == [{'platform': platform, 'health_score': None, 'evidence_coverage': 0.0, 'status': 'insufficient_evidence', 'profile_status': 'disabled'}]


def test_schema_validator_parity_required_unknown_fields_and_literals(demo, repo_root):
    jsonschema = pytest.importorskip('jsonschema')
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    payloads = {'cockpit-index': read(root / 'demo-current/cockpit.json'), 'cockpit-snapshot': state, 'cockpit-action-receipt': receipt}
    for name, payload in payloads.items():
        schema = read(repo_root / 'claude_ads_core/schemas/v1' / (name + '.schema.json'))
        checker = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        validate_cockpit_contract(name, payload)
        checker.validate(payload)
        for key in schema['required']:
            broken = copy.deepcopy(payload)
            del broken[key]
            with pytest.raises(CockpitContractError):
                validate_cockpit_contract(name, broken)
            assert not checker.is_valid(broken)
        for broken in ({**payload, 'unexpected': True}, {**payload, 'schema_version': '9.0.0'}):
            with pytest.raises(CockpitContractError):
                validate_cockpit_contract(name, broken)
            assert not checker.is_valid(broken)
    bad = copy.deepcopy(state)
    bad['findings'][0]['finding']['evidence'] = []
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract('cockpit-snapshot', bad)
    assert not jsonschema.Draft202012Validator(read(repo_root / 'claude_ads_core/schemas/v1/cockpit-snapshot.schema.json')).is_valid(bad)


def add_packet(root, packet, name):
    path = root / 'demo-current' / name
    write(path, packet)
    index = read(root / 'demo-current/cockpit.json')
    index['artifacts'].append({'id': name.removesuffix('.json'), 'path': name, 'contract': packet['artifact_type'], 'sha256': digest(path.read_bytes())})
    write(root / 'demo-current/cockpit.json', index)


def orchestration_packets(root, repo_root):
    templates = read(repo_root / 'tests/fixtures/workflows/valid-artifacts.json')
    run = copy.deepcopy(templates['orchestration-run'])
    task = copy.deepcopy(templates['orchestration-task'])
    result = copy.deepcopy(templates['orchestration-result'])
    manifest = read(root / 'demo-current/manifest.json')
    account = read(root / 'demo-current/cockpit.json')['inputs'][0]
    for packet in (run, task, result):
        packet['run_id'] = 'demo-current'
    run['privacy_class'] = 'public'
    run['data_lifecycle'] = manifest['data_lifecycle']
    task['privacy_class'] = 'public'
    task['inputs'] = [{'artifact_id': 'account', 'sha256': account['sha256']}]
    result['output_artifacts'] = [{'path': 'orun.json', 'contract': 'orchestration-run', 'sha256': digest(encode(run))}]
    return run, task, result


def test_orchestration_latest_supersedes_and_canonical_gate(demo, repo_root):
    root, policy = demo
    from claude_ads_core.orchestration import evaluate_artifact_gate
    run, task, first = orchestration_packets(root, repo_root)
    second = copy.deepcopy(first)
    second.update(result_id='later-result', supersedes=first['result_id'], created_at='2026-07-11T10:12:00Z')
    gate = evaluate_artifact_gate(run, [task], [first, second], gate_id='test-gate', stage='planning', required_task_ids=[task['task_id']], evaluated_at='2026-07-11T10:13:00Z')
    for packet, name in [(run, 'orun.json'), (task, 'task.json'), (first, 'first.json'), (second, 'second.json'), (gate, 'gate.json')]:
        add_packet(root, packet, name)
    change_manifest(root, lambda m: m['worker_status'].update({'build-plan': 'completed'}))
    state = snapshot(root, 'demo-current', policy)
    assert next(w for w in state['workers'] if w['id'] == 'build-plan')['result_status'] == 'ok'


@pytest.mark.parametrize('failure', ['missing_prior', 'fork', 'role', 'subject', 'task_input', 'result_contract', 'duplicate_root', 'forged_gate'])
def test_orchestration_chain_subject_and_reference_failures(demo, repo_root, failure):
    root, policy = demo
    run, task, result = orchestration_packets(root, repo_root)
    if failure == 'missing_prior':
        result['supersedes'] = 'not-present'
    elif failure == 'role':
        result['role'] = 'different-role'
    elif failure == 'subject':
        result['run_id'] = 'different-run'
    elif failure == 'task_input':
        task['inputs'][0]['sha256'] = '0' * 64
    elif failure == 'result_contract':
        result['output_artifacts'][0]['contract'] = 'media-plan'
    for packet, name in [(run, 'orun.json'), (task, 'task.json'), (result, 'first.json')]:
        add_packet(root, packet, name)
    if failure in {'fork', 'duplicate_root'}:
        for number in range(2 if failure == 'fork' else 1):
            later = copy.deepcopy(result)
            later.update(result_id='later-' + str(number), supersedes=result['result_id'] if failure == 'fork' else None, created_at='2026-07-11T10:12:00Z')
            add_packet(root, later, 'later-' + str(number) + '.json')
    elif failure == 'forged_gate':
        from claude_ads_core.orchestration import evaluate_artifact_gate
        gate = evaluate_artifact_gate(run, [task], [result], gate_id='forged-gate', stage='planning', required_task_ids=[task['task_id']], evaluated_at='2026-07-11T10:13:00Z')
        gate['checks'][0]['message'] = 'Forged verification message'
        add_packet(root, gate, 'gate.json')
    with pytest.raises(CockpitError, match='Orchestration|orchestration'):
        snapshot(root, 'demo-current', policy)


def test_nested_registered_file_and_portable_csv_normalization(demo, repo_root):
    root, policy = demo
    source = repo_root / 'tests/fixtures/exports/google.csv'
    if not source.exists():
        source = next((repo_root / 'tests/fixtures/exports').glob('*google*.csv'))
    run = root / 'demo-current'
    # Remove the report to permit an independent CSV fixture account identity.
    index = read(run / 'cockpit.json')
    index['artifacts'] = [r for r in index['artifacts'] if r['contract'] != 'report-bundle']
    index['inputs'] = [{'id': 'csv', 'path': 'nested/export.csv', 'kind': 'csv', 'contract': 'account-snapshot', 'platform': 'google', 'sha256': digest(source.read_bytes())}]
    (run / 'nested').mkdir()
    (run / 'nested/export.csv').write_bytes(source.read_bytes())
    write(run / 'cockpit.json', index)
    state = snapshot(root, 'demo-current', policy)
    assert state['inputs'][0]['validation'] == 'valid'
    assert state['accounts'][0]['platform'] == 'google'
    receipt = action(root, 'demo-current', policy, 'validate-input', input_id='csv', expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] == 'succeeded'


def test_invalid_csv_and_wrong_platform_are_disclosed(demo):
    root, policy = demo
    run = root / 'demo-current'
    index = read(run / 'cockpit.json')
    (run / 'export.csv').write_bytes(b'bad,header\nprivate,body\n')
    index['inputs'].append({'id': 'csv', 'path': 'export.csv', 'kind': 'csv', 'contract': 'account-snapshot', 'platform': 'google', 'sha256': digest((run / 'export.csv').read_bytes())})
    write(run / 'cockpit.json', index)
    state = snapshot(root, 'demo-current', policy)
    assert state['inputs'][-1]['validation'] == 'invalid'
    assert 'private' not in str(state['inputs'])


def test_output_create_is_exclusive(tmp_path):
    with Directory(tmp_path) as directory:
        directory.write('generated/report.md', b'first output')
        with pytest.raises(CockpitError, match='overwrite'):
            directory.write('generated/report.md', b'second output')
    assert (tmp_path / 'generated/report.md').read_bytes() == b'first output'


def test_publisher_second_rename_failure_restores_pair(demo, monkeypatch):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    manifest = read(root / 'demo-current/manifest.json')
    index = read(root / 'demo-current/cockpit.json')
    index['phase'] = 'Uncommitted producer update'
    original = Directory.write
    failed = False
    def fail_once(self, path, data, **kwargs):
        nonlocal failed
        if path == 'cockpit.json' and kwargs.get('replace') and not failed:
            failed = True
            raise CockpitError('Simulated local write failure')
        return original(self, path, data, **kwargs)
    monkeypatch.setattr(Directory, 'write', fail_once)
    with pytest.raises(CockpitError, match='Simulated'):
        publish(root, 'demo-current', policy, manifest, index, expected_fingerprint=state['fingerprint'])
    assert snapshot(root, 'demo-current', policy)['fingerprint'] == state['fingerprint']


def test_shipped_synthetic_run_fixture_is_valid(repo_root):
    state = snapshot(repo_root / 'tests/fixtures/cockpit', 'synthetic-run', repo_root, as_of='2026-10-08')
    assert state['workflow_status'] == 'completed'
    assert state['scoring'][0]['health_score'] is None
    assert state['inputs'][0]['validation'] == 'valid'


def test_publisher_exposes_actual_worker_and_phase_updates(demo):
    root, policy = demo
    target = root / 'producer-run'
    target.mkdir()
    manifest = read(root / 'demo-current/manifest.json')
    manifest.update(run_id='producer-run', worker_status={'google': 'pending'}, completeness='partial')
    index = {'schema_version': '1.0.0', 'run_id': 'producer-run', 'phase': 'Intake', 'inputs': [], 'artifacts': []}
    publish(root, 'producer-run', policy, manifest, index)
    state = snapshot(root, 'producer-run', policy)
    assert state['workflow_status'] == 'pending' and state['phase'] == 'Intake'
    manifest['worker_status']['google'] = 'running'
    index['phase'] = 'Producer analysis'
    publish(root, 'producer-run', policy, manifest, index, expected_fingerprint=state['fingerprint'])
    state = snapshot(root, 'producer-run', policy)
    assert state['workflow_status'] == 'running' and state['phase'] == 'Producer analysis'


@pytest.mark.parametrize('field,value', [('currency', 'EUR'), ('window', {'start':'2026-01-01','end':'2026-01-02'})])
def test_duplicate_account_inputs_reject_window_and_currency_conflicts(demo, field, value):
    root, policy = demo
    account = read(root / 'demo-current/account.json')
    account[field] = value
    write(root / 'demo-current/duplicate.json', account)
    index = read(root / 'demo-current/cockpit.json')
    index['inputs'].append({**index['inputs'][0], 'id':'duplicate', 'path':'duplicate.json', 'sha256':digest(encode(account))})
    write(root / 'demo-current/cockpit.json', index)
    with pytest.raises(CockpitError, match='windows or currencies conflict'):
        snapshot(root, 'demo-current', policy)


@pytest.mark.parametrize('with_findings', [True, False])
def test_compare_rejects_platform_worker_without_actual_account_identity(demo, with_findings):
    root, policy = demo
    worker = read(root / 'demo-current/worker.json')
    worker['platform'] = 'meta'
    if with_findings:
        worker['findings'][0]['control_id'] = 'M01'
    else:
        worker['findings'] = []
    write(root / 'demo-current/meta.json', worker)
    index = read(root / 'demo-current/cockpit.json')
    index['artifacts'].append({'id':'meta','path':'meta.json','contract':'audit-worker-result','sha256':digest(encode(worker))})
    write(root / 'demo-current/cockpit.json', index)
    change_manifest(root, lambda m: m['worker_status'].update(meta='completed'))
    with pytest.raises(CockpitError, match='established account identity'):
        compare(root, 'demo-current', 'demo-baseline', policy)


@pytest.mark.parametrize('status,expected', [('failed','failed'), ('blocked','blocked'), ('needs_input','blocked')])
def test_non_ok_orchestration_result_downgrades_manifest_completeness(demo, repo_root, status, expected):
    root, policy = demo
    run, task, result = orchestration_packets(root, repo_root)
    result.update(status=status, blockers=['Synthetic missing evidence'], recovery_hints=['Supply synthetic evidence'])
    for packet, name in [(run,'orun.json'),(task,'task.json'),(result,'result.json')]:
        add_packet(root, packet, name)
    change_manifest(root, lambda m: m['worker_status'].update({'build-plan':'completed'}))
    state = snapshot(root, 'demo-current', policy)
    assert state['workflow_status'] == expected
    assert state['completeness'] == 'partial'


def test_phone_redaction_preserves_iso_dates(demo):
    root, policy = demo
    from claude_ads_core.cockpit import _safe_text
    assert _safe_text('2026-10-08 2026-10-09 +12345678910') == '2026-10-08 2026-10-09 [REDACTED NUMBER]'
    assert _safe_text('8 October 2026') == '8 October 2026'
    state = compare(root, 'demo-current','demo-baseline',policy)
    date = datetime.now(timezone.utc).date().isoformat()
    assert any('on ' + date in row for row in state['comparison']['differences'])


def test_huge_spend_is_bounded_in_snapshot_and_action(demo):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    account = read(root / 'demo-current/account.json')
    report = read(root / 'demo-current/report.json')
    account['spend'] = 10 ** 1000
    report['account_snapshot'] = account
    write(root / 'demo-current/account.json', account)
    write(root / 'demo-current/report.json', report)
    reindex(root)
    with pytest.raises(CockpitError):
        snapshot(root, 'demo-current', policy)
    receipt = action(root,'demo-current',policy,'validate-run',expected_fingerprint=state['fingerprint'])
    assert receipt['outcome'] in {'blocked','failed'}
    assert '10000000' not in str(receipt)


@pytest.mark.parametrize('outcome', ['succeeded','failed','blocked'])
def test_reopen_projects_canonical_history_and_keeps_original_fingerprint(demo, monkeypatch, outcome):
    root, policy = demo
    import claude_ads_core.cockpit as cockpit
    state = snapshot(root, 'demo-current', policy)
    if outcome == 'failed':
        def fail(_):
            raise ValueError('private detail')
        monkeypatch.setattr(cockpit, '_render_markdown_layout', fail)
    receipt = action(root,'demo-current',policy,'render-report',expected_fingerprint='0'*64 if outcome == 'blocked' else state['fingerprint'])
    assert receipt['outcome'] == outcome
    reopened = snapshot(root,'demo-current',policy)
    assert reopened['fingerprint'] == state['fingerprint']
    row = reopened['receipts'][0]
    assert row['receipt'] == receipt
    assert row['sha256'] == digest((root/'demo-current'/row['path']).read_bytes())
    assert any(a['path'] == row['path'] and a['kind']=='cockpit-action-receipt' for a in reopened['artifacts'])
    if outcome == 'succeeded':
        assert any(a['kind']=='rendered-report' for a in reopened['artifacts'])


@pytest.mark.parametrize('mutation', ['run','operation','inverted_time','future_time','name','output_subject','output_size','output_bytes','output_symlink','receipt_symlink','directory_symlink','extra_file'])
def test_reopen_rejects_unsafe_or_tampered_generated_history(demo, tmp_path, mutation):
    root, policy = demo
    state = snapshot(root,'demo-current',policy)
    receipt = action(root,'demo-current',policy,'render-report',expected_fingerprint=state['fingerprint'])
    selected = root/'demo-current'
    path = selected/'cockpit/receipts'/(receipt['action_id']+'.json')
    output = selected/receipt['outputs'][0]['path']
    if mutation == 'run':
        receipt['run_id'] = 'different-run'
    elif mutation == 'operation':
        receipt['operation'] = 'validate-input'
    elif mutation == 'inverted_time':
        receipt['finished_at'] = '2000-01-01T00:00:00Z'
    elif mutation == 'future_time':
        receipt['finished_at'] = '2099-01-01T00:00:00Z'
    elif mutation == 'output_subject':
        receipt['outputs'][0]['path'] = 'account.json'
    elif mutation == 'output_size':
        receipt['outputs'][0]['size'] += 1
    elif mutation == 'name':
        path.rename(path.with_name('different.json'))
    elif mutation == 'output_bytes':
        output.write_bytes(b'tampered')
    elif mutation in {'output_symlink','receipt_symlink'}:
        target = output if mutation=='output_symlink' else path
        outside = tmp_path/'outside'
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
    elif mutation == 'directory_symlink':
        folder = selected/'cockpit/receipts'
        folder.rename(selected/'cockpit/previous')
        folder.symlink_to(selected/'cockpit/previous',target_is_directory=True)
    elif mutation == 'extra_file':
        (path.parent/'unexpected.txt').write_text('not a canonical receipt')
    if mutation in {'run','operation','inverted_time','future_time','output_subject','output_size'}:
        write(path,receipt)
    with pytest.raises(CockpitError):
        snapshot(root,'demo-current',policy)


def test_history_listing_is_bounded_and_reverified(tmp_path):
    folder = tmp_path/'cockpit/receipts'
    folder.mkdir(parents=True)
    for name in ('a.json','b.json'):
        (folder/name).write_text('{}')
    with Directory(tmp_path) as directory:
        with pytest.raises(CockpitError,match='directory limit'):
            directory.list_files('cockpit/receipts',limit=1)
        assert directory.list_files('cockpit/receipts') == ('a.json','b.json')
        (folder/'c.json').write_text('{}')
        with pytest.raises(CockpitError,match='history changed'):
            directory.verify()


@pytest.mark.parametrize('failure', ['interrupt','timeout'])
def test_local_renderer_interruption_and_deadline_preserve_receipt_and_release_lock(demo, monkeypatch, failure):
    root, policy = demo
    import claude_ads_core.cockpit as cockpit
    import time
    import multiprocessing
    children_before = {child.pid for child in multiprocessing.active_children()}
    def renderer(_):
        if failure == 'interrupt':
            raise KeyboardInterrupt
        time.sleep(5)
        return 'too late'
    monkeypatch.setattr(cockpit,'_render_markdown_layout',renderer)
    monkeypatch.setattr(cockpit,'RENDER_TIMEOUT_SECONDS',0.05)
    state = snapshot(root,'demo-current',policy)
    before = time.monotonic()
    receipt = action(root,'demo-current',policy,'render-report',expected_fingerprint=state['fingerprint'])
    assert time.monotonic()-before < 2
    assert receipt['outcome'] == ('failed' if failure=='interrupt' else 'blocked')
    assert receipt['outputs'] == []
    assert {child.pid for child in multiprocessing.active_children()} == children_before
    assert snapshot(root,'demo-current',policy)['receipts'][0]['receipt'] == receipt
    assert action(root,'demo-current',policy,'validate-run',expected_fingerprint=state['fingerprint'])['outcome']=='succeeded'


def test_historical_policy_fingerprint_is_retained_without_authorizing_current_state(demo):
    root, policy = demo
    before = snapshot(root,'demo-current',policy)
    receipt = action(root,'demo-current',policy,'validate-run',expected_fingerprint=before['fingerprint'])
    target = policy/'control-plane/manifests/scoring-profiles.json'
    profiles = read(target)
    profiles['generated_at'] = '2026-01-01'
    write(target,profiles)
    after = snapshot(root,'demo-current',policy)
    assert after['policy_fingerprint'] != before['policy_fingerprint']
    assert after['receipts'][0]['receipt'] == receipt
    assert after['receipts'][0]['receipt']['policy_fingerprint'] != after['policy_fingerprint']


def test_doctor_and_snapshot_never_start_renderer_child(demo, monkeypatch):
    root, policy = demo
    import multiprocessing
    def forbidden(*args, **kwargs):
        raise AssertionError('read-only call started a child')
    monkeypatch.setattr(multiprocessing,'get_context',forbidden)
    assert doctor(policy,root)['status']=='ok'
    assert snapshot(root,'demo-current',policy)['receipts']==[]


def test_renderer_child_closes_client_directory_and_action_lock_descriptors(tmp_path, monkeypatch):
    import claude_ads_core.cockpit as cockpit
    with Directory(tmp_path) as directory, directory.lock(exclusive=True):
        descriptors = (directory.fd,*directory.lock_fds)
        assert len(descriptors)==2
        def renderer(_):
            for descriptor in descriptors:
                with pytest.raises(OSError):
                    os.fstat(descriptor)
            return 'rendered without client descriptors'
        monkeypatch.setattr(cockpit,'_render_markdown_layout',renderer)
        assert cockpit._render_local({},'markdown',close_fds=descriptors)==b'rendered without client descriptors'
        directory.verify()


def test_parent_keyboard_interrupt_records_failure_receipt(demo, monkeypatch):
    root, policy = demo
    import claude_ads_core.cockpit as cockpit
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(cockpit,'_render_local',interrupted)
    state = snapshot(root,'demo-current',policy)
    receipt = action(root,'demo-current',policy,'render-report',expected_fingerprint=state['fingerprint'])
    assert receipt['outcome']=='failed'
    assert snapshot(root,'demo-current',policy)['receipts'][0]['receipt']==receipt


def test_multiple_report_bundles_share_one_render_deadline(demo, monkeypatch):
    root, policy = demo
    import claude_ads_core.cockpit as cockpit
    import time
    state = snapshot(root,'demo-current',policy)
    original = cockpit._collect
    def two_reports(*args, **kwargs):
        snapshot_state, reports, manifest, index = original(*args, **kwargs)
        return snapshot_state, reports*2, manifest, index
    monkeypatch.setattr(cockpit,'_collect',two_reports)
    monkeypatch.setattr(cockpit,'RENDER_TIMEOUT_SECONDS',0.15)
    def slow(_):
        time.sleep(0.1)
        return 'synthetic report'
    monkeypatch.setattr(cockpit,'_render_markdown_layout',slow)
    receipt = action(root,'demo-current',policy,'render-report',expected_fingerprint=state['fingerprint'])
    assert receipt['outcome']=='blocked'
    assert receipt['outputs']==[]
    assert 'time limit' in receipt['diagnostics'][0]


def refuse_lifecycle(manifest, kind):
    lifecycle = manifest['data_lifecycle']
    if kind == 'expired':
        lifecycle['retention']['delete_after'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    elif kind == 'deleted':
        lifecycle['deletion'].update(status='verified', verification_artifact_locator='deletion.json')
    elif kind == 'restricted':
        manifest['privacy_class'] = lifecycle['classification'] = 'restricted'
        lifecycle['encryption'] = {'at_rest': 'verified', 'in_transit': 'verified', 'evidence_refs': ['synthetic-evidence']}
    else:
        lifecycle['incident'].update(status='open', record_locator='synthetic-incident-record')


@pytest.mark.parametrize('kind,message', [('expired', 'deadline'), ('deleted', 'verified deletion'), ('restricted', 'Restricted lifecycle prohibits persisted cockpit processing'), ('incident', 'incident')])
def test_action_never_writes_into_a_lifecycle_refused_run(demo, kind, message):
    root, policy = demo
    change_manifest(root, lambda m: refuse_lifecycle(m, kind))
    run = root / 'demo-current'
    before = sorted(str(p.relative_to(run)) for p in run.rglob('*'))
    # A junk but well-formed fingerprint must not matter: the gate is lifecycle.
    for operation in ('validate-run', 'render-report'):
        with pytest.raises(CockpitError, match=message):
            action(root, 'demo-current', policy, operation, expected_fingerprint='0' * 64)
    assert sorted(str(p.relative_to(run)) for p in run.rglob('*')) == before
    assert not (run / '.cockpit.lock').exists()
    assert not (run / 'cockpit').exists()


def test_stale_fingerprint_on_an_allowed_run_still_records_a_blocked_receipt(demo):
    root, policy = demo
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint='0' * 64)
    assert receipt['outcome'] == 'blocked' and 'stale' in receipt['diagnostics'][0]
    assert (root / 'demo-current/cockpit/receipts' / (receipt['action_id'] + '.json')).is_file()


def seed_receipts(root, receipt, count):
    folder = root / 'demo-current/cockpit/receipts'
    for _ in range(count):
        copy_ = {**receipt, 'action_id': uuid.uuid4().hex}
        write(folder / (copy_['action_id'] + '.json'), copy_)


def test_receipt_history_is_counted_once_and_failure_says_what_to_archive(demo):
    root, policy = demo
    state = snapshot(root, 'demo-current', policy)
    receipt = action(root, 'demo-current', policy, 'validate-run', expected_fingerprint=state['fingerprint'])
    registered = len(state['artifacts'])
    # Each receipt is one listed artifact. Counting it twice used to fail near 500.
    seed_receipts(root, receipt, 700 - 1)
    reopened = snapshot(root, 'demo-current', policy)
    assert len(reopened['receipts']) == 700
    assert len(reopened['artifacts']) == registered + 700
    seed_receipts(root, receipt, 1000 - registered - 700)
    assert len(snapshot(root, 'demo-current', policy)['receipts']) == 1000 - registered
    seed_receipts(root, receipt, 1)
    for call in (lambda: snapshot(root, 'demo-current', policy), lambda: compare(root, 'demo-current', 'demo-baseline', policy)):
        with pytest.raises(CockpitError, match='archive older receipts') as caught:
            call()
        assert 'cockpit/receipts' in str(caught.value) and 'cockpit/reports' in str(caught.value)


def test_ancestor_symlink_in_a_root_is_refused_with_an_actionable_message(demo, tmp_path):
    root, policy = demo
    link = tmp_path / 'ancestor-link'
    link.symlink_to(root.parent, target_is_directory=True)
    through_link = link / root.name
    with pytest.raises(CockpitError, match='fully resolved path'):
        snapshot(through_link, 'demo-current', policy)
    with pytest.raises(CockpitError, match='fully resolved path'):
        Directory(through_link)
    assert snapshot(through_link.resolve(), 'demo-current', policy)['run_id'] == 'demo-current'


def test_embedded_nul_in_a_path_argument_is_a_bounded_error(tmp_path, repo_root):
    with pytest.raises(CockpitError):
        Directory(str(tmp_path) + '/a\x00b')
    with Directory(tmp_path) as directory:
        for call in (lambda: directory.read('a\x00b.json'), lambda: directory.list_files('a\x00b'), lambda: directory.write('a\x00b/c.json', b'{}')):
            with pytest.raises(CockpitError):
                call()
    with pytest.raises(CockpitError):
        create_demo(tmp_path / 'fresh\x00demo', repo_root)
    assert not list(tmp_path.glob('fresh*'))


def test_failed_demo_creation_cleans_up_only_its_own_destination(tmp_path, repo_root, monkeypatch):
    import claude_ads_core.cockpit as cockpit
    bystander = tmp_path / 'bystander.txt'
    bystander.write_text('keep')
    existing = tmp_path / 'existing'
    existing.mkdir()
    (existing / 'client.json').write_text('{}')
    with pytest.raises(CockpitError, match='fresh'):
        create_demo(existing, repo_root)
    assert (existing / 'client.json').read_text() == '{}'
    destination = tmp_path / 'demo'
    original = cockpit.snapshot
    def broken(*args, **kwargs):
        raise CockpitError('Simulated failure after partial build')
    monkeypatch.setattr(cockpit, 'snapshot', broken)
    with pytest.raises(CockpitError, match='Simulated'):
        create_demo(destination, repo_root)
    assert not destination.exists() and bystander.read_text() == 'keep'
    monkeypatch.setattr(cockpit, 'snapshot', original)
    assert (Path(create_demo(destination, repo_root)['runs_root']) / 'demo-current/manifest.json').is_file()


def test_doctor_lists_unreadable_runs_as_blocked_instead_of_hiding_them(demo):
    root, policy = demo
    (root / 'demo-current/manifest.json').write_text('{broken')
    (root / 'demo-baseline/manifest.json').unlink()
    (root / 'demo-baseline/manifest.json').symlink_to(root / 'demo-stale/manifest.json')
    (root / 'not-a-run').mkdir()
    (root / 'not-a-run/notes.txt').write_text('private')
    result = doctor(policy, root)
    rows = {row['id']: row['status'] for row in result['runs']}
    assert rows['demo-current'] == 'blocked' and rows['demo-baseline'] == 'blocked'
    assert rows['demo-stale'] in {'complete', 'partial', 'failed'}
    assert 'not-a-run' not in rows
    assert result['status'] == 'ok'
    assert len(result['diagnostics']) == 1 and result['diagnostics'][0].startswith('2 run directories')
    assert 'private' not in json.dumps(result)


def test_doctor_with_only_corrupt_runs_is_not_an_empty_chooser(demo):
    root, policy = demo
    for run in root.iterdir():
        if run.name != '_policy':
            (run / 'manifest.json').write_text('{broken')
    result = doctor(policy, root)
    assert len(result['runs']) == 7 and all(row['status'] == 'blocked' for row in result['runs'])


def test_doctor_reports_an_unsupported_platform_explicitly(demo, monkeypatch):
    root, policy = demo
    monkeypatch.delattr(os, 'O_NOFOLLOW')
    result = doctor(policy, root)
    assert result['status'] == 'blocked' and result['runs'] == []
    assert result['diagnostics'] and 'Unsupported platform' in result['diagnostics'][0]
    assert 'unavailable or invalid' not in result['diagnostics'][0]


def test_doctor_reports_unavailable_policy_with_its_own_diagnostic(tmp_path):
    result = doctor(tmp_path / 'missing')
    assert result['status'] == 'blocked' and 'Trusted policy' in result['diagnostics'][0]


def test_urls_survive_display_redaction_while_filesystem_paths_do_not():
    from claude_ads_core.cockpit import _display, _safe_text
    assert _safe_text('see https://example.com/shoes?size=9 and http://example.com/a/b.') == 'see https://example.com/shoes?size=9 and http://example.com/a/b.'
    home = '/' + 'home'
    text = _safe_text(f'opened {home}/someone/client/export.csv and C:\\Users\\someone\\export.csv and D:/data/export.csv')
    assert text == 'opened [REDACTED PATH] and [REDACTED PATH] and [REDACTED PATH]'
    mixed = _safe_text('fetch https://example.com/shoes then read /etc/passwd')
    assert mixed == 'fetch https://example.com/shoes then read [REDACTED PATH]'
    assert _safe_text(f'file://{home}/someone/export.csv') == 'file:[REDACTED PATH]'
    assert _display({'link': 'https://example.com/shoes'}) == {'link': 'https://example.com/shoes'}


def test_display_keeps_every_entry_when_redacted_keys_collide():
    from claude_ads_core.cockpit import _display
    home = '/' + 'var/home'
    shown = _display({f'{home}/a/x': 'first', f'{home}/b/y': 'second', f'{home}/c/z': 'third', 'plain': 'fourth'})
    assert sorted(shown.values()) == ['first', 'fourth', 'second', 'third']
    assert len(shown) == 4 and all('/var' not in key for key in shown)


def test_provider_style_api_keys_are_redacted_without_hiding_ordinary_words():
    from claude_ads_core.cockpit import _safe_text
    key = 'sk-' + 'a1B2c3D4' * 4
    assert _safe_text('token ' + key + ' end') == 'token [REDACTED] end'
    assert _safe_text('sk-ant-api03-' + 'x' * 30) == '[REDACTED]'
    assert _safe_text('risk-assessment-and-mitigation-plan and sk-short') == 'risk-assessment-and-mitigation-plan and sk-short'
