"""Generate one-field Orders request variations from the JSON-form OpenAPI document."""
import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OMIT = object()


def resolve(spec, reference):
    value = spec
    for part in reference.strip('#/').split('/'):
        value = value[part]
    return value


def variations(spec):
    params = spec['components']['parameters']
    path_base = {key: param['schema']['example'] for key, param in params.items()}
    for field, param in params.items():
        schema = param['schema']
        low, high = schema['minLength'], schema['maxLength']
        samples = [('existing', path_base[field]), ('unknown', 'ZZZ'), ('format', '!'),
                   ('null', None), ('type', 7), ('omitted', OMIT), ('empty', '')]
        for label, bound in [('min', low), ('max', high)]:
            for suffix, delta in [('below', -1), ('at', 0), ('above', 1)]:
                samples.append((f'{label}-{suffix}', 'A' * (bound + delta)))
        for label, value in samples:
            valid = (isinstance(value, str) and low <= len(value) <= high
                     and bool(re.fullmatch(schema['pattern'], value)))
            reason = 'matches path schema' if valid else 'violates required path type, length or pattern'
            yield case('readOrder', 'path', field, label, path_base, value, valid, reason)

    read = next(item['get'] for item in spec['paths'].values() if 'get' in item)
    query = read['parameters'][0]['name']
    for label, value, valid in [('default', OMIT, True), ('all', 'true', True), ('active', 'false', True),
                                ('text', 'other', False), ('empty', '', False)]:
        yield case(read['operationId'], 'query', query, label, {}, value, valid, 'optional boolean query parameter')

    for item in spec['paths'].values():
        if 'post' not in item:
            continue
        op = item['post']
        ref = op['requestBody']['content']['application/json']['schema']['$ref']
        for field, field_ref in resolve(spec, ref)['properties'].items():
            schema = resolve(spec, field_ref['$ref'])
            if field == 'cancellation_fee':
                samples = fee_samples(schema)
            elif schema['type'] == 'boolean':
                samples = [(label, value, valid, 'optional JSON boolean') for label, value, valid in [
                    ('omitted', OMIT, True), ('true', True, True), ('false', False, True),
                    ('null', None, False), ('text', 'false', False), ('empty', '', False)]]
            else:
                samples = [(label, value, valid, 'optional nullable text without a length bound')
                           for label, value, valid in [('omitted', OMIT, True), ('text', 'Workshop', True),
                                                       ('null', None, True), ('empty', '', True), ('type', 7, False)]]
            for label, value, valid, reason in samples:
                yield case(op['operationId'], 'body', field, label, {'send_email': False}, value, valid, reason)


def case(operation, location, field, label, base, value, valid, reason):
    values = base.copy()
    if value is OMIT:
        values.pop(field, None)
    else:
        values[field] = value
    return {'id': f'{operation}-{field}-{label}', 'operation': operation, 'location': location,
            'field': field, 'input': values, 'valid': valid, 'reason': reason}


def fee_samples(schema):
    numeric = next(s for s in schema['anyOf'] if s['type'] == 'number')
    step = Decimal(str(numeric['multipleOf']))
    low = Decimal(str(numeric['minimum']))
    cap = Decimal(schema['x-fixture-total'])
    yield from [('omitted', OMIT, True, 'optional'), ('null', None, True, 'nullable'),
                ('number', 5, True, 'JSON number in range'), ('text', 'five', False, 'invalid decimal'),
                ('empty', '', False, 'invalid decimal'), ('type', True, False, 'boolean is not a monetary value')]
    for name, bound in [('min', low), ('cap', cap)]:
        for suffix, delta in [('below', -step), ('at', Decimal(0)), ('above', step)]:
            val = bound + delta
            yield f'{name}-{suffix}', str(val.quantize(step)), low <= val <= cap, f'{name} boundary {bound}'
    scale = -step.as_tuple().exponent
    for places in (scale - 1, scale, scale + 1):
        yield f'scale-{places}', '0.' + '1' * places, places <= scale, f'currency has {scale} decimal places'
    storage_max = Decimal(str(numeric['maximum']))
    for suffix, delta in [('below', -step), ('at', Decimal(0)), ('above', step)]:
        val = storage_max + delta
        reason = 'exceeds fixture cap' if val <= storage_max else 'exceeds decimal capacity and fixture cap'
        yield f'capacity-{suffix}', str(val.quantize(step)), False, reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', action='store_true')
    parser.add_argument('--check', action='store_true', help='compare with the committed dataset')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'openapi.yaml').read_text(encoding='utf-8'))
    if args.revision:
        for edit in json.loads((ROOT / 'data/revision.json').read_text()):
            parent, key = edit['path'].rsplit('/', 1)
            resolve(spec, parent)[key] = edit['value']
    cases = list(variations(spec))
    assert len({c['id'] for c in cases}) == len(cases)
    content = ''.join(json.dumps(c, separators=(',', ':')) + '\n' for c in cases)
    dataset = ROOT / 'data' / ('orders-revised.jsonl' if args.revision else 'orders.jsonl')
    if args.check:
        if dataset.read_text(encoding='utf-8') != content:
            raise SystemExit(f'Stale dataset: {dataset}')
    else:
        dataset.write_text(content, encoding='utf-8', newline='\n')
    print(f'{len(cases)} cases: {dataset.name}')


if __name__ == '__main__':
    main()
