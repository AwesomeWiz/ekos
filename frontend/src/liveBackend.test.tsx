// @vitest-environment jsdom
// Opt-in: credentials are supplied only to the test process, never to the client bundle.
import { env } from 'node:process';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import { api } from './services/api';

afterEach(() => { cleanup(); sessionStorage.clear(); });
describe.skipIf(!env.EKOS_TEST_EMAIL || !env.EKOS_TEST_PASSWORD)('running FastAPI integration', () => {
  it('signs in through the frontend and renders actual profile and connector data', async () => {
    sessionStorage.clear();
    render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: env.EKOS_TEST_EMAIL } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: env.EKOS_TEST_PASSWORD } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByRole('heading', { name: 'Connectors' }, { timeout: 15000 });
    const token = sessionStorage.getItem('ekos.session-token');
    expect(token).toBeTruthy();
    const profile = await api.getProfile(token!);
    expect(screen.getByText(profile.full_name)).toBeTruthy();
    expect(profile.permissions.some(permission => permission.resource === 'connectors' && permission.action === 'read')).toBe(true);
    const sources = await api.getConnectors(token!);
    const github = sources.filter(source => source.type === 'GitHub' && source.name === 'GitHub');
    expect(github).toHaveLength(1);
    expect(await screen.findByText('GitHub')).toBeTruthy();
    expect(github[0].status).toBeTruthy();
    if (profile.role === 'Developer') {
      expect(screen.queryByRole('button', { name: 'Sync' })).toBeNull();
      expect(screen.queryByRole('button', { name: 'Test connection' })).toBeNull();
    }
    fireEvent.click(screen.getByRole('button', { name: 'Refresh sources' }));
    await screen.findByText('GitHub');
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(sessionStorage.getItem('ekos.session-token')).toBeNull();
    expect(await screen.findByText('Sign in to view your connected sources.')).toBeTruthy();
  }, 30000);
});
