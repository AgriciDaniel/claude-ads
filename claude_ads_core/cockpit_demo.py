"""Explicit isolated synthetic walkthrough, with every scoring profile disabled."""
from __future__ import annotations

import copy
import os
import shutil
from datetime import timedelta
from pathlib import Path

from .cockpit_io import CockpitError, Directory, digest, encode


SHOWCASE_PLATFORMS = ('google', 'meta', 'linkedin', 'tiktok')
SHOWCASE_CHECKS = 7
# One result per check. Each platform has its own mix so the full audit does not look uniform.
SHOWCASE_RESULTS = {
    'google': ('pass', 'pass', 'pass', 'fail', 'pass', 'unknown', 'pass'),
    'meta': ('pass', 'fail', 'fail', 'unknown', 'pass', 'fail', 'pass'),
    'linkedin': ('pass', 'unknown', 'pass', 'fail', 'unknown', 'pass', 'pass'),
}
SHOWCASE_NOTES = {
    'pass': ('Synthetic walkthrough observation', 'Fixture-only result, not a platform diagnosis', 'Keep this setting as it is'),
    'fail': ('Synthetic walkthrough observation', 'Fixture-only result, not a platform diagnosis', 'Review the fixture evidence for this check'),
    'unknown': ('Synthetic walkthrough input was not supplied', 'The fixture cannot judge this check without its input', 'Supply the fixture input and run a local check'),
}


def _showcase_finding(control_id, status):
    observation, diagnosis, recommendation = SHOWCASE_NOTES[status]
    evidenced = status in {'pass', 'fail'}
    return {'schema_version': '1.0.0', 'control_id': control_id, 'status': status,
            'evidence': [{'kind': 'synthetic', 'value': 'Fixture-only observation'}] if evidenced else [],
            'confidence': 'high' if evidenced else 'none', 'source_classification': 'evidence_based',
            'observation': observation, 'diagnosis': diagnosis, 'recommendation': recommendation}


def create_demo(runs_root, policy_root):
    destination = Path(runs_root).absolute()
    # The parent must already be trusted and traversable. mkdir is exclusive.
    with Directory(destination.parent) as parent:
        try:
            os.mkdir(destination.name, mode=0o700, dir_fd=parent.fd)
        except (OSError, ValueError) as exc:
            raise CockpitError('Demo destination must be fresh and have a safe existing parent') from exc
    try:
        return _build_demo(destination, policy_root)
    except BaseException:
        # Only the directory created above is removed, by name beneath its
        # trusted parent without following links, so a retry can start fresh.
        with Directory(destination.parent) as parent:
            shutil.rmtree(destination.name, dir_fd=parent.fd, ignore_errors=True)
        raise


