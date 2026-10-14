"""Exercise the approved video story through real core actions, never client data."""
from pathlib import Path
import json
import os

import pytest

from claude_ads_core.cockpit import action, compare, create_demo, doctor, snapshot

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Descriptor IO intentionally fails closed on non-POSIX hosts')


def test_demo_keyword_story_checks_compares_and_renders(tmp_path, repo_root):
    setup = create_demo(tmp_path / 'story', repo_root)
    runs, policy = Path(setup['runs_root']), Path(setup['policy_root'])
    assert setup['steps'][0]['run_id'] == 'demo-showcase'
    assert setup['steps'][1]['run_id'] == 'demo-needs-input'
    assert [step['tab'] for step in setup['steps']] == ['Run', 'Run', 'Inputs', 'Inputs', 'Evidence', 'Run', 'Compare', 'Reports']
    assert setup['steps'][-1]['baseline_id'] == 'demo-needs-input'
    missing = snapshot(runs, 'demo-needs-input', policy)
    keyword = next(row for row in missing['inputs'] if row['id'] == 'keyword-evidence')
    assert keyword['validation'] == 'missing'
    assert not (runs / 'demo-needs-input' / keyword['path']).exists()
    assert 'keyword-evidence' in missing['workers'][0]['missing_inputs'][0]
    assert missing['findings'][0]['finding']['status'] == 'unknown'
    assert missing['findings'][0]['finding']['control_id'] == 'G14'
    failed = action(runs, 'demo-needs-input', policy, 'validate-input', input_id='keyword-evidence',
                    expected_fingerprint=missing['fingerprint'])
    assert failed['outcome'] == 'failed'

    corrected = snapshot(runs, 'demo-corrected', policy)
    assert corrected['findings'][0]['finding']['control_id'] == 'G14'
    assert corrected['findings'][0]['source_ids'] == ['cockpit-demo-source-3']
    keyword = next(row for row in corrected['inputs'] if row['id'] == 'keyword-evidence')
    assert keyword['validation'] == 'valid'
    payload = json.loads((runs / 'demo-corrected' / keyword['path']).read_text())
    assert {row['polarity'] for row in payload['campaigns'][0]['keywords']} == {'positive', 'negative'}
    checked = action(runs, 'demo-corrected', policy, 'validate-input', input_id='keyword-evidence',
                     expected_fingerprint=corrected['fingerprint'])
    assert checked['outcome'] == 'succeeded'
    assert snapshot(runs, 'demo-corrected', policy)['fingerprint'] == corrected['fingerprint']

    comparison = compare(runs, 'demo-corrected', 'demo-needs-input', policy)['comparison']
    assert comparison['comparable']
    assert comparison['findings'][0]['baseline_status'] == 'unknown'
    assert comparison['findings'][0]['current_status'] == 'fail'
    assert comparison['findings'][0]['change'] == 'new_failure'
    rendered = action(runs, 'demo-corrected', policy, 'render-report',
                      expected_fingerprint=corrected['fingerprint'])
    assert rendered['outcome'] == 'succeeded'
    text = (runs / 'demo-corrected' / rendered['outputs'][0]['path']).read_text()
    assert 'synthetic keyword' in text.lower()
    assert 'Not scored' in text
    assert len(snapshot(runs, 'demo-corrected', policy)['receipts']) == 2
    assert all(row['status'] == 'disabled' for row in doctor(policy)['profiles'])
    for run in ['demo-needs-input', 'demo-corrected', 'demo-stale', 'demo-partial', 'demo-showcase']:
        assert all(row['health_score'] is None and row['evidence_coverage'] == 0
                   for row in snapshot(runs, run, policy)['scoring'])


def test_demo_showcase_is_a_full_unscored_four_platform_audit(tmp_path, repo_root):
    setup = create_demo(tmp_path / 'showcase', repo_root)
    runs, policy = Path(setup['runs_root']), Path(setup['policy_root'])
    state = snapshot(runs, 'demo-showcase', policy)
    assert [w['platform'] for w in state['workers']] == ['google', 'linkedin', 'meta', 'tiktok']
    assert {w['platform']: w['status'] for w in state['workers']} == {'google': 'completed', 'linkedin': 'completed', 'meta': 'completed', 'tiktok': 'failed'}
    assert state['completeness'] == 'partial' and state['workflow_status'] == 'failed'
    assert len(state['findings']) == 28
    by_platform = {p: {f['finding']['status'] for f in state['findings'] if f['platform'] == p} for p in ('google', 'meta', 'linkedin', 'tiktok')}
    assert by_platform['tiktok'] == {'unknown'} and {'pass', 'fail', 'unknown'} <= by_platform['meta']
    assert {f['evidence_status'] for f in state['findings']} == {'current', 'stale'}
    assert all(f['finding']['observation'].startswith('Synthetic') for f in state['findings'])
    assert all(row['health_score'] is None and row['evidence_coverage'] == 0 and row['profile_status'] == 'disabled' for row in state['scoring'])
    rendered = action(runs, 'demo-showcase', policy, 'render-report', expected_fingerprint=state['fingerprint'])
    assert rendered['outcome'] == 'succeeded'
