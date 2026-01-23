<script lang="ts">
	interface Props {
		label: string;
		value: string;
		options: Array<{ value: string; label: string }>;
	}

	let { label, value = $bindable(''), options }: Props = $props();
</script>

<div>
	<label class="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
		{label}
	</label>
	<select
		bind:value
		class="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg
		       text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2
		       focus:ring-[var(--accent-primary)] focus:border-transparent transition-all"
	>
		{#each options as option}
			<option value={option.value}>{option.label}</option>
		{/each}
	</select>
</div>
