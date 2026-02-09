<script lang="ts">
	import { ExclamationCircle } from '@steeze-ui/heroicons';
	import * as HeroIcons from '@steeze-ui/heroicons';

	type IconShape = {
		default?: { a?: Record<string, string>; path?: Array<Record<string, string>> };
		solid?: { a?: Record<string, string>; path?: Array<Record<string, string>> };
		mini?: { a?: Record<string, string>; path?: Array<Record<string, string>> };
		micro?: { a?: Record<string, string>; path?: Array<Record<string, string>> };
	};

	function toPascalCase(name: string): string {
		return name
			.split('-')
			.filter(Boolean)
			.map((part) => {
				const normalized = part.replace(/x/g, 'X');
				return normalized.charAt(0).toUpperCase() + normalized.slice(1);
			})
			.join('');
	}

	type IconInput = IconShape | string | undefined;

	let {
		src,
		size = '100%',
		solid = false,
		mini = false,
		micro = false,
		...rest
	} = $props<{
		src?: IconInput;
		size?: string;
		solid?: boolean;
		mini?: boolean;
		micro?: boolean;
		[key: string]: unknown;
	}>();

	let resolvedIcon = $derived.by(() => {
		if (typeof src !== 'string') {
			return (src as IconShape | undefined) ?? (ExclamationCircle as IconShape);
		}

		const key = toPascalCase(src);
		return (
			((HeroIcons as unknown as Record<string, IconShape>)[key] as IconShape | undefined) ??
			(ExclamationCircle as IconShape)
		);
	});

	let variant = $derived(solid ? 'solid' : mini ? 'mini' : micro ? 'micro' : 'default');
	let iconData = $derived(
		(resolvedIcon?.[variant as keyof IconShape] as
			| { a?: Record<string, string>; path?: Array<Record<string, string>> }
			| undefined) ??
			resolvedIcon?.default
	);

	function normalizedSize(input: string): string {
		if (!input || input === '100%') return '100%';
		const suffix = input.slice(-1);
		if (suffix !== 'x' && suffix !== 'm' && suffix !== '%') {
			const parsed = Number.parseInt(input, 10);
			if (!Number.isNaN(parsed)) return `${parsed}px`;
		}
		return input;
	}
</script>

<svg
	{...(iconData?.a ?? {})}
	xmlns="http://www.w3.org/2000/svg"
	width={normalizedSize(size)}
	height={normalizedSize(size)}
	aria-hidden="true"
	{...rest}
>
	{#each iconData?.path ?? [] as pathProps}
		<path {...pathProps} />
	{/each}
</svg>
