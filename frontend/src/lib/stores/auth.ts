/**
 * Authentication Store
 *
 * Manages authentication state and JWT token handling.
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';

interface AuthUser {
	username: string;
	role: string;
	token: string;
	expiresAt: number;
}

interface AuthStore {
	user: AuthUser | null;
	isLoading: boolean;
	error: string | null;
}

const TOKEN_KEY = 'signalforge_auth_token';
const USER_KEY = 'signalforge_auth_user';

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthStore>({
		user: null,
		isLoading: true,
		error: null
	});

	// Initialize from localStorage
	if (browser) {
		const storedToken = localStorage.getItem(TOKEN_KEY);
		const storedUser = localStorage.getItem(USER_KEY);

		if (storedToken && storedUser) {
			try {
				const user = JSON.parse(storedUser) as AuthUser;

				// Check if token is expired
				if (user.expiresAt > Date.now()) {
					set({ user, isLoading: false, error: null });
				} else {
					// Token expired, clear storage
					localStorage.removeItem(TOKEN_KEY);
					localStorage.removeItem(USER_KEY);
					set({ user: null, isLoading: false, error: null });
				}
			} catch {
				set({ user: null, isLoading: false, error: null });
			}
		} else {
			set({ user: null, isLoading: false, error: null });
		}
	}

	return {
		subscribe,

		async login(username: string, password: string): Promise<boolean> {
			update((s) => ({ ...s, isLoading: true, error: null }));

			try {
				const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
				const response = await fetch(`${apiUrl}/auth/token`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded'
					},
					body: new URLSearchParams({
						username,
						password
					})
				});

				if (!response.ok) {
					const error = await response.json().catch(() => ({ detail: 'Login failed' }));
					if (error.detail === 'email_not_verified') {
						throw new Error('Email not verified. Check your inbox for a verification link.');
					}
					throw new Error(error.detail || 'Login failed');
				}

				const data = await response.json();
				const token = data.access_token;

				// Get user info
				const meResponse = await fetch(`${apiUrl}/auth/me`, {
					headers: {
						Authorization: `Bearer ${token}`
					}
				});

				if (!meResponse.ok) {
					throw new Error('Failed to get user info');
				}

				const userInfo = await meResponse.json();

				// Calculate expiry (60 minutes by default)
				const expiresAt = Date.now() + 60 * 60 * 1000;

				const user: AuthUser = {
					username: userInfo.username,
					role: userInfo.role,
					token,
					expiresAt
				};

				// Store in localStorage
				if (browser) {
					localStorage.setItem(TOKEN_KEY, token);
					localStorage.setItem(USER_KEY, JSON.stringify(user));
				}

				set({ user, isLoading: false, error: null });
				return true;
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Login failed';
				update((s) => ({ ...s, isLoading: false, error: message }));
				return false;
			}
		},

		async register(
			username: string,
			email: string,
			password: string,
			role: string = 'viewer'
		): Promise<{ success: boolean; error?: string }> {
			update((s) => ({ ...s, isLoading: true, error: null }));

			try {
				const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
				const response = await fetch(`${apiUrl}/auth/register`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded'
					},
					body: new URLSearchParams({
						username,
						email,
						password,
						role
					})
				});

				if (!response.ok) {
					const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
					throw new Error(error.detail || 'Registration failed');
				}

				update((s) => ({ ...s, isLoading: false }));
				return { success: true };
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Registration failed';
				update((s) => ({ ...s, isLoading: false, error: message }));
				return { success: false, error: message };
			}
		},

		logout() {
			if (browser) {
				localStorage.removeItem(TOKEN_KEY);
				localStorage.removeItem(USER_KEY);
			}
			set({ user: null, isLoading: false, error: null });
			goto('/login');
		},

		clearError() {
			update((s) => ({ ...s, error: null }));
		},

		getToken(): string | null {
			let token: string | null = null;
			subscribe((s) => {
				token = s.user?.token || null;
			})();
			return token;
		},

		isTokenExpired(): boolean {
			let expired = true;
			subscribe((s) => {
				if (s.user) {
					expired = s.user.expiresAt <= Date.now();
				}
			})();
			return expired;
		}
	};
}

export const authStore = createAuthStore();

// Derived stores
export const isAuthenticated = derived(authStore, ($auth) => $auth.user !== null);
export const currentUser = derived(authStore, ($auth) => $auth.user);
export const userRole = derived(authStore, ($auth) => $auth.user?.role);
