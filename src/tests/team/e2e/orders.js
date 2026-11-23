import { readFile } from 'node:fs/promises';
import { expect, test as base } from '@playwright/test';

const fixtureFile = new URL('../../../../local/sqe/windows/fixtures.json', import.meta.url);

export const test = base.extend({
    orders: async ({ page, request }, use) => {
        const fixtures = JSON.parse(await readFile(fixtureFile, 'utf8'));
        const prefix = '/' + [fixtures.organizer, fixtures.event].map(encodeURIComponent).join('/');

        const codeFor = (alias) => {
            const code = fixtures.orders[alias];
            if (!code) throw new Error('Unknown SQE order fixture: ' + alias);
            return code;
        };

        await use({
            priorPaymentDate: fixtures.priorPaymentDate,
            async open(alias, role = 'manager') {
                const credentials = fixtures.roles[role];
                const code = codeFor(alias);
                const orderPath = '/control/event' + prefix + '/orders/' + code + '/';
                await page.goto(orderPath);
                await page.getByLabel('Email', { exact: true }).fill(credentials.email);
                await page.getByLabel('Password', { exact: true }).fill(credentials.password);
                await page.getByRole('button', { name: 'Log in', exact: true }).click();
                await expect(page).toHaveURL(new RegExp(orderPath + '$'));
                await expect(page.getByRole('heading', { name: new RegExp(code) })).toBeVisible();
            },
            async read(alias, { includeCanceled = false } = {}) {
                const code = codeFor(alias);
                const path = '/api/v1/organizers/' + encodeURIComponent(fixtures.organizer)
                    + '/events/' + encodeURIComponent(fixtures.event) + '/orders/' + code + '/';
                const response = await request.get(path, {
                    headers: { Authorization: 'Token ' + fixtures.roles.viewer.token },
                    params: { include_canceled_positions: String(includeCanceled) },
                });
                expect(response.status(), 'scoped API order read').toBe(200);
                const order = await response.json();
                expect(order.code).toBe(code);
                const { status, total, cancellation_date: cancellationDate, positions, payments, fees, refunds } = order;
                return {
                    code,
                    status,
                    total,
                    cancellationDate,
                    positions: positions.map(({ id, canceled }) => ({ id, canceled })),
                    payments: payments.map(({ local_id: id, amount, provider, state, payment_date: date }) => ({
                        id, amount, provider, state, date,
                    })),
                    fees: fees.map(({ fee_type: type, value }) => ({ type, value })),
                    refunds: refunds.map(({ local_id: id, amount, state }) => ({ id, amount, state })),
                };
            },
        });
    },
});

export { expect };

export async function pay(page, { amount = '20.00', date } = {}) {
    await page.getByRole('link', { name: /Mark as paid$/ }).click();
    await page.getByLabel('Payment amount').fill(amount);
    await page.getByLabel('Notify customer by email').uncheck();
    if (date) {
        const dateField = page.getByLabel('Payment date');
        await dateField.fill(date);
        await dateField.press('Escape');
    }
    await page.getByRole('button', { name: 'Create payment', exact: true }).click();
}
