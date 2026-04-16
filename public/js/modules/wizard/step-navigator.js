/**
 * 分步向导导航器
 */
import { StateManager } from '/js/modules/core/state-manager.js';

const STEPS = ['credential', 'select_source', 'mapping', 'execute', 'report'];

export class StepNavigator {
    #navEl;
    #contentEl;
    #state;
    #completedSteps = new Set();

    constructor(navId, contentId) {
        this.#navEl = document.getElementById(navId);
        this.#contentEl = document.getElementById(contentId);
        this.#state = StateManager.getInstance();
    }

    init() {
        this.#bindEvents();
        this.goTo('credential');
    }

    goTo(stepName) {
        if (!STEPS.includes(stepName)) return;

        const currentIdx = STEPS.indexOf(this.#state.get('currentStep'));
        const targetIdx = STEPS.indexOf(stepName);

        if (targetIdx > currentIdx + 1 && !this.#completedSteps.has(STEPS[targetIdx - 1])) {
            M.toast({ html: '请先完成当前步骤', classes: 'orange' });
            return;
        }

        this.#state.set('currentStep', stepName);
        this.#updateNav(stepName);
        this.#renderStep(stepName);
    }

    completeStep(stepName) {
        this.#completedSteps.add(stepName);
        const idx = STEPS.indexOf(stepName);
        if (idx < STEPS.length - 1) {
            this.goTo(STEPS[idx + 1]);
        }
    }

    #bindEvents() {
        this.#navEl.querySelectorAll('.step').forEach(el => {
            el.addEventListener('click', () => {
                const step = el.dataset.step;
                if (this.#completedSteps.has(step) || step === this.#state.get('currentStep')) {
                    this.goTo(step);
                }
            });
        });
    }

    #updateNav(activeStep) {
        this.#navEl.querySelectorAll('.step').forEach(el => {
            el.classList.remove('active', 'completed');
            const step = el.dataset.step;
            if (step === activeStep) {
                el.classList.add('active');
            } else if (this.#completedSteps.has(step)) {
                el.classList.add('completed');
            }
        });
    }

    async #renderStep(stepName) {
        this.#contentEl.innerHTML = '<div class="center-align" style="padding:60px 0;"><div class="preloader-wrapper active"><div class="spinner-layer spinner-blue-only"><div class="circle-clipper left"><div class="circle"></div></div><div class="gap-patch"><div class="circle"></div></div><div class="circle-clipper right"><div class="circle"></div></div></div></div><p class="grey-text">加载中...</p></div>';

        const MODULE_MAP = {
            credential: 'credential',
            select_source: 'aliyun',
            mapping: 'mapping',
            execute: 'execute',
            report: 'report',
        };

        try {
            const modulePath = MODULE_MAP[stepName] || stepName;
            const module = await import(`/js/modules/${modulePath}/index.js`);
            if (module.render) {
                this.#contentEl.innerHTML = '';
                try {
                    module.render(this.#contentEl, this);
                } catch (renderErr) {
                    console.error(`步骤 ${stepName} 渲染失败:`, renderErr);
                    this.#contentEl.innerHTML = `
                        <div class="card-panel red lighten-4">
                            <h5><i class="material-icons left">error</i>页面渲染错误</h5>
                            <p>${renderErr.message}</p>
                        </div>`;
                }
            }
        } catch (e) {
            console.error(`步骤 ${stepName} 模块加载失败:`, e);
            this.#contentEl.innerHTML = `
                <div class="card-panel blue-grey lighten-5">
                    <h5><i class="material-icons left">construction</i>功能开发中</h5>
                    <p>步骤「${stepName}」的页面正在开发中...</p>
                    <p class="red-text" style="font-size:12px;">${e.message}</p>
                </div>`;
        }
    }
}
