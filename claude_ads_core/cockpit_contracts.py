"""Strict dependency-free validation of the portable cockpit wire contracts.

The installed schemas are the structural authority. Only the deliberately small
JSON Schema vocabulary used by these three schemas is implemented here. Schema
changes introducing other keywords fail closed rather than becoming no-ops.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit

# One registration point: contracts.py owns the names and the public CLI choices.
from .contracts import COCKPIT_CONTRACT_NAMES

# RFC 3339 date-time as the schema's format check requires. Python 3.11+
# fromisoformat also accepts the ISO 8601 basic form, which the schema rejects.
_DATE_TIME = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})', re.ASCII)


class CockpitContractError(ValueError):
    """A bounded structural or semantic cockpit contract failure."""


def _check(schema: dict, value: Any, location: str = '$') -> None:
    allowed = {'$schema', '$id', 'title', 'type', 'additionalProperties', 'required',
               'properties', 'items', 'minItems', 'maxItems', 'minLength', 'maxLength',
               'pattern', 'format', 'enum', 'const', 'minimum', 'maximum', 'anyOf'}
    if set(schema) - allowed:
        raise CockpitContractError('unsupported cockpit schema vocabulary')
    def fail():
        raise CockpitContractError(f'{location}: invalid cockpit contract value')
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            try:
                _check(branch, value, location)
                break
            except CockpitContractError:
                pass
        else:
            fail()
    if 'const' in schema and value != schema['const']:
        fail()
    if 'enum' in schema and value not in schema['enum']:
        fail()
    kind = schema.get('type')
    checks = {'object': lambda: isinstance(value, dict), 'array': lambda: isinstance(value, list),
              'string': lambda: isinstance(value, str), 'null': lambda: value is None,
              'boolean': lambda: isinstance(value, bool),
              'integer': lambda: isinstance(value, int) and not isinstance(value, bool),
              'number': lambda: isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)}
    if kind is not None and (kind not in checks or not checks[kind]()):
        fail()
    if isinstance(value, dict):
        props = schema.get('properties', {})
        if any(key not in value for key in schema.get('required', [])):
            fail()
        if schema.get('additionalProperties') is False and set(value) - set(props):
            fail()
        for key in props.keys() & value.keys():
            _check(props[key], value[key], location + '.' + key)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', 100000):
            fail()
        for item in value:
            _check(schema.get('items', {}), item, location + '[]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', 1000000):
            fail()
        # Every cockpit pattern is anchored. fullmatch also rejects a trailing
        # newline, which Python's $ would otherwise accept.
        if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
            fail()
        try:
            fmt = schema.get('format')
            if fmt == 'date':
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
                    fail()
                date.fromisoformat(value)
            elif fmt == 'date-time':
                if not _DATE_TIME.fullmatch(value) or datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                    fail()
            elif fmt == 'uri':
                parsed = urlsplit(value)
                if parsed.scheme not in {'https', 'http'} or not parsed.hostname or parsed.username or parsed.password:
                    fail()
        except ValueError:
            fail()
    if kind in {'number', 'integer'}:
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf):
            fail()


def validate_cockpit_contract(name: str, payload: Any) -> None:
    """Validate an index, display snapshot, or redacted action receipt."""
    if name not in COCKPIT_CONTRACT_NAMES:
        raise CockpitContractError('unknown cockpit contract')
    schema = json.loads(files('claude_ads_core').joinpath('schemas', 'v1', name + '.schema.json').read_text(encoding='utf-8'))
    try:
        _check(schema, payload)
        if name == 'cockpit-index':
            rows = payload['inputs'] + payload['artifacts']
            if len({row['id'] for row in rows}) != len(rows) or len({row['path'] for row in rows}) != len(rows):
                raise CockpitContractError('cockpit index requires unique IDs and paths')
            for row in rows:
                if row['path'].startswith('cockpit/') or row['path'] in {'manifest.json', 'cockpit.json'}:
                    raise CockpitContractError('cockpit index contains a reserved output path')
                if len(row['path'].split('/')) > 16 or any(len(part) > 128 for part in row['path'].split('/')):
                    raise CockpitContractError('cockpit index path exceeds bounds')
        elif name == 'cockpit-snapshot':
            from .contracts import validate_contract
            for row in payload['findings']:
                validate_contract('finding', row['finding'])
            for account in payload['accounts']:
                if account['window']['end'] < account['window']['start']:
                    raise CockpitContractError('cockpit account window is inverted')
            for score in payload['scoring']:
                if score['profile_status'] == 'disabled' and (score['health_score'] is not None or score['evidence_coverage'] != 0 or score['status'] != 'insufficient_evidence'):
                    raise CockpitContractError('disabled cockpit profile cannot expose a health score or approved coverage')
            identities = set()
            for row in payload['receipts']:
                receipt = row['receipt']
                validate_cockpit_contract('cockpit-action-receipt', receipt)
                if receipt['run_id'] != payload['run_id'] or row['path'] != 'cockpit/receipts/' + receipt['action_id'] + '.json' or receipt['action_id'] in identities:
                    raise CockpitContractError('cockpit history subject or identity mismatch')
                identities.add(receipt['action_id'])
        else:
            if datetime.fromisoformat(payload['finished_at'].replace('Z', '+00:00')) < datetime.fromisoformat(payload['started_at'].replace('Z', '+00:00')):
                raise CockpitContractError('cockpit receipt timestamps are inverted')
    except (RecursionError, TypeError, KeyError, OverflowError) as exc:
        raise CockpitContractError('invalid cockpit contract structure') from exc
