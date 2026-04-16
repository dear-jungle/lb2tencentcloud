/**
 * JSON 侧边抽屉组件 — 右侧滑出面板
 */
export class JsonDrawer {
    #overlay = null;
    #panel = null;

    constructor() {
        this.#createDOM();
    }

    #createDOM() {
        // 遮罩
        this.#overlay = document.createElement('div');
        this.#overlay.className = 'json-drawer-overlay';
        this.#overlay.addEventListener('click', () => this.close());

        // 面板
        this.#panel = document.createElement('div');
        this.#panel.className = 'json-drawer-panel';
        this.#panel.innerHTML = `
            <div class="json-drawer-header">
                <span class="json-drawer-title">JSON 对比</span>
                <a href="#!" class="json-drawer-close"><i class="material-icons">close</i></a>
            </div>
            <div class="json-drawer-body">
                <div class="json-drawer-section">
                    <h6 class="orange-text text-darken-2">阿里云原始配置</h6>
                    <pre class="json-drawer-pre" id="jd-source"></pre>
                </div>
                <div class="json-drawer-section">
                    <h6 class="blue-text text-darken-1">腾讯云映射配置</h6>
                    <pre class="json-drawer-pre" id="jd-target"></pre>
                </div>
            </div>`;

        this.#panel.querySelector('.json-drawer-close').addEventListener('click', () => this.close());
        document.body.appendChild(this.#overlay);
        document.body.appendChild(this.#panel);
    }

    open(sourceJson, targetJson, title) {
        const srcEl = this.#panel.querySelector('#jd-source');
        const tgtEl = this.#panel.querySelector('#jd-target');
        const titleEl = this.#panel.querySelector('.json-drawer-title');
        if (srcEl) srcEl.textContent = typeof sourceJson === 'string' ? sourceJson : JSON.stringify(sourceJson, null, 2);
        if (tgtEl) tgtEl.textContent = typeof targetJson === 'string' ? targetJson : JSON.stringify(targetJson, null, 2);
        if (titleEl && title) titleEl.textContent = title;
        this.#overlay.classList.add('active');
        this.#panel.classList.add('active');
    }

    close() {
        this.#overlay.classList.remove('active');
        this.#panel.classList.remove('active');
    }

    destroy() {
        this.#overlay?.remove();
        this.#panel?.remove();
    }
}
