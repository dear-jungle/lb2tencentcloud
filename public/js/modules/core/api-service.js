/**
 * API 调用封装（单例模式）
 */
export class ApiService {
    static #instance = null;
    #baseUrl = '';

    static getInstance() {
        if (!ApiService.#instance) {
            ApiService.#instance = new ApiService();
        }
        return ApiService.#instance;
    }

    async get(url, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullUrl = query ? `${this.#baseUrl}${url}?${query}` : `${this.#baseUrl}${url}`;
        return this.#request(fullUrl, { method: 'GET' });
    }

    async post(url, data = {}) {
        return this.#request(`${this.#baseUrl}${url}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
    }

    async patch(url, data = {}) {
        return this.#request(`${this.#baseUrl}${url}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
    }

    async delete(url) {
        return this.#request(`${this.#baseUrl}${url}`, { method: 'DELETE' });
    }

    async #request(url, options) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            const response = await fetch(url, { ...options, credentials: 'same-origin', signal: controller.signal });
            clearTimeout(timeoutId);

            let data;
            try { data = await response.json(); } catch { data = { success: false, message: `HTTP ${response.status}` }; }

            if (!response.ok || data.success === false) {
                throw new Error(data.message || `HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            if (error.name === 'AbortError') throw new Error('请求超时');
            throw error;
        }
    }
}
