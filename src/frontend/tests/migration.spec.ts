import { expect, test } from '@playwright/test';

test('existing theme and knowledge routes work against the real backend', async ({
    page,
}, testInfo) => {
    const identity = {
        name: `browser-${testInfo.project.name}`,
        email: `browser-${testInfo.project.name}@example.com`,
        password: 'Strong!123456789',
    };
    expect((await page.request.post('/api/v1/auth/signup', { data: identity })).ok()).toBeTruthy();
    const login = await page.request.post('/api/v1/auth/login', { data: identity });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token;
    const headers = { Authorization: `Bearer ${token}` };
    await page.request.patch('/api/v1/auth/me/guide', { headers, data: { seen: true } });
    const created = await page.request.post('/api/v1/knowledge/', {
        headers,
        data: {
            title: 'Browser migration note',
            content: 'Preserve the existing UI',
            topic: 'Testing',
        },
    });
    expect(created.ok()).toBeTruthy();
    const knowledge = await created.json();
    await page.addInitScript((accessToken) => {
        sessionStorage.setItem('hippobox_access_token', accessToken);
        localStorage.setItem('lang', 'en');
    }, token);
    await page.goto('/app');
    await expect(page.getByText('Browser migration note').first()).toBeVisible();
    if (testInfo.project.name === 'dark') await expect(page.locator('html')).toHaveClass(/dark/);
    else await expect(page.locator('html')).not.toHaveClass(/dark/);
    await page.screenshot({ path: testInfo.outputPath('library.png'), fullPage: true });
    await expect(page.locator('nav').first()).toBeVisible();
    for (const route of [
        `/app/knowledge/${knowledge.id}`,
        `/app/knowledge/${knowledge.id}/edit`,
        '/app/mcp',
        '/app/insights',
        '/app/settings',
    ]) {
        await page.goto(route);
        await expect(page.locator('nav').first()).toBeVisible();
        await expect(page.getByText('Cannot connect to HippoBox')).toHaveCount(0);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/app/knowledge/${knowledge.id}`);
    await expect(page.getByText('Preserve the existing UI').first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Create knowledge' })).toBeVisible();
    expect(
        await page.evaluate(
            () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
        ),
    ).toBeTruthy();
    await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true });
});

test('configuration failure is recoverable without an assumed login mode', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('lang', 'en'));
    await page.route('**/config', (route) => route.fulfill({ status: 503, body: '{}' }));
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Cannot connect to HippoBox' })).toBeVisible();
    await page.unroute('**/config');
    await page.getByRole('button', { name: 'Try again' }).click();
    await expect(page.getByRole('heading', { name: 'Cannot connect to HippoBox' })).toHaveCount(0);
    await expect(page.locator('input[type=email]')).toBeVisible();
});

test('signup explains duplicate names and allows retry', async ({ page }, testInfo) => {
    const name = `signup-${testInfo.project.name}`;
    const password = 'Strong!123456789';
    expect(
        (
            await page.request.post('/api/v1/auth/signup', {
                data: { name, email: `${name}@example.com`, password },
            })
        ).ok(),
    ).toBeTruthy();
    await page.addInitScript(() => localStorage.setItem('lang', 'en'));
    await page.goto('/signup');
    await page.locator('#signup-name').fill(name);
    await page.locator('#signup-email').fill(`retry-${name}@example.com`);
    await page.locator('#signup-password').fill(password);
    await page.locator('#signup-password-confirm').fill(password);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(page.getByText('This name is already in use.')).toBeVisible();
    await expect(page.getByText(/IntegrityError|INSERT INTO/)).toHaveCount(0);
    await page.locator('#signup-name').fill(`retry-${name}`);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(page).toHaveURL(/\/signup\/success/);
});

test('auth errors use shared localized messages without server internals', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('lang', 'en'));
    await page.route('**/api/v1/auth/login', (route) =>
        route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({
                detail: {
                    error: 'INVALID_CREDENTIALS',
                    message: 'private SQL',
                    limit_count: 3,
                },
            }),
        }),
    );
    await page.goto('/');
    await page.locator('#login-email').fill('test@example.com');
    await page.locator('#login-password').fill('Strong!123456789');
    await page.locator('button[type=submit]').click();
    await expect(page.getByText(/Remaining login attempts: 3/)).toBeVisible();
    await page.unroute('**/api/v1/auth/login');
    await page.route('**/api/v1/auth/login', (route) =>
        route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: { error: 'UNKNOWN_ERROR', message: 'private SQL' } }),
        }),
    );
    await page.locator('button[type=submit]').click();
    await expect(page.getByText('Login failed. Please try again.')).toBeVisible();
    await expect(page.getByText('private SQL')).toHaveCount(0);
});
