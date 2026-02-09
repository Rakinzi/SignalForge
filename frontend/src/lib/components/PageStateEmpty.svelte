<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		title: string;
		message: string;
		icon?: string;
	}

	let { title, message, icon = 'inbox' }: Props = $props();
</script>

<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-12 text-center shadow-[var(--shadow-soft)]">
	<Icon src={icon} class="mx-auto mb-3 h-10 w-10 text-[var(--text-tertiary)]" />
	<h2 class="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
	<p class="mt-2 text-sm text-[var(--text-secondary)]">{message}</p>
</div>
