import { createHash } from 'node:crypto';
import { expect, test } from '@playwright/test';

test('MCP authorization preserves login context and requires explicit consent', async ({
    page,
}, testInfo) => {
    const origin = 'http://127.0.0.1:8127';
    const email = `oauth-${testInfo.project.name}-${Date.now()}@example.com`;
    const password = 'Strong!123abc';
    const signup = await page.request.post('/api/v1/auth/signup', {
        data: { email, name: `oauth-${testInfo.project.name}`, password },
    });
    expect(signup.ok()).toBeTruthy();
    const registered = await page.request.post('/oauth/register', {
        data: {
            client_name: 'ChatGPT test',
            redirect_uris: ['https://chatgpt.com/connector_platform_oauth_redirect'],
            token_endpoint_auth_method: 'none',
            grant_types: ['authorization_code', 'refresh_token'],
            response_types: ['code'],
        },
    });
    expect(registered.status()).toBe(201);
    const { client_id } = await registered.json();
    const verifier = 'a'.repeat(64);
    const params = new URLSearchParams({
        client_id,
        redirect_uri: 'https://chatgpt.com/connector_platform_oauth_redirect',
        response_type: 'code',
        scope: 'knowledge:read knowledge:write',
        resource: `${origin}/mcp`,
        state: 'browser-test',
        code_challenge: createHash('sha256').update(verifier).digest('base64url'),
        code_challenge_method: 'S256',
    });
    await page.goto(`/oauth/authorize?${params}`);
    await expect(page.getByRole('heading', { name: 'Connect HippoBox' })).toBeVisible();
    await page.getByRole('button', { name: 'Sign in to continue' }).click();
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page.getByText(email, { exact: true })).toBeVisible();
    await expect(page.getByText('Create, edit and delete my knowledge')).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath('mcp-consent.png'), fullPage: true });
    let callback = '';
    await page.route('https://chatgpt.com/connector_platform_oauth_redirect?**', async (route) => {
        callback = route.request().url();
        await route.fulfill({ body: 'OAuth callback received', contentType: 'text/plain' });
    });
    await page.getByRole('button', { name: 'Allow connection' }).click();
    await expect(page.getByText('OAuth callback received')).toBeVisible();
    const query = new URL(callback).searchParams;
    expect(query.get('state')).toBe('browser-test');
    expect(query.get('iss')).toBe(origin);
    const tokens = await page.request.post(`${origin}/oauth/token`, {
        form: {
            grant_type: 'authorization_code',
            client_id,
            code: query.get('code')!,
            code_verifier: verifier,
            redirect_uri: 'https://chatgpt.com/connector_platform_oauth_redirect',
            resource: `${origin}/mcp`,
        },
    });
    expect(tokens.status()).toBe(200);
    const access = (await tokens.json()).access_token;
    expect(access).toMatch(/^hpm_/);
    await page.goto('/app/mcp');
    await expect(page.getByRole('heading', { name: 'Connected MCP clients' })).toBeVisible();
    await page.getByRole('button', { name: 'Disconnect', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Connected MCP clients' })).toHaveCount(0);
    const revoked = await page.request.get('/api/v1/knowledge/list', {
        headers: { Authorization: `Bearer ${access}` },
    });
    expect(revoked.status()).toBe(401);
});
