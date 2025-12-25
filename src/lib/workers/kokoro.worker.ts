// workers/kokoro.worker.ts
// import { KokoroTTS } from 'kokoro-js';

let tts;
let isInitialized = false; // Flag to track initialization status
const DEFAULT_MODEL_ID = 'onnx-community/Kokoro-82M-v1.0-ONNX'; // Default model

self.onmessage = async (event) => {
	const { type, payload } = event.data;

	if (type === 'init') {
		let { model_id, dtype } = payload;
		model_id = model_id || DEFAULT_MODEL_ID; // Use default model if none provided

		self.postMessage({ status: 'init:start' });

		try {
			// 初始化KokoroTTS，移除transformers相关的环境依赖
			// tts = await KokoroTTS.from_pretrained(model_id, {
			// 	dtype,
			// 	// 调整设备检测逻辑（如果kokoro-js自身支持WebGPU/wasm配置）
			// 	// 注：如果kokoro-js不需要device参数，可移除该配置
			// 	device: !!navigator?.gpu ? 'webgpu' : 'wasm'
			// });
			// isInitialized = true; // Mark as initialized after successful loading
			// self.postMessage({ status: 'init:complete' });
			if (true) {
				throw new Error('KokoroTTS not supported in this environment');
			}
		} catch (error) {
			isInitialized = false; // Ensure it's marked as false on failure
			self.postMessage({ status: 'init:error', error: error.message });
		}
	}

	if (type === 'generate') {
		if (!isInitialized || !tts) {
			// Ensure model is initialized
			self.postMessage({ status: 'generate:error', error: 'TTS model not initialized' });
			return;
		}

		const { text, voice } = payload;
		self.postMessage({ status: 'generate:start' });

		try {
			const rawAudio = await tts.generate(text, { voice });
			const blob = await rawAudio.toBlob();
			const blobUrl = URL.createObjectURL(blob);
			self.postMessage({ status: 'generate:complete', audioUrl: blobUrl });
		} catch (error) {
			self.postMessage({ status: 'generate:error', error: error.message });
		}
	}

	if (type === 'status') {
		// Respond with the current initialization status
		self.postMessage({ status: 'status:check', initialized: isInitialized });
	}
};