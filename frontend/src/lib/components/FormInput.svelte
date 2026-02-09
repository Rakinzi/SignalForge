<script lang="ts">
	interface Props {
		label: string;
		value: string;
		placeholder?: string;
		type?: 'text' | 'number' | 'email';
		id?: string;
	}

	let { label, value = $bindable(''), placeholder = '', type = 'text', id }: Props = $props();
	let inputId = $derived(id ?? `input-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`);
</script>

<div>
	<label for={inputId} class="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
		{label}
	</label>
	<input
		id={inputId}
		{type}
		bind:value
		{placeholder}
		class="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg
		       text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]
		       focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent
		       transition-all"
	/>
</div>
