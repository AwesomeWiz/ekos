// @vitest-environment jsdom
// Opt-in: credentials are supplied only to the test process, never to the client bundle.
import { env } from 'node:process';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
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
  it.skipIf(env.EKOS_TEST_LIVE_SEARCH !== '1')('renders a real chat answer and indexed GitHub sources', async () => {
    render(<MemoryRouter initialEntries={['/login']}><App /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: env.EKOS_TEST_EMAIL } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: env.EKOS_TEST_PASSWORD } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await screen.findByRole('heading', { name: 'Connectors' }, { timeout: 15000 });
    const token = sessionStorage.getItem('ekos.session-token')!;
    expect((await api.getSearchStatus(token)).document_count).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('link', { name: 'New chat' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Ask EKOS anything...' }), { target: { value: 'repository branches' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByRole('heading', { name: 'Sources' }, { timeout: 180000 });
    const sources = within(screen.getByRole('complementary', { name: 'Conversation context' }));
    expect(sources.getAllByRole('link').length).toBeGreaterThan(0);
    expect(sources.queryByText('PAY-42')).toBeNull();
    expect(sources.queryByText('Architecture.md')).toBeNull();
    const results = await api.semanticSearch(token, 'repository branches');
    expect(results.results.length).toBeGreaterThan(0);
    expect(results.results.every(result => result.metadata.source === 'github')).toBe(true);
  }, 210000);
});
