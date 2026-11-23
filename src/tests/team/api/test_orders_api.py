"""Black-box tests for the disposable SQE Orders instance. Run via windows.ps1 api."""
import json
import os
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import pytest
import requests

ROOT = Path(__file__).resolve().parents[4]
CASES = [json.loads(row) for row in (ROOT / 'sqe/data/orders.jsonl').read_text().splitlines()]
BASE = 'http://127.0.0.1:18081'
pytestmark = pytest.mark.skipif(os.environ.get('SQE_LIVE_API') != '1', reason='requires reset SQE loopback instance')


@pytest.fixture(scope='module')
def api():
    config = json.loads((ROOT / 'local/sqe/windows/fixtures.json').read_text())
    assert config['baseUrl'] == BASE
    with requests.Session() as session:
        session.trust_env = False

        def call(alias='journey', *, operation=None, role='viewer', body=None, path=None, query=None):
            values = path or dict(organizer=config['organizer'], event=config['event'], code=config['orders'][alias])
            parts = {key: quote(value, safe='') for key, value in values.items()}
            url = BASE + '/api/v1/organizers/{organizer}/events/{event}/orders/{code}/'.format(**parts)
            headers = {'Authorization': 'Token ' + config['roles'][role]['token']} if role else {}
            if operation:
                url += operation + '/'
            return session.request('POST' if operation else 'GET', url, headers=headers, params=query,
                                   json=body, timeout=30, allow_redirects=False)
        yield call


def snapshot(api, alias):
    response = api(alias, query={'include_canceled_positions': 'true'})
    assert response.status_code == 200
    order = response.json()
    fields = {'positions': ('id', 'canceled'), 'fees': ('id', 'fee_type', 'value'),
              'payments': ('local_id', 'state', 'amount', 'provider', 'payment_date'),
              'refunds': ('local_id', 'state', 'amount')}
    state = {key: order[key] for key in ('code', 'status', 'total', 'cancellation_date')}
    for field, keys in fields.items():
        state[field] = [{key: item[key] for key in keys} for item in order[field]]
    return state


def assert_payment(before, after):
    assert before['status'] in ('n', 'e') and not before['payments']
    assert len(after['payments']) == 1
    payment, = after['payments']
    assert (payment['state'], payment['provider'], payment['amount']) == ('confirmed', 'manual', before['total'])
    assert payment['payment_date']
    assert after == {**before, 'status': 'p', 'payments': [payment]}


def assert_cancel(before, after, fee):
    assert before['cancellation_date'] is None and after['cancellation_date']
    assert before['positions'] and all(not p['canceled'] for p in before['positions'])
    expected = {**before, 'status': 'c', 'cancellation_date': after['cancellation_date']}
    if fee:
        charge, = after['fees']
        assert (charge['fee_type'], Decimal(charge['value'])) == ('cancellation', fee)
        expected.update(status='p' if before['payments'] else 'n', total=f'{fee:.2f}', fees=[charge],
                        positions=[{**p, 'canceled': True} for p in before['positions']])
    assert after == expected


def wire_path(case):
    return case['location'] == 'path' and all(isinstance(case['input'].get(field), str)
                                              and case['input'][field] for field in ('organizer', 'event', 'code'))


@pytest.mark.parametrize('case', [c for c in CASES if wire_path(c)], ids=lambda c: c['id'])
def test_get_resource(api, case):
    response = api(path=case['input'])
    if case['id'].endswith('-existing'):
        assert response.status_code == 200
        assert response.json()['code'] == case['input']['code']
    elif case['field'] == 'code':
        assert response.status_code == 404
    else:
        assert response.status_code in (403, 404)


@pytest.fixture(scope='module')
def canceled_position(api):
    alias = 'retained_fee'
    before = snapshot(api, alias)
    assert api(alias, operation='mark_canceled', role='manager',
               body={'send_email': False, 'cancellation_fee': '5.00'}).status_code == 200
    after = snapshot(api, alias)
    assert_cancel(before, after, Decimal('5.00'))
    return after


@pytest.mark.parametrize('case', [c for c in CASES if c['location'] == 'query'], ids=lambda c: c['id'])
def test_read_filter(api, canceled_position, case):
    response = api('retained_fee', query=case['input'])
    # The pinned read filter treats any value other than "true" as false.
    assert response.status_code == 200
    order = response.json()
    assert order['code'] == canceled_position['code']
    visible = [{'id': p['id'], 'canceled': p['canceled']} for p in order['positions']]
    expected = canceled_position['positions'] if case['input'].get('include_canceled_positions') == 'true' else []
    assert visible == expected


@pytest.mark.parametrize('case', [c for c in CASES if c['location'] == 'body'], ids=lambda c: c['id'])
def test_generated_actions(api, case):
    alias, action, body = case['id'], case['operation'], case['input']
    before = snapshot(api, alias)
    response = api(alias, operation=action, role='manager', body=body)
    after = snapshot(api, alias)
    if not case['valid']:
        assert (response.status_code, after == before) == (400, True), 'expected rejection with original state'
    elif action == 'mark_paid':
        assert response.status_code == 200
        assert_payment(before, after)
    else:
        assert response.status_code == 200
        assert_cancel(before, after, Decimal(str(body.get('cancellation_fee') or 0)))


@pytest.mark.parametrize('alias,fee', [('api_no_fee', '0.00'), ('api_keep_fee', '5.00'), ('api_late', '0.00')])
def test_pay_then_cancel_and_replay(api, alias, fee):
    """PAY-01/02/03, CAN-01/02/04, BR-01 through BR-04."""
    before = snapshot(api, alias)
    for action in ('mark_paid', 'mark_canceled'):
        body = {'send_email': False}
        if action == 'mark_canceled':
            body['cancellation_fee'] = fee
        response = api(alias, operation=action, role='manager', body=body)
        assert response.status_code == 200 and response.json()['code'] == before['code']
        after = snapshot(api, alias)
        if action == 'mark_paid':
            assert_payment(before, after)
        else:
            assert_cancel(before, after, Decimal(fee))
            if Decimal(fee):
                assert api(alias).json()['positions'] == []
        assert api(alias, operation=action, role='manager', body=body).status_code == 400
        assert snapshot(api, alias) == after
        before = after


@pytest.mark.parametrize('alias,action', [('api_view_pay', 'mark_paid'), ('api_view_cancel', 'mark_canceled')])
def test_viewer_write_denied(api, alias, action):
    """PAY-04 and CAN-05. Viewer can read each eligible order."""
    before = snapshot(api, alias)
    for role, expected in [(None, 401), ('viewer', 403)]:
        assert api(alias, role=role, operation=action, body={'send_email': False}).status_code == expected
        assert snapshot(api, alias) == before


def test_quota_rejection(api):
    """PAY-02. Rejection must preserve the order and its confirmed balance."""
    before = snapshot(api, 'api_blocked')
    assert before['status'] == 'e' and before['payments'] == []
    assert api('api_blocked', operation='mark_paid', role='manager', body={'send_email': False}).status_code == 400
    after = snapshot(api, 'api_blocked')
    assert after == {**before, 'payments': after['payments']}
    assert len(after['payments']) <= 1
    for attempt in after['payments']:
        assert (attempt['amount'], attempt['provider']) == ('20.00', 'manual')
        assert attempt['state'] in ('created', 'failed', 'canceled')


def test_positionless_cancellation(api):
    """CAN-04 / BR-02 requires an active position."""
    before = snapshot(api, 'positionless')
    assert before['positions'] == []
    assert api('positionless', operation='mark_canceled', role='manager', body={'send_email': False}).status_code == 400
    assert snapshot(api, 'positionless') == before
