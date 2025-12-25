<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';

	import ModelModal from './LeaderboardModal.svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	// 移除嵌入模型相关常量
	// const EMBEDDING_MODEL = 'TaylorAI/bge-micro-v2';

	// 移除嵌入相关变量
	// let tokenizer = null;
	// let model = null;

	export let feedbacks = [];

	let rankedModels = [];

	let query = '';
	// 移除嵌入相关变量
	// let tagEmbeddings = new Map();
	let loadingLeaderboard = true;
	let debounceTimer;

	let orderBy: string = 'rating'; // default sort column
	let direction: 'asc' | 'desc' = 'desc'; // default sort order

	type Feedback = {
		id: string;
		data: {
			rating: number;
			model_id: string;
			sibling_model_ids: string[] | null;
			reason: string;
			comment: string;
			tags: string[];
		};
		user: {
			name: string;
			profile_image_url: string;
		};
		updated_at: number;
	};

	type ModelStats = {
		rating: number;
		won: number;
		lost: number;
	};

	function setSortKey(key) {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = key === 'name' ? 'asc' : 'desc';
		}
	}

	//////////////////////
	//
	// Aggregate Level Modal
	//
	//////////////////////

	let showLeaderboardModal = false;
	let selectedModel = null;

	const openLeaderboardModelModal = (model) => {
		showLeaderboardModal = true;
		selectedModel = model;
	};

	const closeLeaderboardModal = () => {
		showLeaderboardModal = false;
		selectedModel = null;
	};

	//////////////////////
	//
	// Rank models by Elo rating
	//
	//////////////////////

	// 简化rankHandler，移除similarities参数（始终传空Map）
	const rankHandler = async () => {
		const modelStats = calculateModelStats(feedbacks);

		rankedModels = $models
			.filter((m) => m?.owned_by !== 'arena' && (m?.info?.meta?.hidden ?? false) !== true)
			.map((model) => {
				const stats = modelStats.get(model.id);
				return {
					...model,
					rating: stats ? Math.round(stats.rating) : '-',
					stats: {
						count: stats ? stats.won + stats.lost : 0,
						won: stats ? stats.won.toString() : '-',
						lost: stats ? stats.lost.toString() : '-'
					}
				};
			})
			.sort((a, b) => {
				if (a.rating === '-' && b.rating !== '-') return 1;
				if (b.rating === '-' && a.rating !== '-') return -1;
				if (a.rating !== '-' && b.rating !== '-') return b.rating - a.rating;
				return (a?.name ?? a?.id ?? '').localeCompare(b?.name ?? b?.id ?? '');
			});

		loadingLeaderboard = false;
	};

	// 简化calculateModelStats，移除similarities参数和相关逻辑
	function calculateModelStats(
		feedbacks: Feedback[]
	): Map<string, ModelStats> {
		const stats = new Map<string, ModelStats>();
		const K = 32;

		function getOrDefaultStats(modelId: string): ModelStats {
			return stats.get(modelId) || { rating: 1000, won: 0, lost: 0 };
		}

		function updateStats(modelId: string, ratingChange: number, outcome: number) {
			const currentStats = getOrDefaultStats(modelId);
			currentStats.rating += ratingChange;
			if (outcome === 1) currentStats.won++;
			else if (outcome === 0) currentStats.lost++;
			stats.set(modelId, currentStats);
		}

		// 简化calculateEloChange，移除similarity参数（始终乘1）
		function calculateEloChange(
			ratingA: number,
			ratingB: number,
			outcome: number
		): number {
			const expectedScore = 1 / (1 + Math.pow(10, (ratingB - ratingA) / 400));
			return K * (outcome - expectedScore);
		}

		feedbacks.forEach((feedback) => {
			if (!feedback?.data?.model_id || !feedback?.data?.rating) return;

			const modelA = feedback.data.model_id;
			const statsA = getOrDefaultStats(modelA);
			let outcome: number;

			switch (feedback.data.rating.toString()) {
				case '1':
					outcome = 1;
					break;
				case '-1':
					outcome = 0;
					break;
				default:
					return; // Skip invalid ratings
			}

			// 移除similarity相关逻辑，始终使用1
			const opponents = feedback.data.sibling_model_ids || [];

			opponents.forEach((modelB) => {
				const statsB = getOrDefaultStats(modelB);
				const changeA = calculateEloChange(statsA.rating, statsB.rating, outcome);
				const changeB = calculateEloChange(statsB.rating, statsA.rating, 1 - outcome);

				updateStats(modelA, changeA, outcome);
				updateStats(modelB, changeB, 1 - outcome);
			});
		});

		return stats;
	}

	// 移除所有嵌入相关函数
	// const cosineSimilarity = (vecA, vecB) => { ... }
	// const calculateMaxSimilarity = (queryEmbedding, tagEmbeddings: Map<string, number[]>) => { ... }
	const loadEmbeddingModel = async () => { return; }
	// const getEmbeddings = async (text: string) => { ... }
	// const getTagEmbeddings = async (tags: string[]) => { ... }

	// 简化debouncedQueryHandler，仅做基础的rankHandler调用
	const debouncedQueryHandler = async () => {
		loadingLeaderboard = true;
		clearTimeout(debounceTimer);

		debounceTimer = setTimeout(async () => {
			// 无论query是否为空，都直接调用rankHandler（不再计算相似度）
			rankHandler();
		}, 1500); // 保留防抖逻辑，可根据需要调整时长
	};

	$: query, debouncedQueryHandler();

	onMount(async () => {
		rankHandler();
	});

	$: sortedModels = [...rankedModels].sort((a, b) => {
		let aVal, bVal;
		if (orderBy === 'name') {
			aVal = a.name;
			bVal = b.name;
			return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
		} else if (orderBy === 'rating') {
			aVal = a.rating === '-' ? -Infinity : a.rating;
			bVal = b.rating === '-' ? -Infinity : bVal;
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'won') {
			aVal = a.stats.won === '-' ? -Infinity : Number(a.stats.won);
			bVal = b.stats.won === '-' ? -Infinity : Number(b.stats.won);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		} else if (orderBy === 'lost') {
			aVal = a.stats.lost === '-' ? -Infinity : Number(a.stats.lost);
			bVal = b.stats.lost === '-' ? -Infinity : Number(b.stats.lost);
			return direction === 'asc' ? aVal - bVal : bVal - aVal;
		}
		return 0;
	});
