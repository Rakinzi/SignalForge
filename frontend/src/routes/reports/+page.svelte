<script lang="ts">
	import { onMount } from 'svelte';
	import { getReports } from '$lib/api/client';
	import type { EvaluationMetrics } from '$lib/types';
	import { Icon } from 'svelte-hero-icons';

	let metrics = $state<EvaluationMetrics | null>(null);
	let loading = $state(true);

	async function loadReports() {
		loading = true;
		metrics = await getReports();
		loading = false;
	}

	function getScoreColor(score: number): string {
		if (score >= 0.9) return 'var(--color-success)';
		if (score >= 0.7) return 'var(--color-medium)';
		return 'var(--color-high)';
	}

	function getScoreBg(score: number): string {
		if (score >= 0.9) return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200';
		if (score >= 0.7)
			return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200';
		return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
	}

	onMount(loadReports);

	let confusionMatrix = $derived(
		metrics
			? [
					{ label: 'True Positives', value: metrics.true_positives, color: 'var(--color-success)' },
					{ label: 'False Positives', value: metrics.false_positives, color: 'var(--color-high)' },
					{ label: 'True Negatives', value: metrics.true_negatives, color: 'var(--color-info)' },
					{
						label: 'False Negatives',
						value: metrics.false_negatives,
						color: 'var(--color-critical)'
					}
				]
			: []
	);

	let performanceMetrics = $derived(
		metrics
			? [
					{ label: 'Precision', value: metrics.precision },
					{ label: 'Recall', value: metrics.recall },
					{ label: 'F1 Score', value: metrics.f1_score },
					{ label: 'Accuracy', value: metrics.accuracy }
				]
			: []
	);
</script>

<svelte:head>
	<title>Reports</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Detection Reports</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">Performance metrics and evaluation</p>
	</div>
	<button
		onclick={loadReports}
		disabled={loading}
		class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
		       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
	>
		<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
		Refresh
	</button>
</div>

{#if loading && !metrics}
	<div
		class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-12 text-center"
	>
		<div class="flex items-center justify-center gap-2">
			<div
				class="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]"
			></div>
			<span class="text-sm text-[var(--text-secondary)]">Loading reports...</span>
		</div>
	</div>
{:else if metrics}
	<!-- Performance Metrics -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
		{#each performanceMetrics as metric (metric.label)}
			<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
				<div class="flex items-center justify-between mb-2">
					<p class="text-sm text-[var(--text-secondary)]">{metric.label}</p>
					<span class="px-2 py-1 text-xs font-medium rounded {getScoreBg(metric.value)}">
						{(metric.value * 100).toFixed(1)}%
					</span>
				</div>
				<p class="text-2xl font-semibold text-[var(--text-primary)]">
					{metric.value.toFixed(4)}
				</p>
				<div class="mt-2 w-full h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
					<div
						class="h-full rounded-full transition-all duration-500"
						style="width: {metric.value * 100}%; background-color: {getScoreColor(
							metric.value
						)}"
					></div>
				</div>
			</div>
		{/each}
	</div>

	<!-- Confusion Matrix Cards -->
	<div class="mb-6">
		<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Confusion Matrix</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			{#each confusionMatrix as item (item.label)}
				<div
					class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6"
					style="border-left: 4px solid {item.color}"
				>
					<p class="text-sm text-[var(--text-secondary)] mb-2">{item.label}</p>
					<p class="text-3xl font-semibold text-[var(--text-primary)]">
						{item.value.toLocaleString()}
					</p>
				</div>
			{/each}
		</div>
	</div>

	<!-- Classification Matrix Table -->
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6">
		<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Classification Matrix</h2>
		<div class="overflow-x-auto">
			<table class="w-full border-collapse">
				<thead>
					<tr>
						<th class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)]"></th>
						<th
							colspan="2"
							class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)] text-center text-sm font-medium text-[var(--text-primary)]"
						>
							Predicted
						</th>
					</tr>
					<tr>
						<th class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)]"></th>
						<th
							class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)] text-center text-sm font-medium text-[var(--text-primary)]"
						>
							Positive
						</th>
						<th
							class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)] text-center text-sm font-medium text-[var(--text-primary)]"
						>
							Negative
						</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td
							class="border border-[var(--border-color)] p-4 bg-[var(--bg-tertiary)] text-center text-sm font-medium text-[var(--text-primary)]"
							rowspan="2"
						>
							<div class="transform -rotate-90 whitespace-nowrap">Actual</div>
						</td>
					</tr>
					<tr>
						<td
							class="border border-[var(--border-color)] p-8 text-center bg-green-50 dark:bg-green-900/10"
						>
							<div class="text-sm text-[var(--text-secondary)] mb-2">True Positive</div>
							<div class="text-3xl font-semibold" style="color: var(--color-success)">
								{metrics.true_positives}
							</div>
						</td>
						<td
							class="border border-[var(--border-color)] p-8 text-center bg-red-50 dark:bg-red-900/10"
						>
							<div class="text-sm text-[var(--text-secondary)] mb-2">False Negative</div>
							<div class="text-3xl font-semibold" style="color: var(--color-critical)">
								{metrics.false_negatives}
							</div>
						</td>
					</tr>
					<tr>
						<td class="border-0"></td>
						<td
							class="border border-[var(--border-color)] p-8 text-center bg-orange-50 dark:bg-orange-900/10"
						>
							<div class="text-sm text-[var(--text-secondary)] mb-2">False Positive</div>
							<div class="text-3xl font-semibold" style="color: var(--color-high)">
								{metrics.false_positives}
							</div>
						</td>
						<td
							class="border border-[var(--border-color)] p-8 text-center bg-blue-50 dark:bg-blue-900/10"
						>
							<div class="text-sm text-[var(--text-secondary)] mb-2">True Negative</div>
							<div class="text-3xl font-semibold" style="color: var(--color-info)">
								{metrics.true_negatives}
							</div>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
{/if}
