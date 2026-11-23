import { expect, pay, test } from './orders.js';

async function cancel(page, fee) {
    await page.getByRole('link', { name: /Cancel order$/ }).click();
    await page.getByLabel('Keep a cancellation fee of').fill(fee);
    await page.getByLabel('Notify customer by email').uncheck();
    await page.getByRole('button', { name: 'Yes, cancel order', exact: true }).click();
}

async function expectCancellation(page, before, after, fee) {
    await expect(page.locator('.alert-success').filter({ hasText: 'The order has been canceled.' })).toBeVisible();
    expect(before.positions).toEqual([expect.objectContaining({ canceled: false })]);
    expect(before.cancellationDate).toBeNull();
    const expected = { ...before, cancellationDate: expect.any(String), status: 'c' };
    if (fee) {
        expected.status = before.status;
        expected.positions = before.positions.map(p => ({ ...p, canceled: true }));
        expected.fees = [{ type: 'cancellation', value: fee }];
        expected.total = fee;
    }
    expect(after).toEqual(expected);
}

const capError = 'The cancellation fee cannot be higher than the total amount of this order.';
const scaleError = 'Ensure that there are no more than 2 decimal places.';

for (const [id, alias, initial, fee, error] of [
    ['M', 'fee_paid', 'p', '19.99'],
    ['A1', 'fee_equal', 'p', '20.00'],
    ['A2', 'fee_unfunded', 'n', '5.00'],
    ['E1', 'fee_above', 'p', '20.01', capError],
    ['E2', 'fee_scale', 'p', '5.001', scaleError],
]) {
    test('UC-03-' + id + ' ' + alias, async ({ page, orders }) => {
        const read = () => orders.read(alias, { includeCanceled: true });
        const before = await read();
        expect(before).toMatchObject({ status: initial, total: '20.00', fees: [], refunds: [] });
        expect(before.payments).toHaveLength(initial === 'p' ? 1 : 0);
        await orders.open(alias);
        await cancel(page, fee);
        if (error) {
            await expect(page.getByText(error, { exact: true })).toBeVisible();
            expect(await read()).toEqual(before);
        } else {
            await expectCancellation(page, before, await read(), fee);
        }
    });
}

for (const [id, alias, initial, fee] of [
    ['M', 'flow_no_fee', 'n', ''],
    ['A1', 'flow_fee', 'n', '5.00'],
    ['A2', 'flow_expired', 'e', ''],
    ['E1', 'flow_blocked', 'e', ''],
    ['E2', 'flow_reject_fee', 'n', '20.01'],
]) {
    test('UC-04-' + id + ' ' + alias, async ({ page, orders }, testInfo) => {
        test.setTimeout(60_000);
        const read = () => orders.read(alias, { includeCanceled: true });
        const before = await read();
        expect(before).toMatchObject({ status: initial, total: '20.00', payments: [], fees: [], refunds: [] });
        await orders.open(alias);
        await pay(page);
        if (id === 'E1') {
            await expect(page.getByText(/Limited ticket.*no longer available/)).toBeVisible();
            const rejected = await read();
            expect(rejected).toEqual({ ...before, payments: [expect.objectContaining({ state: 'failed', amount: '20.00' })] });
            return;
        }
        await expect(page.getByText('The payment has been created successfully.', { exact: true })).toBeVisible();
        const paid = await read();
        expect(paid).toEqual({ ...before, status: 'p', payments: [
            expect.objectContaining({ state: 'confirmed', provider: 'manual', amount: '20.00' }),
        ] });
        await cancel(page, fee);
        if (id === 'E2') {
            await expect(page.getByText(capError, { exact: true })).toBeVisible();
            expect(await read()).toEqual(paid);
            return;
        }
        const canceled = await read();
        await expectCancellation(page, paid, canceled, fee);
        await testInfo.attach('same-order-readbacks', {
            contentType: 'application/json',
            body: JSON.stringify({ before, paid, canceled }, null, 2),
        });
    });
}