def _build_demo(destination, policy_root):
    from .cockpit import INTERFACE_VERSION, POLICY_FILES, _now, _policy, _timestamp, snapshot
    with _policy(policy_root) as source:
        payloads = copy.deepcopy(source['payloads'])
        source['directory'].verify()
    now = _now()
    today = now.date()
    fresh = (today + timedelta(days=20)).isoformat()
    expired = (today - timedelta(days=1)).isoformat()
    # The copy contains only trusted public policy and synthetic additions.
    # Profiles stay disabled even if a future source policy enables one.
    for profile in payloads['scoring-profiles.json']['profiles']:
        profile.update(status='disabled', category_weights={}, health_control_ids=[], disabled_reason='Synthetic demo has no approved scoring profile')
    google = [r for r in payloads['control-registry.json']['controls'] if r['platform'] == 'google']
    keyword_control = next((row for row in google if row['control_id'] == 'G14'), None)
    if len(google) < 2 or keyword_control is None:
        raise CockpitError('Demo requires the canonical Google keyword governance catalog')
    for number, row in enumerate([*google[:2], keyword_control]):
        claim_id = f'COCKPIT-DEMO-CLAIM-{number + 1}'
        source_id = f'cockpit-demo-source-{number + 1}'
        due = expired if number == 1 else fresh
        retrieved = (today - timedelta(days=2)).isoformat()
        row['source_claim_ids'] = [claim_id]
        row['control_definition']['source_ids'] = [source_id]
        payloads['claim-ledger.json']['claims'].append({'id': claim_id, 'statement': 'Synthetic walkthrough support only, no platform fact',
             'classification': 'evidence-based', 'verdict': 'verified', 'source_ids': [source_id], 'load_bearing': False,
             'last_verified': retrieved, 'refresh_due': due, 'owner': 'synthetic-demo'})
        payloads['source-ledger.json']['sources'].append({'id': source_id, 'title': 'Synthetic cockpit walkthrough evidence',
             'locator': 'synthetic:fixture-only', 'source_type': 'repository-local', 'retrieved_at': retrieved,
             'refresh_due': due, 'confidence': 'high', 'claim_ids': [claim_id], 'redistribution': 'public-safe'})
    # A larger synthetic audit across four platforms, so the walkthrough can show a full run.
    # Every check gets its own synthetic support (fresh, or expired for a few) and no platform fact.
    registry_rows = payloads['control-registry.json']['controls']
    showcase_plan = {}
    for platform in SHOWCASE_PLATFORMS:
        rows = [r for r in registry_rows if r['platform'] == platform]
        if len(rows) < SHOWCASE_CHECKS:
            raise CockpitError('Demo requires the canonical control catalog for the showcase platforms')
        showcase_plan[platform] = rows[:SHOWCASE_CHECKS]
    number = 3
    showcase_support = {}
    for platform in SHOWCASE_PLATFORMS:
        for index, row in enumerate(showcase_plan[platform]):
            number += 1
            claim_id, source_id = f'COCKPIT-DEMO-CLAIM-{number}', f'cockpit-demo-source-{number}'
            due = expired if (number % 5 == 0) else fresh
            retrieved = (today - timedelta(days=2)).isoformat()
            row['source_claim_ids'] = [claim_id]
            row['control_definition']['source_ids'] = [source_id]
            payloads['claim-ledger.json']['claims'].append({'id': claim_id, 'statement': 'Synthetic walkthrough support only, no platform fact',
                 'classification': 'evidence-based', 'verdict': 'verified', 'source_ids': [source_id], 'load_bearing': False,
                 'last_verified': retrieved, 'refresh_due': due, 'owner': 'synthetic-demo'})
            payloads['source-ledger.json']['sources'].append({'id': source_id, 'title': 'Synthetic cockpit walkthrough evidence',
                 'locator': 'synthetic:fixture-only', 'source_type': 'repository-local', 'retrieved_at': retrieved,
                 'refresh_due': due, 'confidence': 'high', 'claim_ids': [claim_id], 'redistribution': 'public-safe'})
            showcase_support[(platform, row['control_id'])] = source_id
    demo_policy = destination / '_policy'
    with Directory(destination) as root:
        for name in POLICY_FILES:
            root.write('_policy/control-plane/manifests/' + name, encode(payloads[name]))
        lifecycle = {'schema_version': '1.0.0', 'lifecycle_id': 'synthetic-cockpit-demo', 'classification': 'public',
             'retention': {'minimum_seconds': 0, 'mode': 'operator-defined', 'delete_after': _timestamp(now + timedelta(days=30)),
                           'purpose': 'Synthetic local cockpit walkthrough', 'exception_reason': None},
             'encryption': {'at_rest': 'not-applicable', 'in_transit': 'not-applicable', 'evidence_refs': []},
             'access': {'owner': 'synthetic-demo-owner', 'authorized_roles': ['demo-operator'], 'access_log_locator': None},
             'deletion': {'status': 'scheduled', 'method': 'Operator removes isolated demo directory', 'verification_required': True, 'verification_artifact_locator': None},
             'incident': {'owner': 'synthetic-demo-owner', 'reporting_channel': 'Synthetic local demo channel', 'status': 'not-triggered', 'record_locator': None}}
        for name, finding_status, worker_status, result_status, incomplete in [
                ('demo-baseline', 'pass', 'completed', 'ok', False),
                ('demo-current', 'fail', 'completed', 'ok', False),
                ('demo-corrected', 'fail', 'completed', 'ok', False),
                ('demo-needs-input', 'unknown', 'running', 'needs_input', False),
                ('demo-stale', 'unknown', 'completed', 'ok', False),
                ('demo-partial', 'unknown', 'failed', 'failed', True)]:
            manifest = {'schema_version': '1.0.0', 'run_id': name, 'started_at': _timestamp(now - timedelta(minutes=5)),
                    'scopes': ['audit', 'google'], 'adapters': [{'platform': 'google', 'mode': 'export'}],
                    'sources': ['cockpit-demo-source-1'], 'privacy_class': 'public', 'data_lifecycle': lifecycle,
                    'worker_status': {'google': worker_status}, 'completeness': 'partial' if incomplete or worker_status != 'completed' else 'complete'}
            account = {'schema_version': '1.0.0', 'account': {'platform': 'google', 'account_id': 'synthetic-demo-account', 'name': 'Synthetic Demo'},
                    'window': {'start': (today - timedelta(days=8)).isoformat(), 'end': (today - timedelta(days=1)).isoformat()},
                    'currency': 'USD', 'spend': 0, 'campaigns': [], 'creatives': [], 'conversions': [], 'budgets': []}
            keyword_account = copy.deepcopy(account)
            keyword_account['campaigns'] = [{'id': 'synthetic-search', 'name': 'Synthetic keyword example',
                    'keywords': [{'text': 'demo shoes', 'match_type': 'exact', 'polarity': 'positive', 'scope': 'ad-group'},
                                 {'text': 'demo shoes', 'match_type': 'exact', 'polarity': 'negative', 'scope': 'campaign'}]}]
            if name == 'demo-corrected':
                account = keyword_account
            selected = keyword_control if name in {'demo-needs-input', 'demo-corrected'} else google[1] if name == 'demo-stale' else google[0]
            manifest['sources'] = list(selected['control_definition']['source_ids'])
            finding = {'schema_version': '1.0.0', 'control_id': selected['control_id'], 'status': finding_status,
                    'evidence': [{'kind': 'synthetic', 'value': 'Fixture-only observation'}] if finding_status in {'pass', 'fail'} else [],
                    'confidence': 'high' if finding_status in {'pass', 'fail'} else 'none', 'source_classification': 'evidence_based',
                    'observation': 'Synthetic walkthrough result', 'diagnosis': 'This fixture is not a platform diagnosis',
                    'recommendation': 'Review the fixture evidence and try a local validation'}
            if name == 'demo-needs-input':
                finding.update(observation='Synthetic keyword evidence has not been supplied',
                               diagnosis='The fixture cannot inspect positive and negative keywords without its indexed input',
                               recommendation='Supply the synthetic keyword-evidence input and run a local check')
            elif name == 'demo-corrected':
                finding.update(evidence=[{'kind': 'synthetic-keyword-inventory', 'input_id': 'keyword-evidence',
                                          'path': 'keyword-evidence.json', 'keywords': keyword_account['campaigns'][0]['keywords']}],
                               observation='Corrected synthetic keyword input is available for inspection',
                               diagnosis='Precomputed fixture finding: identical exact positive and campaign negative keywords. This is not a live platform diagnosis',
                               recommendation='Inspect both polarities and their scope. Structural validation alone does not diagnose an account')
            worker = {'schema_version': '1.0.0', 'status': result_status, 'platform': 'google', 'scope': ['audit', 'google'],
                    'findings': [finding], 'contradictions': [], 'missing_inputs': ['Supply keyword-evidence (keyword-evidence.json) with both positive and negative keywords'] if result_status == 'needs_input' else [],
                    'stale_sources': ['cockpit-demo-source-2'] if name == 'demo-stale' else [],
                    'recovery_hints': ['Supply fixture evidence'] if result_status in {'failed', 'needs_input'} else []}
            report = {'schema_version': '1.0.0', 'run_manifest': manifest, 'account_snapshot': account,
                    'control_definitions': [selected['control_definition']], 'findings': [finding],
                    'scoring': {'health_score': None, 'evidence_coverage': 0.0, 'status': 'insufficient_evidence', 'categories': []}}
            files = {'account.json': encode(account), 'worker.json': encode(worker), 'report.json': encode(report)}
            inputs = [{'id': 'account', 'path': 'account.json', 'kind': 'json', 'contract': 'account-snapshot', 'platform': 'google', 'sha256': digest(files['account.json'])}]
            if name in {'demo-needs-input', 'demo-corrected'}:
                keyword_bytes = encode(keyword_account)
                inputs.append({'id': 'keyword-evidence', 'path': 'keyword-evidence.json', 'kind': 'json',
                               'contract': 'account-snapshot', 'platform': 'google', 'sha256': digest(keyword_bytes)})
                if name == 'demo-corrected':
                    files['keyword-evidence.json'] = keyword_bytes
            artifacts = [{'id': 'worker', 'path': 'worker.json', 'contract': 'audit-worker-result', 'sha256': digest(files['worker.json'])},
                         {'id': 'report', 'path': 'report.json', 'contract': 'report-bundle', 'sha256': digest(files['report.json'])}]
            index = {'schema_version': '1.0.0', 'run_id': name, 'phase': 'Synthetic walkthrough', 'inputs': inputs, 'artifacts': artifacts}
            root.write(name + '/manifest.json', encode(manifest))
            root.write(name + '/cockpit.json', encode(index))
            for relative, data in files.items():
                root.write(name + '/' + relative, data)
    with Directory(destination) as root:
        _write_showcase(root, showcase_plan, today, now, lifecycle, _timestamp)
    for name in ('demo-baseline', 'demo-current', 'demo-corrected', 'demo-needs-input', 'demo-stale', 'demo-partial', 'demo-showcase'):
        snapshot(destination, name, demo_policy)
    return {'interface_version': INTERFACE_VERSION, 'runs_root': str(destination), 'policy_root': str(demo_policy),
            'steps': [{'run_id': 'demo-showcase', 'title': 'Look at a full synthetic audit', 'baseline_id': None, 'tab': 'Run'},
                      {'run_id': 'demo-needs-input', 'title': 'Identify missing synthetic keyword evidence', 'baseline_id': None, 'tab': 'Run'},
                      {'run_id': 'demo-needs-input', 'title': 'Inspect the missing keyword input', 'baseline_id': None, 'tab': 'Inputs'},
                      {'run_id': 'demo-corrected', 'title': 'Check the corrected synthetic keyword input', 'baseline_id': None, 'tab': 'Inputs'},
                      {'run_id': 'demo-stale', 'title': 'Inspect expired synthetic support', 'baseline_id': None, 'tab': 'Evidence'},
                      {'run_id': 'demo-partial', 'title': 'Inspect a failed synthetic worker', 'baseline_id': None, 'tab': 'Run'},
                      {'run_id': 'demo-corrected', 'title': 'Compare unknown and observed fixture results', 'baseline_id': 'demo-needs-input', 'tab': 'Compare'},
                      {'run_id': 'demo-corrected', 'title': 'Render a local synthetic report and receipt', 'baseline_id': 'demo-needs-input', 'tab': 'Reports'}]}


