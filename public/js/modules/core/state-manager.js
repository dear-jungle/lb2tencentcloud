/**
 * 全局状态管理器（单例模式）
 */
export class StateManager {
    static #instance = null;

    #state = {
        currentStep: 'credential',
        taskId: null,
        credentials: { aliyun: { configured: false }, tencent: { configured: false } },
        sourceInstances: [],
        sourceConfigs: {},      // { instanceId: { listeners: [...] } }
        instanceMappings: [],   // [{sourceId, targetId, sourceName, targetName, listeners}]
        mappingResults: {},     // { sourceId: {targetId, results[], summary} } — 按实例分组
        planItems: [],
        stepConfirm: false,     // 是否逐项确认
        executionStatus: null,
    };

    #listeners = new Map();

    static getInstance() {
        if (!StateManager.#instance) StateManager.#instance = new StateManager();
        return StateManager.#instance;
    }

    get(key) { return key ? this.#state[key] : { ...this.#state }; }

    set(key, value) {
        this.#state[key] = value;
        (this.#listeners.get(key) || []).forEach(cb => cb(value));
    }

    on(key, callback) {
        if (!this.#listeners.has(key)) this.#listeners.set(key, []);
        this.#listeners.get(key).push(callback);
    }

    clearListeners(key) {
        if (key) this.#listeners.delete(key);
        else this.#listeners.clear();
    }
}
