<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let importedPosts: { post_id: string }[] = [];
	export let isImporting = false;
	export let fetchStatistics: () => Promise<any>;

	let importPostId = '';
	let statistics = null;

	const dispatch = createEventDispatcher();

	onMount(async () => {
		// if (show && fetchStatistics) {
		if (true) {
			await loadStatistics();
		}
	});

	const loadStatistics = async () => {
		try {
			const data = await fetchStatistics();
			if (data) {
				statistics = data;
			}
		} catch (error) {
			console.error('Error fetching statistics:', error);
		}
	};

	const handleImportSingle = () => {
		if (importPostId.trim()) {
			dispatch('importSingle', { postId: importPostId.trim() });
		}
	};

	const handleImportAll = () => {
		dispatch('importAll');
	};

	const handleDelete = (postId: string) => {
		dispatch('delete', { postId });
	};
</script>

<Modal bind:show={show} size="lg">
	<div class="absolute top-0 right-0 p-5">
		<button
			class="self-center dark:text-white"
			type="button"
			on:click={() => {
				show = false;
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>
	
	<div class="flex flex-col gap-4 p-5">
		<div class="text-2xl font-bold mb-4">Import AI Sites</div>
		
		<div class="text-sm text-gray-600 dark:text-gray-400 mb-4">
			Import AI sites from WordPress database into knowledge base.
		</div>

		{#if statistics}
			<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg mb-4">
				<div class="text-sm font-medium mb-2">Import Statistics</div>
				<div class="grid grid-cols-2 gap-2">
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">Total Posts</div>
						<div class="text-lg font-bold">{statistics.total_post_num}</div>
					</div>
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">Imported Files</div>
						<div class="text-lg font-bold">{statistics.knowledge_files_num}</div>
					</div>
				</div>
			</div>
		{/if}
		
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between gap-2">
				<div class="text-sm font-medium">Import single post</div>
				<input 
					type="text"
					placeholder="Enter post ID" 
					bind:value={importPostId} 
					class="w-32 px-3 py-2 border rounded-md"
					disabled={isImporting}
				/>
				<button 
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
					on:click={handleImportSingle}
					disabled={!importPostId || isImporting}
				>
					{#if isImporting}
						<Spinner className="size-4" />
					{:else}
						Import
					{/if}
				</button>
			</div>
			
			<div class="flex items-center justify-between gap-2">
				<div class="text-sm font-medium">Import all posts</div>
				<button 
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
					on:click={handleImportAll}
					disabled={isImporting}
				>
					{#if isImporting}
						<Spinner className="size-4" />
					{:else}
						Import All
					{/if}
				</button>
			</div>
		</div>
	</div>
</Modal>