def _write_showcase(root, plan, today, now, lifecycle, timestamp):
    """One synthetic four-platform audit: three platforms finished, one worker failed."""
    worker_status = {'google': 'completed', 'meta': 'completed', 'linkedin': 'completed', 'tiktok': 'failed'}
    source_ids = sorted({sid for rows in plan.values() for row in rows for sid in row['control_definition']['source_ids']})
    manifest = {'schema_version': '1.0.0', 'run_id': 'demo-showcase', 'started_at': timestamp(now - timedelta(minutes=5)),
                'scopes': ['audit', *SHOWCASE_PLATFORMS], 'adapters': [{'platform': p, 'mode': 'export'} for p in SHOWCASE_PLATFORMS],
                'sources': source_ids, 'privacy_class': 'public', 'data_lifecycle': lifecycle,
                'worker_status': worker_status, 'completeness': 'partial'}
    files, inputs, artifacts = {}, [], []
    window = {'start': (today - timedelta(days=8)).isoformat(), 'end': (today - timedelta(days=1)).isoformat()}
    for platform in SHOWCASE_PLATFORMS:
        account = {'schema_version': '1.0.0', 'account': {'platform': platform, 'account_id': f'synthetic-demo-account-{platform}', 'name': f'Synthetic Demo {platform}'},
                   'window': window, 'currency': 'USD', 'spend': 0, 'campaigns': [], 'creatives': [], 'conversions': [], 'budgets': []}
        failed = worker_status[platform] == 'failed'
        findings = []
        for index, row in enumerate(plan[platform]):
            status = 'unknown' if failed else SHOWCASE_RESULTS[platform][index]
            findings.append(_showcase_finding(row['control_id'], status))
        worker = {'schema_version': '1.0.0', 'status': 'failed' if failed else 'ok', 'platform': platform, 'scope': ['audit', platform],
                  'findings': findings, 'contradictions': [], 'missing_inputs': [],
                  'stale_sources': [], 'recovery_hints': ['Supply fixture evidence'] if failed else []}
        files[f'account-{platform}.json'] = encode(account)
        files[f'worker-{platform}.json'] = encode(worker)
        inputs.append({'id': f'account-{platform}', 'path': f'account-{platform}.json', 'kind': 'json', 'contract': 'account-snapshot',
                       'platform': platform, 'sha256': digest(files[f'account-{platform}.json'])})
        artifacts.append({'id': f'worker-{platform}', 'path': f'worker-{platform}.json', 'contract': 'audit-worker-result',
                          'sha256': digest(files[f'worker-{platform}.json'])})
        if platform == 'google':
            report = {'schema_version': '1.0.0', 'run_manifest': manifest, 'account_snapshot': account,
                      'control_definitions': [row['control_definition'] for row in plan[platform]], 'findings': findings,
                      'scoring': {'health_score': None, 'evidence_coverage': 0.0, 'status': 'insufficient_evidence', 'categories': []}}
            files['report.json'] = encode(report)
            artifacts.append({'id': 'report', 'path': 'report.json', 'contract': 'report-bundle', 'sha256': digest(files['report.json'])})
    index = {'schema_version': '1.0.0', 'run_id': 'demo-showcase', 'phase': 'Synthetic full audit', 'inputs': inputs, 'artifacts': artifacts}
    root.write('demo-showcase/manifest.json', encode(manifest))
    root.write('demo-showcase/cockpit.json', encode(index))
    for relative, data in files.items():
        root.write('demo-showcase/' + relative, data)
