/**
 * 步骤1 — 凭证配置：纯凭证填写 + 验证 + Cookie 持久化
 *
 * 地域选择已移至步骤2（实例关联）
 */
import { ApiService } from '/js/modules/core/api-service.js';
import { StateManager } from '/js/modules/core/state-manager.js';
import { CookieHelper, CREDS_COOKIE_KEY } from '/js/modules/core/cookie-helper.js';

export function render(container, nav) {
    const api = ApiService.getInstance();
    const state = StateManager.getInstance();
    const cookieHelper = CookieHelper.getInstance();

    container.innerHTML = `
        <div class="row"><div class="col s12">
            <h5><i class="material-icons left">vpn_key</i>云平台凭证配置</h5>
            <p class="grey-text">请输入阿里云（源端）和腾讯云（目标端）凭证，系统将验证有效性。凭证将保存在浏览器本地，7天内免重复输入。</p>
        </div></div>
        <div class="row">
            <div class="col s12 m6"><div class="card"><div class="card-content">
                <span class="card-title orange-text text-darken-2"><i class="material-icons left">cloud</i>阿里云（源端·只读）</span>
                <div class="input-field"><input id="c-aliyun-ak" type="text"><label for="c-aliyun-ak">AccessKey ID</label></div>
                <div class="input-field"><input id="c-aliyun-sk" type="password"><label for="c-aliyun-sk">AccessKey Secret</label></div>
                <button id="c-btn-verify-ali" class="btn waves-effect orange darken-2"><i class="material-icons left">verified</i>验证连接</button>
                <span id="c-ali-status" style="margin-left:8px"></span>
            </div></div></div>
            <div class="col s12 m6"><div class="card"><div class="card-content">
                <span class="card-title blue-text text-darken-2"><i class="material-icons left">cloud_queue</i>腾讯云（目标端）</span>
                <div class="input-field"><input id="c-tencent-sid" type="text"><label for="c-tencent-sid">SecretId</label></div>
                <div class="input-field"><input id="c-tencent-sk" type="password"><label for="c-tencent-sk">SecretKey</label></div>
                <button id="c-btn-verify-tc" class="btn waves-effect blue darken-2"><i class="material-icons left">verified</i>验证连接</button>
                <span id="c-tc-status" style="margin-left:8px"></span>
            </div></div></div>
        </div>
        <div class="row">
            <div class="col s6">
                <button id="c-btn-load-env" class="btn-flat waves-effect"><i class="material-icons left">file_download</i>从.env加载</button>
                <button id="c-btn-clear-cookie" class="btn-flat waves-effect red-text" style="margin-left:8px"><i class="material-icons left">delete_forever</i>清除已保存凭证</button>
            </div>
            <div class="col s6 right-align">
                <button id="c-btn-next" class="btn-large waves-effect blue" disabled>下一步<i class="material-icons right">arrow_forward</i></button>
            </div>
        </div>`;

    let aliOk = false, tcOk = false;

    // 自动填充已保存的凭证
    autoFill(cookieHelper);

    // 从.env加载
    document.getElementById('c-btn-load-env')?.addEventListener('click', async () => {
        try {
            const r = await api.post('/api/credentials/load-env');
            const d = r.data || {};
            if (d.aliyun_ak) { const el = document.getElementById('c-aliyun-ak'); if(el) el.value = d.aliyun_ak; }
            if (d.aliyun_sk) { const el = document.getElementById('c-aliyun-sk'); if(el) el.value = d.aliyun_sk; }
            if (d.tencent_sid) { const el = document.getElementById('c-tencent-sid'); if(el) el.value = d.tencent_sid; }
            if (d.tencent_sk) { const el = document.getElementById('c-tencent-sk'); if(el) el.value = d.tencent_sk; }
            M.toast({html: r.message || '已加载', classes: 'teal'});
        } catch(e) { M.toast({html: '加载失败', classes: 'red'}); }
    });

    // 清除已保存的凭证
    document.getElementById('c-btn-clear-cookie')?.addEventListener('click', () => {
        cookieHelper.remove(CREDS_COOKIE_KEY);
        document.getElementById('c-aliyun-ak').value = '';
        document.getElementById('c-aliyun-sk').value = '';
        document.getElementById('c-tencent-sid').value = '';
        document.getElementById('c-tencent-sk').value = '';
        aliOk = false; tcOk = false;
        document.getElementById('c-ali-status').innerHTML = '';
        document.getElementById('c-tc-status').innerHTML = '';
        checkNext();
        M.toast({html: '已清除保存的凭证', classes: 'orange'});
    });

    // 验证阿里云
    document.getElementById('c-btn-verify-ali')?.addEventListener('click', async () => {
        const ak = document.getElementById('c-aliyun-ak')?.value?.trim();
        const sk = document.getElementById('c-aliyun-sk')?.value?.trim();
        if (!ak || !sk) { M.toast({html: '请填写AccessKey', classes: 'orange'}); return; }
        const btn = document.getElementById('c-btn-verify-ali');
        btn.disabled = true;
        try {
            await api.post('/api/credentials/aliyun/verify', {access_key_id: ak, access_key_secret: sk});
            aliOk = true;
            document.getElementById('c-ali-status').innerHTML = '<i class="material-icons green-text">check_circle</i> 成功';
            saveCredentials(cookieHelper);
            checkNext();
        } catch(e) {
            document.getElementById('c-ali-status').innerHTML = '<i class="material-icons red-text">error</i> ' + e.message;
        }
        btn.disabled = false;
    });

    // 验证腾讯云
    document.getElementById('c-btn-verify-tc')?.addEventListener('click', async () => {
        const sid = document.getElementById('c-tencent-sid')?.value?.trim();
        const sk = document.getElementById('c-tencent-sk')?.value?.trim();
        if (!sid || !sk) { M.toast({html: '请填写SecretId/Key', classes: 'orange'}); return; }
        const btn = document.getElementById('c-btn-verify-tc');
        btn.disabled = true;
        try {
            await api.post('/api/credentials/tencent/verify', {secret_id: sid, secret_key: sk});
            tcOk = true;
            document.getElementById('c-tc-status').innerHTML = '<i class="material-icons green-text">check_circle</i> 成功';
            saveCredentials(cookieHelper);
            checkNext();
        } catch(e) {
            document.getElementById('c-tc-status').innerHTML = '<i class="material-icons red-text">error</i> ' + e.message;
        }
        btn.disabled = false;
    });

    // 下一步
    document.getElementById('c-btn-next')?.addEventListener('click', () => {
        state.set('credentials', {
            aliyun: { configured: true },
            tencent: { configured: true },
        });
        nav.completeStep('credential');
    });

    function checkNext() {
        const btn = document.getElementById('c-btn-next');
        if (btn) btn.disabled = !(aliOk && tcOk);
    }

    /** 从 Cookie 读取并自动填充凭证 */
    function autoFill(helper) {
        const saved = helper.getJSON(CREDS_COOKIE_KEY);
        if (!saved) return;

        if (saved.aliyun_ak) { const el = document.getElementById('c-aliyun-ak'); if (el) el.value = saved.aliyun_ak; }
        if (saved.aliyun_sk) { const el = document.getElementById('c-aliyun-sk'); if (el) el.value = saved.aliyun_sk; }
        if (saved.tencent_sid) { const el = document.getElementById('c-tencent-sid'); if (el) el.value = saved.tencent_sid; }
        if (saved.tencent_sk) { const el = document.getElementById('c-tencent-sk'); if (el) el.value = saved.tencent_sk; }

        if (saved.ali_verified) aliOk = true;
        if (saved.tc_verified) tcOk = true;
        if (aliOk) document.getElementById('c-ali-status').innerHTML = '<i class="material-icons green-text">check_circle</i> 已加载';
        if (tcOk) document.getElementById('c-tc-status').innerHTML = '<i class="material-icons green-text">check_circle</i> 已加载';
        checkNext();
    }

    /** 两侧都验证成功后保存到 Cookie */
    function saveCredentials(helper) {
        helper.set(CREDS_COOKIE_KEY, {
            aliyun_ak: document.getElementById('c-aliyun-ak')?.value?.trim(),
            aliyun_sk: document.getElementById('c-aliyun-sk')?.value?.trim(),
            tencent_sid: document.getElementById('c-tencent-sid')?.value?.trim(),
            tencent_sk: document.getElementById('c-tencent-sk')?.value?.trim(),
            ali_verified: aliOk,
            tc_verified: tcOk,
        }, { maxAgeSeconds: 604800 });
    }
}
