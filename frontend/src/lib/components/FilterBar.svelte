<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		onApply: () => void;
		onClear: () => void;
		children: any;
	}

	let { onApply, onClear, children }: Props = $props();
</script>

<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
	<div class="flex items-end gap-4">
		<div class="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
			{@render children()}
		</div>
		<div class="flex gap-2">
			<button
				onclick={onApply}
				class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
				       transition-opacity flex items-center gap-2 text-sm font-medium whitespace-nowrap"
			>
				<Icon src="magnifying-glass" class="w-4 h-4" />
				Apply
			</button>
			<button
				onclick={onClear}
				class="px-4 py-2 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg
				       hover:bg-[var(--border-color)] transition-colors text-sm font-medium whitespace-nowrap"
			>
				Clear
			</button>
		</div>
	</div>
</div>
