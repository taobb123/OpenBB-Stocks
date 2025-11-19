/**
 * API 配置
 * 可以通过环境变量或配置文件修改
 */

// 从环境变量获取 API URL，如果没有则使用默认值
const getApiBaseUrl = (): string => {
	// 优先使用环境变量
	if (import.meta.env.VITE_API_BASE_URL) {
		return import.meta.env.VITE_API_BASE_URL;
	}
	
	// 其次检查 localStorage（允许用户动态配置）
	const savedUrl = localStorage.getItem('api_base_url');
	if (savedUrl) {
		return savedUrl;
	}
	
	// 默认值（8003 端口）
	return 'http://localhost:8003/api';
};

export const API_BASE_URL = getApiBaseUrl();

// 导出函数以便动态更新
export const setApiBaseUrl = (url: string): void => {
	localStorage.setItem('api_base_url', url);
	// 注意：需要刷新页面才能生效，或者使用状态管理
};

export const getApiBaseUrlWithoutPath = (): string => {
	const url = getApiBaseUrl();
	// 移除 /api 后缀，返回基础 URL
	return url.replace(/\/api$/, '');
};

