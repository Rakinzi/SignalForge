<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		label?: string;
	}

	let { label = 'Loading data...' }: Props = $props();
</script>

<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-12 text-center shadow-[var(--shadow-soft)]">
	<div class="mx-auto mb-3 flex w-fit items-center gap-2 text-[var(--text-secondary)]">
		<Icon src="arrow-path" class="h-5 w-5 animate-spin text-[var(--accent-primary)]" />
		<span class="text-sm">{label}</span>
	</div>
</div>
