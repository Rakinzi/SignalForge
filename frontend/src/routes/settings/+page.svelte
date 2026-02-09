<script lang="ts">
	import { onMount } from 'svelte';
	import { getConfig, getVersion, normalizeApiError } from '$lib/api/client';
	import type { SystemConfig } from '$lib/types';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateForbidden from '$lib/components/PageStateForbidden.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';

	let config = $state<SystemConfig | null>(null);
	let version = $state<string>('');
	let loading = $state(true);
	let error = $state<string | null>(null);
	let isForbidden = $state(false);

	async function loadSettings() {
		loading = true;
		error = null;
		isForbidden = false;
		try {
			const [configData, versionData] = await Promise.all([getConfig(), getVersion()]);
			config = configData;
			version = versionData.version;
		} catch (err) {
			config = null;
			version = '';
			const normalized = normalizeApiError(err, 'Failed to load settings');
			if (normalized.kind === 'forbidden') {
				isForbidden = true;
			} else {
				error = normalized.message;
			}
		} finally {
			loading = false;
		}
	}

	onMount(loadSettings);
</script>

<svelte:head>
	<title>Settings</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-[var(--text-primary)]">System Settings</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Configuration and platform metadata.
			</p>
		</div>
		<button
			onclick={loadSettings}
			disabled={loading}
			class="rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<PageStateLoading label="Loading settings..." />
	{:else if isForbidden}
		<PageStateForbidden
			title="System settings are admin-only"
			message="You can continue using operational pages, but configuration details require elevated access."
			requiredRole="admin"
		/>
	{:else if error}
		<PageStateError message={error} onAction={loadSettings} />
	{:else if config}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
				<h2 class="text-lg font-semibold text-[var(--text-primary)]">Platform</h2>
				<div class="mt-4 space-y-3 text-sm">
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Version</span>
						<span class="font-mono text-[var(--text-primary)]">{version}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Rules Version</span>
						<span class="font-mono text-[var(--text-primary)]">{config.rules_version}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Capture Interface</span>
						<span class="font-mono text-[var(--text-primary)]">{config.capture_interface}</span>
					</div>
				</div>
			</div>

			<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
				<h2 class="text-lg font-semibold text-[var(--text-primary)]">Detection Configuration</h2>
				<div class="mt-4 space-y-3 text-sm">
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Detector Status</span>
						<span class="font-medium text-[var(--text-primary)]">
							{config.detector_enabled ? 'Enabled' : 'Disabled'}
						</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Baseline Window</span>
						<span class="font-medium text-[var(--text-primary)]">{config.baseline_window_hours}h</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-[var(--text-secondary)]">Alert Threshold</span>
						<span class="font-medium text-[var(--text-primary)]">
							{(config.alert_threshold * 100).toFixed(0)}%
						</span>
					</div>
				</div>
			</div>
		</div>

		<div class="rounded-2xl border border-sky-300/70 bg-sky-50 p-5 text-sm text-sky-900 shadow-[var(--shadow-soft)] dark:border-sky-700/50 dark:bg-sky-900/20 dark:text-sky-200">
			Configuration is read-only in the dashboard. Service configuration files remain the source of truth.
		</div>
	{/if}
</div>
