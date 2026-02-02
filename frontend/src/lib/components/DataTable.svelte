<script lang="ts" generics="T">
	import { Icon } from 'svelte-hero-icons';

	interface Props {
		data: T[];
		columns: Array<{
			key: keyof T;
			label: string;
			format?: (value: any, row: T) => string;
		}>;
		onRowClick?: (row: T) => void;
		loading?: boolean;
		emptyMessage?: string;
	}

	let {
		data = [],
		columns,
		onRowClick,
		loading = false,
		emptyMessage = 'No data available'
	}: Props = $props();

	// Pagination state
	let currentPage = $state(1);
	let pageSize = $state(25);

	// Derived values
	let totalPages = $derived(Math.ceil(data.length / pageSize));
	let startIndex = $derived((currentPage - 1) * pageSize);
	let endIndex = $derived(startIndex + pageSize);
	let paginatedData = $derived(data.slice(startIndex, endIndex));

	function goToPage(page: number) {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	}

	function previousPage() {
		goToPage(currentPage - 1);
	}

	function nextPage() {
		goToPage(currentPage + 1);
	}

	// Generate page numbers to show
	let visiblePages = $derived.by(() => {
		const pages: number[] = [];
		const maxVisible = 5;

		if (totalPages <= maxVisible) {
			for (let i = 1; i <= totalPages; i++) {
				pages.push(i);
			}
		} else {
			if (currentPage <= 3) {
				for (let i = 1; i <= 4; i++) pages.push(i);
				pages.push(-1); // ellipsis
				pages.push(totalPages);
			} else if (currentPage >= totalPages - 2) {
				pages.push(1);
				pages.push(-1);
				for (let i = totalPages - 3; i <= totalPages; i++) pages.push(i);
			} else {
				pages.push(1);
				pages.push(-1);
				pages.push(currentPage - 1);
				pages.push(currentPage);
				pages.push(currentPage + 1);
				pages.push(-1);
				pages.push(totalPages);
			}
		}

		return pages;
	});
</script>

<div class="space-y-4">
	<!-- Table -->
	<div class="overflow-x-auto bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)]">
		<table class="w-full">
			<thead class="border-b border-[var(--border-color)]">
				<tr class="bg-[var(--bg-tertiary)]">
					{#each columns as column (column.key)}
						<th class="px-4 py-3 text-left text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
							{column.label}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody class="divide-y divide-[var(--border-color)]">
				{#if loading}
					<tr>
						<td colspan={columns.length} class="px-4 py-12 text-center">
							<div class="flex items-center justify-center space-x-2">
								<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]"></div>
								<span class="text-sm text-[var(--text-secondary)]">Loading...</span>
							</div>
						</td>
					</tr>
				{:else if paginatedData.length === 0}
					<tr>
						<td colspan={columns.length} class="px-4 py-12 text-center text-sm text-[var(--text-secondary)]">
							{emptyMessage}
						</td>
					</tr>
				{:else}
					{#each paginatedData as row, i (i)}
						<tr
							class="hover:bg-[var(--bg-tertiary)] transition-colors {onRowClick ? 'cursor-pointer' : ''}"
							onclick={() => onRowClick?.(row)}
						>
							{#each columns as column (column.key)}
								<td class="px-4 py-3 text-sm text-[var(--text-primary)]">
									{#if column.format}
										{column.format(row[column.key], row)}
									{:else}
										{String(row[column.key])}
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>

	<!-- Pagination -->
	{#if !loading && data.length > 0}
		<div class="flex flex-col sm:flex-row items-center justify-between gap-4">
			<div class="text-sm text-[var(--text-secondary)]">
				Showing {startIndex + 1}-{Math.min(endIndex, data.length)} of {data.length}
			</div>

			<div class="flex items-center space-x-2">
				<!-- Previous -->
				<button
					onclick={previousPage}
					disabled={currentPage === 1}
					class="px-3 py-2 rounded-lg border border-[var(--border-color)] text-sm font-medium
					       text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] disabled:opacity-50
					       disabled:cursor-not-allowed transition-colors"
				>
					<Icon src="chevron-left" class="w-4 h-4" />
				</button>

				<!-- Page numbers - hidden on mobile -->
				<div class="hidden sm:flex items-center space-x-2">
					{#each visiblePages as page, pageIndex (pageIndex)}
						{#if page === -1}
							<span class="px-3 py-2 text-sm text-[var(--text-secondary)]">...</span>
						{:else}
							<button
								onclick={() => goToPage(page)}
								class="px-4 py-2 rounded-lg text-sm font-medium transition-colors
								       {currentPage === page
									? 'bg-[var(--accent-primary)] text-white'
									: 'border border-[var(--border-color)] text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'}"
							>
								{page}
							</button>
						{/if}
					{/each}
				</div>

				<!-- Mobile page indicator -->
				<span class="sm:hidden text-sm text-[var(--text-secondary)]">
					Page {currentPage} of {totalPages}
				</span>

				<!-- Next -->
				<button
					onclick={nextPage}
					disabled={currentPage === totalPages}
					class="px-3 py-2 rounded-lg border border-[var(--border-color)] text-sm font-medium
					       text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] disabled:opacity-50
					       disabled:cursor-not-allowed transition-colors"
				>
					<Icon src="chevron-right" class="w-4 h-4" />
				</button>
			</div>

			<!-- Page size selector -->
			<div class="flex items-center space-x-2">
				<label for="page-size" class="text-sm text-[var(--text-secondary)] hidden sm:inline">Per page:</label>
				<select
					id="page-size"
					bind:value={pageSize}
					onchange={() => (currentPage = 1)}
					class="px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)]
					       text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2
					       focus:ring-[var(--accent-primary)] focus:border-transparent"
				>
					<option value={10}>10</option>
					<option value={25}>25</option>
					<option value={50}>50</option>
					<option value={100}>100</option>
				</select>
			</div>
		</div>
	{/if}
</div>

<style>
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.animate-spin {
		animation: spin 1s linear infinite;
	}
</style>