</script>

<ModelModal
	bind:show={showLeaderboardModal}
	model={selectedModel}
	{feedbacks}
	onClose={closeLeaderboardModal}
/>

<div
	class="pt-0.5 pb-1 gap-1 flex flex-col md:flex-row justify-between sticky top-0 z-10 bg-white dark:bg-gray-900"
>
	<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
		<div>
			{$i18n.t('Leaderboard')}
		</div>

		<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
			{rankedModels.length}
		</div>
	</div>

	<div class=" flex space-x-2">
		<Tooltip content={$i18n.t('Re-rank models by topic similarity')}>
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search')}
					on:focus={() => { loadEmbeddingModel(); }}
				/>
			</div>
		</Tooltip>
	</div>
</div>

<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm">
	{#if loadingLeaderboard}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner className="size-5" />
			</div>
		</div>
	{/if}
	{#if (rankedModels ?? []).length === 0}
		<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-1">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<table
			class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full {loadingLeaderboard
				? 'opacity-20'
				: ''}"
		>
			<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
				<tr class=" border-b-[1.5px] border-gray-50 dark:border-gray-850/30">
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none w-3"
						on:click={() => setSortKey('rating')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('RK')}
							{#if orderBy === 'rating'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 cursor-pointer select-none"
						on:click={() => setSortKey('name')}
					>
						<div class="flex gap-1.5 items-center">
							{$i18n.t('Model')}
							{#if orderBy === 'name'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 text-right cursor-pointer select-none w-fit"
						on:click={() => setSortKey('rating')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Rating')}
							{#if orderBy === 'rating'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 text-right cursor-pointer select-none w-5"
						on:click={() => setSortKey('won')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Won')}
							{#if orderBy === 'won'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
					<th
						scope="col"
						class="px-2.5 py-2 text-right cursor-pointer select-none w-5"
						on:click={() => setSortKey('lost')}
					>
						<div class="flex gap-1.5 items-center justify-end">
							{$i18n.t('Lost')}
							{#if orderBy === 'lost'}
								<span class="font-normal">
									{#if direction === 'asc'}
										<ChevronUp className="size-2" />
									{:else}
										<ChevronDown className="size-2" />
									{/if}
								</span>
							{:else}
								<span class="invisible">
									<ChevronUp className="size-2" />
								</span>
							{/if}
						</div>
					</th>
				</tr>
			</thead>
			<tbody class="">
				{#each sortedModels as model, modelIdx (model.id)}
					<tr
						class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs group cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850/50 transition"
						on:click={() => openLeaderboardModelModal(model)}
					>
						<td class="px-3 py-1.5 text-left font-medium text-gray-900 dark:text-white w-fit">
							<div class=" line-clamp-1">
								{model?.rating !== '-' ? modelIdx + 1 : '-'}
							</div>
						</td>
						<td class="px-3 py-1.5 flex flex-col justify-center">
							<div class="flex items-center gap-2">
								<div class="shrink-0">
									<img
										src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}`}
										alt={model.name}
										class="size-5 rounded-full object-cover shrink-0"
									/>
								</div>

								<div class="font-medium text-gray-800 dark:text-gray-200 pr-4">
									{model.name}
								</div>
							</div>
						</td>
						<td class="px-3 py-1.5 text-right font-medium text-gray-900 dark:text-white w-max">
							{model.rating}
						</td>

						<td class=" px-3 py-1.5 text-right font-medium text-green-500">
							<div class=" w-10">
								{#if model.stats.won === '-'}
									-
								{:else}
									<span class="hidden group-hover:inline"
										>{((model.stats.won / model.stats.count) * 100).toFixed(1)}%</span
									>
									<span class=" group-hover:hidden">{model.stats.won}</span>
								{/if}
							</div>
						</td>

						<td class="px-3 py-1.5 text-right font-medium text-red-500">
							<div class=" w-10">
								{#if model.stats.lost === '-'}
									-
								{:else}
									<span class="hidden group-hover:inline"
										>{((model.stats.lost / model.stats.count) * 100).toFixed(1)}%</span
									>
									<span class=" group-hover:hidden">{model.stats.lost}</span>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<div class=" text-gray-500 text-xs mt-1.5 w-full flex justify-end">
	<div class=" text-right">
		<div class="line-clamp-1">
			ⓘ {$i18n.t(
				'The evaluation leaderboard is based on the Elo rating system and is updated in real-time.'
			)}
		</div>
		{$i18n.t(
			'The leaderboard is currently in beta, and we may adjust the rating calculations as we refine the algorithm.'
		)}
	</div>
</div>