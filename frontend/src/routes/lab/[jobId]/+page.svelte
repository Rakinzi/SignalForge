<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { getDetectionJob, exportDetectionJob, normalizeApiError } from '$lib/api/client';
	import type { LabJob } from '$lib/types';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let job = $state<LabJob | null>(null);
	let exporting = $state<'json' | 'csv' | null>(null);

	let jobId = $derived($page.params.jobId ?? '');

	function harareTime(value: string): string {
		return new Date(value).toLocaleString('en-ZW', { timeZone: 'Africa/Harare' });
	}

	async function loadJob() {
		loading = true;
		error = null;
		if (!jobId) {
			error = 'Missing job id.';
			loading = false;
			return;
		}
		try {
			job = await getDetectionJob(jobId);
		} catch (err) {
			error = normalizeApiError(err, 'Failed to load job details').message;
		} finally {
			loading = false;
		}
	}

	async function handleExport(format: 'json' | 'csv') {
		if (!jobId) return;
		exporting = format;
		try {
			const payload = await exportDetectionJob(jobId, format);
			const blob = new Blob([payload], {
				type: format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8'
			});
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = `${jobId}.${format}`;
			document.body.appendChild(link);
			link.click();
			link.remove();
			URL.revokeObjectURL(url);
		} catch (err) {
			error = normalizeApiError(err, `Export ${format.toUpperCase()} failed`).message;
		} finally {
			exporting = null;
		}
	}

	onMount(loadJob);
</script>

<svelte:head>
	<title>Lab Job {jobId} - SignalForge</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Experiment {jobId}</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">Detailed hybrid detection execution record.</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={() => handleExport('json')}
				disabled={exporting !== null}
				class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm"
			>
				{exporting === 'json' ? 'Exporting JSON...' : 'Export JSON'}
			</button>
			<button
				onclick={() => handleExport('csv')}
				disabled={exporting !== null}
				class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm"
			>
				{exporting === 'csv' ? 'Exporting CSV...' : 'Export CSV'}
			</button>
		</div>
	</div>

	{#if loading}
		<PageStateLoading label="Loading experiment..." />
	{:else if error}
		<PageStateError message={error} onAction={loadJob} />
	{:else if !job}
		<PageStateError message="Experiment not found." onAction={loadJob} />
	{:else}
		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)] space-y-2 text-sm">
			<p><span class="font-semibold">Type:</span> {job.job_type}</p>
			<p><span class="font-semibold">Status:</span> {job.status}</p>
			<p><span class="font-semibold">Actor:</span> {job.actor}</p>
			<p><span class="font-semibold">Created (Harare):</span> {harareTime(job.created_at)}</p>
			{#if job.error}
				<p class="text-red-600"><span class="font-semibold">Error:</span> {job.error}</p>
			{/if}
		</div>

		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)]">
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-3">Input</h2>
			<pre class="overflow-x-auto rounded-lg bg-[var(--bg-secondary)] p-3 text-xs">{JSON.stringify(job.input ?? {}, null, 2)}</pre>
		</div>

		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)]">
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-3">Result</h2>
			<pre class="overflow-x-auto rounded-lg bg-[var(--bg-secondary)] p-3 text-xs">{JSON.stringify(job.result ?? {}, null, 2)}</pre>
		</div>
	{/if}
</div>
