/**
 * Cookie 工具类 — 读写、混淆编解码
 *
 * 混淆方式：Base64 编码 + XOR（非加密，防肉眼识别）
 */
const XOR_KEY = 0x5A;  // 固定 XOR 密钥

export class CookieHelper {
    static #instance = null;

    static getInstance() {
        if (!CookieHelper.#instance) CookieHelper.#instance = new CookieHelper();
        return CookieHelper.#instance;
    }

    /**
     * 设置 Cookie（值自动混淆编码）
     * @param {string} name - Cookie 名称
     * @param {string|object} value - 值（对象自动 JSON 序列化）
     * @param {object} options - { maxAgeSeconds, path, sameSite }
     */
    set(name, value, options = {}) {
        const str = typeof value === 'object' ? JSON.stringify(value) : String(value);
        const encoded = this.#encode(str);
        const maxAge = options.maxAgeSeconds ?? 604800; // 默认 7 天
        const path = options.path || '/';
        const sameSite = options.sameSite || 'Strict';
        // 不设 HttpOnly，前端 JS 需要读取填充表单
        document.cookie = `${name}=${encoded};max-age=${maxAge};path=${path};samesite=${sameSite}`;
    }

    /**
     * 获取并解码 Cookie 值
     * @param {string} name
     * @returns {string|null}
     */
    get(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        if (!match) return null;
        try {
            return this.#decode(match[2]);
        } catch {
            return null;
        }
    }

    /**
     * 获取并解析为 JSON 对象
     * @param {string} name
     * @returns {object|null}
     */
    getJSON(name) {
        const raw = this.get(name);
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    /**
     * 删除 Cookie
     * @param {string} name
     */
    remove(name) {
        document.cookie = `${name}=;max-age=0=path=/;samesite=Strict`;
    }

    // ── 混淆/解混淆 ──────────────────────────────────

    #encode(str) {
        // 1. XOR 每个字符
        const xored = Array.from(str, ch => String.fromCharCode(ch.charCodeAt(0) ^ XOR_KEY)).join('');
        // 2. Base64 编码
        return btoa(unescape(encodeURIComponent(xored)));
    }

    #decode(encoded) {
        // 1. Base64 解码
        const xored = decodeURIComponent(escape(atob(encoded)));
        // 2. XOR 还原
        return Array.from(xored, ch => String.fromCharCode(ch.charCodeAt(0) ^ XOR_KEY)).join('');
    }
}

// 凭证专用 key
export const CREDS_COOKIE_KEY = 'lb2tc_creds';
