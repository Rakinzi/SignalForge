<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		title?: string;
		message?: string;
		requiredRole?: string;
	}

	let {
		title = 'Access Limited',
		message = 'This section is available only to higher-privileged roles.',
		requiredRole = 'analyst or admin'
	}: Props = $props();
</script>

<div class="rounded-2xl border border-amber-300/70 bg-amber-50 p-8 text-left shadow-[var(--shadow-soft)] dark:border-amber-700/60 dark:bg-amber-900/20">
	<div class="flex items-start gap-3">
		<Icon src="shield-exclamation" class="mt-0.5 h-6 w-6 text-amber-700 dark:text-amber-400" />
		<div>
			<h2 class="text-lg font-semibold text-amber-900 dark:text-amber-200">{title}</h2>
			<p class="mt-1 text-sm text-amber-800 dark:text-amber-300">{message}</p>
			<p class="mt-2 text-xs font-medium uppercase tracking-wider text-amber-700/90 dark:text-amber-400/90">
				Required role: {requiredRole}
			</p>
		</div>
	</div>
</div>
