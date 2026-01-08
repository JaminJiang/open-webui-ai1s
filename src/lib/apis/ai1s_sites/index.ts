import { WEBUI_API_BASE_URL } from '$lib/constants';

export const importSinglePost = async (
	token: string,
	id: string,
	postId: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/ai1s_sites/${id}/import/post`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			post_id: postId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const importAllPosts = async (
	token: string,
	id: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/ai1s_sites/${id}/import/all`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getImportProgress = async (
	token: string,
	id: string,
	task_id: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/ai1s_sites/${id}/import/progress/${task_id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getImportStatistics = async (
	token: string,
	id: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/ai1s_sites/${id}/import/statistics`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};