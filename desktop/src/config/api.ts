/**
 * API 配置
 * 可以通过环境变量或配置文件修改
 */

// 从环境变量获取 API URL，如果没有则使用默认值
const getApiBaseUrlInternal = (): string => {
	// 优先使用环境变量
	if (import.meta.env.VITE_API_BASE_URL) {
		const envUrl = import.meta.env.VITE_API_BASE_URL;
		// 确保 URL 格式正确
		if (envUrl && !envUrl.startsWith('http://') && !envUrl.startsWith('https://')) {
			console.warn(`VITE_API_BASE_URL 格式不正确，应该是完整的 URL: ${envUrl}`);
		}
		return envUrl;
	}
	
	// 其次检查 localStorage（允许用户动态配置）
	const savedUrl = localStorage.getItem('api_base_url');
	if (savedUrl) {
		// 验证保存的 URL 格式
		if (savedUrl && !savedUrl.startsWith('http://') && !savedUrl.startsWith('https://')) {
			console.warn(`localStorage 中的 api_base_url 格式不正确: ${savedUrl}`);
			// 如果格式不正确，使用默认值
			localStorage.removeItem('api_base_url');
		} else {
			return savedUrl;
		}
	}
	
	// 默认值（8003 端口）
	const defaultUrl = 'http://localhost:8003/api';
	console.log(`使用默认 API URL: ${defaultUrl}`);
	return defaultUrl;
};

// 导出函数以便动态获取（每次调用时重新计算）
export const getApiBaseUrl = (): string => {
	return getApiBaseUrlInternal();
};

// 静态导出（在模块加载时计算一次）
export const API_BASE_URL = (() => {
	const url = getApiBaseUrlInternal();
	console.log(`API_BASE_URL 设置为: ${url}`);
	return url;
})();

// 导出函数以便动态更新
export const setApiBaseUrl = (url: string): void => {
	localStorage.setItem('api_base_url', url);
	// 注意：需要刷新页面才能生效，或者使用状态管理
};

export const getApiBaseUrlWithoutPath = (): string => {
	const url = getApiBaseUrl();
	// 移除 /api 后缀，返回基础 URL
	const baseUrl = url.replace(/\/api\/?$/, '');
	// 确保返回的 URL 格式正确
	if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
		console.warn(`getApiBaseUrlWithoutPath 返回的 URL 格式不正确: ${baseUrl}`);
	}
	return baseUrl;
};

