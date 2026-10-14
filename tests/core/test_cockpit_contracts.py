"""Portable wire validation, independent of POSIX secure filesystem support."""
from __future__ import annotations

import copy
import json

import pytest

from claude_ads_core.cockpit_contracts import CockpitContractError, validate_cockpit_contract
from claude_ads_core.contracts import validate_contract, ContractError


@pytest.fixture
def wires(repo_root):
    root = repo_root / 'tests/fixtures/cockpit'
    return {'cockpit-index': json.loads((root / 'synthetic-run/cockpit.json').read_text()),
            'cockpit-snapshot': json.loads((root / 'wire/snapshot.json').read_text()),
            'cockpit-action-receipt': json.loads((root / 'wire/receipt.json').read_text())}


def schema(repo_root, name):
    jsonschema = pytest.importorskip('jsonschema')
    value = json.loads((repo_root / 'claude_ads_core/schemas/v1' / (name + '.schema.json')).read_text())
    return jsonschema.Draft202012Validator(value, format_checker=jsonschema.FormatChecker())


@pytest.mark.parametrize('name', ['cockpit-index', 'cockpit-snapshot', 'cockpit-action-receipt'])
def test_wire_structural_parity_and_registration(wires, repo_root, name):
    payload = wires[name]
    checker = schema(repo_root, name)
    checker.validate(payload)
    validate_cockpit_contract(name, payload)
    validate_contract(name, payload)
    for key in checker.schema['required']:
        broken = copy.deepcopy(payload)
        del broken[key]
        assert not checker.is_valid(broken)
        with pytest.raises(CockpitContractError):
            validate_cockpit_contract(name, broken)
    for broken in ({**payload, 'extra': 'unsupported'}, {**payload, 'schema_version': '2.0.0'}):
        assert not checker.is_valid(broken)
        with pytest.raises(CockpitContractError):
            validate_cockpit_contract(name, broken)
        with pytest.raises(ContractError):
            validate_contract(name, broken)


@pytest.mark.parametrize('name,field', [('cockpit-snapshot', 'artifacts'), ('cockpit-action-receipt', 'outputs')])
@pytest.mark.parametrize('value', [True, False, 0.5, '0', None, -1])
def test_all_size_integer_fields_schema_and_runtime_reject_invalid(wires, repo_root, name, field, value):
    payload = copy.deepcopy(wires[name])
    payload[field][0]['size'] = value
    assert not schema(repo_root, name).is_valid(payload)
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract(name, payload)


@pytest.mark.parametrize('name,field', [('cockpit-snapshot', 'artifacts'), ('cockpit-action-receipt', 'outputs')])
@pytest.mark.parametrize('value', [0, 1, 10000])
def test_all_size_integer_fields_accept_nonnegative_integers(wires, repo_root, name, field, value):
    payload = copy.deepcopy(wires[name])
    payload[field][0]['size'] = value
    schema(repo_root, name).validate(payload)
    validate_cockpit_contract(name, payload)


@pytest.mark.parametrize('name,field', [('cockpit-snapshot', 'artifacts'), ('cockpit-action-receipt', 'outputs')])
def test_size_lexical_integral_float_rejected_like_existing_runtime(wires, repo_root, name, field):
    payload = copy.deepcopy(wires[name])
    payload[field][0]['size'] = 0.0
    # Draft 2020-12 treats an integral number as integer. The Python runtime
    # deliberately retains the repository's stricter lexical integer rule.
    assert schema(repo_root, name).is_valid(payload)
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract(name, payload)


def test_portable_validator_rejects_findings_without_pass_fail_evidence(wires, repo_root):
    payload = copy.deepcopy(wires['cockpit-snapshot'])
    payload['findings'] = [{'platform': 'google', 'account_key': None, 'control_title': 'Synthetic check', 'severity': 'informational', 'claim_ids': [], 'source_ids': [],
        'evidence_status': 'missing', 'finding': {'schema_version': '1.0.0', 'control_id': 'synthetic-control', 'status': 'fail', 'evidence': [],
            'confidence': 'none', 'observation': '', 'diagnosis': '', 'recommendation': ''}}]
    assert not schema(repo_root, 'cockpit-snapshot').is_valid(payload)
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract('cockpit-snapshot', payload)


