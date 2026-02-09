// Authentication module for API access

import { browser } from '$app/environment';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const SESSION_TOKEN_KEY = 'signalforge_auth_token';

// Default credentials (development only)
const DEFAULT_USERNAME = import.meta.env.VITE_API_USERNAME || 'viewer';
const DEFAULT_PASSWORD = import.meta.env.VITE_API_PASSWORD || 'viewer';

let accessToken: string | null = null;
let tokenExpiry: number = 0;

export async function getAccessToken(): Promise<string | null> {
	// Prefer active session token from auth store/localStorage.
	if (browser) {
		const sessionToken = localStorage.getItem(SESSION_TOKEN_KEY);
		if (sessionToken) {
			return sessionToken;
		}
	}

	// Return cached token if still valid
	if (accessToken && Date.now() < tokenExpiry) {
		return accessToken;
	}

	try {
		// Request new token
		const formData = new URLSearchParams();
		formData.append('username', DEFAULT_USERNAME);
		formData.append('password', DEFAULT_PASSWORD);

		const response = await fetch(`${API_BASE_URL}/auth/token`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			},
			body: formData.toString(),
			signal: AbortSignal.timeout(3000)
		});

		if (!response.ok) {
			console.error('Failed to authenticate:', response.status);
			return null;
		}

		const data = await response.json();
		accessToken = data.access_token;

		// Set expiry to 50 minutes (token expires in 60 minutes by default)
		tokenExpiry = Date.now() + 50 * 60 * 1000;

		console.log('Successfully authenticated with backend API');
		return accessToken;
	} catch (error) {
		console.error('Authentication error:', error);
		return null;
	}
}

export function clearToken(): void {
	accessToken = null;
	tokenExpiry = 0;
}
