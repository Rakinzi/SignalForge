<script lang="ts">
	import { onMount } from 'svelte';
	import { getReportsOverview, normalizeApiError } from '$lib/api/client';
	import type { EvaluationMetrics } from '$lib/types';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateEmpty from '$lib/components/PageStateEmpty.svelte';
	import PageStateForbidden from '$lib/components/PageStateForbidden.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';

	let metrics = $state<EvaluationMetrics | null>(null);
	let byRule = $state<Array<{ rules: string; count: number }>>([]);
	let latestEvaluation = $state<Record<string, unknown> | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let isForbidden = $state(false);

	async function loadReports() {
		loading = true;
		error = null;
		isForbidden = false;
		try {
			const report = await getReportsOverview();
			metrics = report.metrics;
			byRule = report.by_rule;
			latestEvaluation = report.latest_evaluation;
		} catch (err) {
			metrics = null;
			byRule = [];
			latestEvaluation = null;
			const normalized = normalizeApiError(err, 'Failed to load reports');
			if (normalized.kind === 'forbidden') {
				isForbidden = true;
			} else {
				error = normalized.message;
			}
		} finally {
			loading = false;
		}
	}

	function ratio(value: number): string {
		return `${(value * 100).toFixed(1)}%`;
	}

	function flowSampleSize(): number {
		if (!metrics) return 0;
		return (
			metrics.true_positives +
			metrics.false_positives +
			metrics.true_negatives +
			metrics.false_negatives
		);
	}

	onMount(loadReports);
</script>

<svelte:head>
	<title>Reports</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Detection Reports</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">Model quality and confusion metrics.</p>
		</div>
		<button
			onclick={loadReports}
			disabled={loading}
			class="rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<PageStateLoading label="Loading report metrics..." />
	{:else if isForbidden}
		<PageStateForbidden
			title="Report data requires elevated access"
			message="Viewer accounts can monitor operational dashboards, while full reports are restricted."
			requiredRole="analyst or admin"
		/>
	{:else if error}
		<PageStateError message={error} onAction={loadReports} />
	{:else if !metrics}
		<PageStateEmpty
			title="No report metrics yet"
			message="Run a labeled evaluation cycle to generate reports."
			icon="document-chart-bar"
		/>
	{:else}
		{#if flowSampleSize() < 30}
			<div class="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-800">
				Report quality note: current metrics are based on {flowSampleSize()} labeled flow(s). Run more
				labeled analyses in `Lab` for stronger confidence.
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
				<p class="text-sm text-[var(--text-secondary)]">Precision</p>
				<p class="mt-2 text-3xl font-semibold text-[var(--text-primary)]">{ratio(metrics.precision)}</p>
			</div>
			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
				<p class="text-sm text-[var(--text-secondary)]">Recall</p>
				<p class="mt-2 text-3xl font-semibold text-[var(--text-primary)]">{ratio(metrics.recall)}</p>
			</div>
			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
				<p class="text-sm text-[var(--text-secondary)]">F1 Score</p>
				<p class="mt-2 text-3xl font-semibold text-[var(--text-primary)]">{ratio(metrics.f1_score)}</p>
			</div>
			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
				<p class="text-sm text-[var(--text-secondary)]">Accuracy</p>
				<p class="mt-2 text-3xl font-semibold text-[var(--text-primary)]">{ratio(metrics.accuracy)}</p>
			</div>
		</div>

		<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
			<h2 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Classification Counts</h2>
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				<div class="rounded-xl border border-emerald-400/40 bg-emerald-50/60 p-4 dark:bg-emerald-900/10">
					<p class="text-sm text-[var(--text-secondary)]">True Positives</p>
					<p class="mt-2 text-2xl font-bold text-emerald-700 dark:text-emerald-300">
						{metrics.true_positives.toLocaleString()}
					</p>
				</div>
				<div class="rounded-xl border border-orange-400/40 bg-orange-50/60 p-4 dark:bg-orange-900/10">
					<p class="text-sm text-[var(--text-secondary)]">False Positives</p>
					<p class="mt-2 text-2xl font-bold text-orange-700 dark:text-orange-300">
						{metrics.false_positives.toLocaleString()}
					</p>
				</div>
				<div class="rounded-xl border border-sky-400/40 bg-sky-50/60 p-4 dark:bg-sky-900/10">
					<p class="text-sm text-[var(--text-secondary)]">True Negatives</p>
					<p class="mt-2 text-2xl font-bold text-sky-700 dark:text-sky-300">
						{metrics.true_negatives.toLocaleString()}
					</p>
				</div>
				<div class="rounded-xl border border-rose-400/40 bg-rose-50/60 p-4 dark:bg-rose-900/10">
					<p class="text-sm text-[var(--text-secondary)]">False Negatives</p>
					<p class="mt-2 text-2xl font-bold text-rose-700 dark:text-rose-300">
						{metrics.false_negatives.toLocaleString()}
					</p>
				</div>
			</div>
		</div>

		<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
			<h2 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Rule Trigger Distribution</h2>
			{#if byRule.length === 0}
				<p class="text-sm text-[var(--text-secondary)]">No rule aggregation is available yet.</p>
			{:else}
				<div class="space-y-2">
					{#each byRule.slice(0, 6) as row}
						<div class="flex items-center justify-between rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm">
							<span class="truncate text-[var(--text-secondary)]">
								{row.rules && row.rules !== '[]' ? row.rules : 'No deterministic rules'}
							</span>
							<span class="font-semibold text-[var(--text-primary)]">{row.count}</span>
						</div>
					{/each}
				</div>
			{/if}
			{#if latestEvaluation}
				<p class="mt-4 text-xs text-[var(--text-tertiary)]">
					Latest backend snapshot is available and merged with labeled run metrics.
				</p>
			{/if}
		</div>
	{/if}
</div>
