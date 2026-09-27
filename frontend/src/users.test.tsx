// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from './App';

const roles = [{ id: 'admin-role', role_name: 'Administrator' }, { id: 'dev-role', role_name: 'Developer' }, { id: 'manager-role', role_name: 'Manager' }];
const admin = { id: 'admin', full_name: 'System Admin', email: 'admin@example.test', role: 'Administrator', organization: 'Team', permissions: [] };
const employee = { id: 'employee', full_name: 'New Developer', email: 'employee@example.test', role_id: 'dev-role', organization_id: 'team', status: true, created_at: '2026-01-01T00:00:00Z' };
beforeEach(() => { sessionStorage.clear(); sessionStorage.setItem('ekos.session-token', 'admin-token'); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
function setup(profile = admin, failure = false) {
  const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
    expect((options?.headers as Record<string, string>).Authorization).toBe('Bearer admin-token');
    if (url.endsWith('/profile')) return Response.json(profile);
    if (url.endsWith('/connectors')) return Response.json([]);
    if (url.endsWith('/users/roles')) return Response.json(roles);
    if (url.endsWith('/users') && options?.method === 'POST') {
      if (failure) return Response.json({ detail: 'An account with this email already exists' }, { status: 409 });
      return Response.json(employee, { status: 201 });
    }
    if (url.endsWith('/users')) return Response.json([]);
    if (url.endsWith('/users/employee')) return Response.json({ ...employee, ...JSON.parse(String(options?.body)) });
    throw new Error(`Unexpected endpoint: ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  render(<MemoryRouter initialEntries={['/admin/users']}><App /></MemoryRouter>);
  return fetchMock;
}
function fill() {
  fireEvent.change(screen.getByLabelText('Full name'), { target: { value: employee.full_name } });
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: employee.email } });
  fireEvent.change(screen.getByLabelText('Initial password'), { target: { value: 'password123' } });
}
describe('admin user management', () => {
  it('creates a Developer with JWT and changes role/status through existing API client', async () => {
    const fetchMock = setup();
    await screen.findByLabelText('Full name');
    expect(screen.getByRole('link', { name: 'User Management' })).toBeTruthy();
    expect(screen.getByLabelText('Role')).toHaveProperty('value', 'dev-role');
    fill(); fireEvent.click(screen.getByRole('button', { name: 'Add User' }));
    await screen.findByText('User created.');
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/users', expect.objectContaining({ method: 'POST', body: JSON.stringify({ full_name: employee.full_name, email: employee.email, password: 'password123', role_id: 'dev-role' }) }));
    expect(screen.getByLabelText('Initial password')).toHaveProperty('value', '');
    expect(JSON.stringify(sessionStorage)).not.toContain('password123');
    const card = within(screen.getByRole('article', { name: employee.full_name }));
    fireEvent.change(card.getByLabelText(`Role for ${employee.full_name}`), { target: { value: 'manager-role' } });
    await screen.findByText('User updated.');
    expect(card.getByRole('combobox')).toHaveProperty('value', 'manager-role');
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/users/employee', expect.objectContaining({ method: 'PUT', body: '{"role_id":"manager-role"}' }));
    fireEvent.click(card.getByRole('button', { name: 'Disable' }));
    await card.findByText('Disabled');
    fireEvent.click(card.getByRole('button', { name: 'Enable' }));
    await card.findByText('Enabled');
  });
  it('blocks Developers and hides admin navigation without fetching users', async () => {
    const fetchMock = setup({ ...admin, role: 'Developer' });
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Administrator access required.');
    expect(screen.queryByRole('link', { name: 'User Management' })).toBeNull();
    expect(fetchMock.mock.calls.some(([url]) => url.includes('/users'))).toBe(false);
  });
  it('shows server validation errors without adding a fake user', async () => {
    setup(admin, true); await screen.findByLabelText('Full name'); fill();
    fireEvent.click(screen.getByRole('button', { name: 'Add User' }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'An account with this email already exists');
    expect(screen.queryByRole('article')).toBeNull();
    expect(screen.getByRole('button', { name: 'Add User' })).toHaveProperty('disabled', false);
  });
});
