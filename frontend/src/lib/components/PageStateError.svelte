<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		title?: string;
		message: string;
		actionLabel?: string;
		onAction?: (() => void) | undefined;
	}

	let {
		title = 'Unable to load this section',
		message,
		actionLabel = 'Try again',
		onAction
	}: Props = $props();
</script>

<div class="rounded-2xl border border-rose-300/70 bg-rose-50 p-8 shadow-[var(--shadow-soft)] dark:border-rose-700/60 dark:bg-rose-900/20">
	<div class="flex items-start gap-3">
		<Icon src="exclamation-triangle" class="mt-0.5 h-6 w-6 text-rose-700 dark:text-rose-400" />
		<div class="flex-1">
			<h2 class="text-lg font-semibold text-rose-900 dark:text-rose-200">{title}</h2>
			<p class="mt-1 text-sm text-rose-800 dark:text-rose-300">{message}</p>
			{#if onAction}
				<button
					type="button"
					onclick={onAction}
					class="mt-4 inline-flex items-center gap-2 rounded-lg border border-rose-400/70 bg-white px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100 dark:border-rose-600 dark:bg-rose-950/30 dark:text-rose-300 dark:hover:bg-rose-900/40"
				>
					<Icon src="arrow-path" class="h-4 w-4" />
					{actionLabel}
				</button>
			{/if}
		</div>
	</div>
</div>
