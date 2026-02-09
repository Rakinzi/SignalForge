<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	interface Props {
		label: string;
		value: string | number;
		unit?: string;
		icon?: string;
		trend?: { value: number; positive: boolean };
		color?: string;
	}

	let { label, value, unit = '', icon, trend, color }: Props = $props();
</script>

<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6
            hover:border-[var(--border-color-hover)] transition-colors">
	<div class="flex items-start justify-between">
		<div class="flex-1">
			<p class="text-sm font-medium text-[var(--text-secondary)] mb-2">{label}</p>
			<div class="flex items-baseline gap-2">
				<p class="text-3xl font-semibold text-[var(--text-primary)]" style={color ? `color: ${color}` : ''}>
					{typeof value === 'number' ? value.toLocaleString() : value}
				</p>
				{#if unit}
					<span class="text-sm text-[var(--text-tertiary)]">{unit}</span>
				{/if}
			</div>
			{#if trend}
				<div class="mt-2 flex items-center gap-1 text-sm">
					<span class={trend.positive ? 'text-green-600 dark:text-emerald-400' : 'text-red-600'}>
						{trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}%
					</span>
					<span class="text-[var(--text-tertiary)]">vs last hour</span>
				</div>
			{/if}
		</div>
		{#if icon}
			<div class="w-12 h-12 rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
				<Icon src={icon} class="w-6 h-6 text-[var(--text-secondary)]" />
			</div>
		{/if}
	</div>
</div>
