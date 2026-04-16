/**
 * 应用入口
 */
import { StateManager } from '/js/modules/core/state-manager.js';
import { ApiService } from '/js/modules/core/api-service.js';
import { StepNavigator } from '/js/modules/wizard/step-navigator.js';

document.addEventListener('DOMContentLoaded', () => {
    if (typeof M !== 'undefined') M.AutoInit();

    const state = StateManager.getInstance();
    const api = ApiService.getInstance();
    const stepNav = new StepNavigator('step-navigator', 'step-content');

    // 非阻塞健康检查
    api.get('/api/health').then(res => {
        if (res.success) console.log('后端连接正常');
    }).catch(() => {});

    stepNav.init();
});