@pytest.mark.parametrize('field', ['health_score','evidence_coverage'])
def test_huge_wire_numeric_value_is_a_bounded_contract_error(wires, field):
    payload = copy.deepcopy(wires['cockpit-snapshot'])
    payload['scoring'][0][field] = 10 ** 400
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract('cockpit-snapshot', payload)


def test_disabled_profile_rejects_numeric_health_and_approved_coverage(wires):
    for field, value in [('health_score', 90), ('evidence_coverage', 100), ('status','normal')]:
        payload = copy.deepcopy(wires['cockpit-snapshot'])
        payload['scoring'][0][field] = value
        with pytest.raises(CockpitContractError,match='disabled cockpit profile'):
            validate_cockpit_contract('cockpit-snapshot', payload)


def test_embedded_history_validates_canonical_receipt_subject(wires, repo_root):
    payload = copy.deepcopy(wires['cockpit-snapshot'])
    receipt = copy.deepcopy(wires['cockpit-action-receipt'])
    receipt['run_id'] = payload['run_id']
    row = {'path':'cockpit/receipts/'+receipt['action_id']+'.json','sha256':'a'*64,'size':123,'receipt':receipt}
    payload['receipts'] = [row]
    schema(repo_root,'cockpit-snapshot').validate(payload)
    validate_cockpit_contract('cockpit-snapshot',payload)
    receipt['finished_at'] = '2000-01-01T00:00:00Z'
    with pytest.raises(CockpitContractError,match='timestamps are inverted'):
        validate_cockpit_contract('cockpit-snapshot',payload)


def test_pattern_checks_reject_a_trailing_newline(wires):
    receipt = copy.deepcopy(wires['cockpit-action-receipt'])
    validate_cockpit_contract('cockpit-action-receipt', receipt)
    for field in ('action_id', 'run_id', 'input_fingerprint', 'policy_fingerprint'):
        broken = copy.deepcopy(receipt)
        broken[field] = broken[field] + '\n'
        with pytest.raises(CockpitContractError):
            validate_cockpit_contract('cockpit-action-receipt', broken)


@pytest.mark.parametrize('value', ['20261008T101010Z', '2026-10-08T10:10:10', '2026-10-08 10:10:10Z', '2026-10-08T10:10:10z', '2026-10-08T10:10Z', '\u0662\u0660\u0662\u0666-10-08T10:10:10Z', '2026-10-08T10:10:10Z\n'])
def test_date_time_rejects_forms_the_schema_format_rejects(wires, value):
    receipt = copy.deepcopy(wires['cockpit-action-receipt'])
    receipt['started_at'] = receipt['finished_at'] = value
    with pytest.raises(CockpitContractError):
        validate_cockpit_contract('cockpit-action-receipt', receipt)


@pytest.mark.parametrize('value', ['2026-10-08T10:10:10Z', '2026-10-08T10:10:10.5Z', '2026-10-08T10:10:10+02:00'])
def test_date_time_accepts_rfc3339_forms(wires, value):
    receipt = copy.deepcopy(wires['cockpit-action-receipt'])
    receipt['started_at'] = receipt['finished_at'] = value
    validate_cockpit_contract('cockpit-action-receipt', receipt)


def test_schema_files_are_read_with_an_explicit_encoding(wires, monkeypatch):
    import pathlib
    seen = []
    original = pathlib.Path.read_text
    def spy(self, *args, **kwargs):
        seen.append(kwargs.get('encoding', args[0] if args else None))
        return original(self, *args, **kwargs)
    monkeypatch.setattr(pathlib.Path, 'read_text', spy)
    validate_cockpit_contract('cockpit-action-receipt', wires['cockpit-action-receipt'])
    assert seen and set(seen) == {'utf-8'}


def test_cockpit_contract_names_have_one_definition():
    from claude_ads_core import cockpit_contracts, contracts
    assert cockpit_contracts.COCKPIT_CONTRACT_NAMES is contracts.COCKPIT_CONTRACT_NAMES
