// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';
import type { Connector } from './services/api';

const profile = { id: 'admin', full_name: 'System Admin', role: 'Administrator', permissions: [{ resource: 'connectors', action: 'read' }, { resource: 'connectors', action: 'test' }, { resource: 'connectors', action: 'sync' }] };
function connector(type: string, status: string): Connector {
  return { id: type.toLowerCase(), name: `Team ${type}`, type, status, organization_id: 'org', created_at: '2026-01-01T00:00:00Z', configuration: null };
}
beforeEach(() => { sessionStorage.clear(); sessionStorage.setItem('ekos.session-token', 'connector-token'); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function setup(list: () => Promise<Response>, test?: () => Promise<Response>) {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer connector-token');
    if (url.endsWith('/profile')) return Response.json(profile);
    if (url.endsWith('/connectors')) return list();
    if (url.endsWith('/test') && test) return test();
    throw new Error(`Unexpected endpoint ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter initialEntries={['/connectors']}><App /></MemoryRouter>);
  return fetchMock;
}
describe('connector availability and health', () => {
  it('renders real records, distinguishes health, and shows missing supported types', async () => {
    setup(async () => Response.json([connector('GitHub', 'connected'), connector('Jira', 'unhealthy'), connector('Confluence', 'configured')]));
    const github = within(await screen.findByRole('group', { name: 'Team GitHub' }));
    expect(github.getByText('GitHub · Configured · Working')).toBeTruthy();
    expect(github.getByRole('button', { name: 'Test connection' })).toHaveProperty('disabled', false);
    const jira = within(screen.getByRole('group', { name: 'Team Jira' }));
    expect(jira.getByText('Jira · Configured · Unhealthy')).toBeTruthy();
    expect(jira.queryByRole('button')).toBeNull();
    expect(jira.getByText('Test/sync unavailable in this backend.')).toBeTruthy();
    expect(screen.getByText('Confluence · Configured · Not yet verified')).toBeTruthy();
    const slack = within(screen.getByRole('group', { name: 'Slack' }));
    expect(slack.getByText('Supported · Not configured')).toBeTruthy();
    expect(slack.queryByRole('button')).toBeNull();
    expect(screen.queryByText(/Planned:/)).toBeNull();
  });
  it('does not treat active/registered as connected or enable explicitly unconfigured GitHub', async () => {
    setup(async () => Response.json([connector('GitHub', 'not_configured'), connector('Jira', 'active'), connector('Slack', 'registered')]));
    const github = within(await screen.findByRole('group', { name: 'Team GitHub' }));
    expect(github.getByRole('button', { name: 'Test connection' })).toHaveProperty('disabled', true);
    expect(github.getByRole('button', { name: 'Sync' })).toHaveProperty('disabled', true);
    expect(screen.getByText('Jira · Not yet verified')).toBeTruthy();
    expect(screen.getByText('Slack · Not yet verified')).toBeTruthy();
    expect(screen.queryByText(/Configured · Working/)).toBeNull();
  });
  it('does not assume unconfigured records when loading the backend fails', async () => {
    setup(async () => Response.json({ detail: 'Connector service unavailable' }, { status: 503 }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Connector service unavailable');
    expect(screen.queryByText('Supported · Not configured')).toBeNull();
    expect(screen.getByText('Supported connector types: GitHub · Jira · Confluence · Slack')).toBeTruthy();
  });
  it('refreshes backend health after failed GitHub tests and never invents success', async () => {
    let status = 'configured';
    const fetchMock = setup(async () => Response.json([connector('GitHub', status)]), async () => {
      status = 'error'; return Response.json({ status: 'error', connector: 'GitHub', account: '' });
    });
    await screen.findByRole('group', { name: 'Team GitHub' });
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Connection test did not confirm a working connection (status: error).');
    await screen.findByText('GitHub · Configured · Unhealthy');
    expect(screen.queryByText(/Connected as/)).toBeNull();
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/connectors'))).toHaveLength(2));
  });
});
