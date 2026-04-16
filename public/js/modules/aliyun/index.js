/**
 * 步骤2 — 实例关联：地域选择（顶部）+ 源/目标实例关联（左右两栏）
 *
 * 地域选择从步骤1移至此处，支持动态修改和级联重置
 */
import { ApiService } from '/js/modules/core/api-service.js';
import { StateManager } from '/js/modules/core/state-manager.js';

export function render(container, nav) {
    const api = ApiService.getInstance();
    const state = StateManager.getInstance();
    const creds = state.get('credentials') || {};

    let srcInstances = [];
    let tgtInstances = [];
    let srcConfigs = {};
    let currentAliRegion = creds.aliyun?.region || '';
    let currentTcRegion = creds.tencent?.region || '';

    container.innerHTML = `
        <div class="row"><div class="col s12">
            <h5><i class="material-icons left">link</i>实例关联</h5>
            <p class="grey-text">先选择源端和目标端地域，再在下方关联实例。支持一对一和多对一。</p>
        </div></div>

        <!-- 地域选择区 -->
        <div class="row" id="ia-region-bar">
            <div class="col s12 m6">
                <div class="card-panel grey lighten-4">
                    <label class="active orange-text"><i class="material-icons tiny left">cloud</i>源端地域（阿里云）</label>
                    <select id="ia-ali-region" class="browser-default"></select>
                </div>
            </div>
            <div class="col s12 m6">
                <div class="card-panel grey lighten-4">
                    <label class="active blue-text"><i class="material-icons tiny left">cloud_queue</i>目标地域（腾讯云）</label>
                    <select id="ia-tc-region" class="browser-default"></select>
                </div>
            </div>
        </div>

        <!-- 实例关联区 -->
        <div class="row">
            <div class="col s12 m6">
                <h6 class="orange-text text-darken-2"><i class="material-icons left small">cloud</i>源端实例</h6>
                <div id="ia-src-loading" class="center-align" style="padding:30px"><div class="preloader-wrapper small active"><div class="spinner-layer spinner-orange-only"><div class="circle-clipper left"><div class="circle"></div></div><div class="gap-patch"><div class="circle"></div></div><div class="circle-clipper right"><div class="circle"></div></div></div></div></div>
                <div id="ia-src-list" style="display:none"></div>
            </div>
            <div class="col s12 m6">
                <h6 class="blue-text text-darken-1"><i class="material-icons left small">cloud_queue</i>目标端实例</h6>
                <div id="ia-tgt-info" class="grey-text" style="padding:16px">请先在左侧勾选源端实例</div>
            </div>
        </div>
        <div id="ia-conflict" style="display:none;margin-top:12px"></div>
        <div class="row" style="margin-top:20px">
            <div class="col s6"><button id="ia-prev" class="btn-flat waves-effect"><i class="material-icons left">arrow_back</i>上一步</button></div>
            <div class="col s6 right-align"><button id="ia-next" class="btn-large waves-effect blue" disabled>下一步<i class="material-icons right">arrow_forward</i></button></div>
        </div>

        <!-- 地域变更确认弹窗 -->
        <div id="ia-region-modal" class="modal" style="max-width:480px">
            <div class="modal-content">
                <h5><i class="material-icons left orange-text">warning</i>确认修改地域</h5>
                <p>修改地域将清空后续所有步骤的数据（实例关联、配置映射、迁移计划等），并重新加载实例列表。</p>
                <p><strong>确定继续吗？</strong></p>
            </div>
            <div class="modal-footer">
                <a href="#!" id="ia-region-cancel" class="modal-close waves-effect waves-red btn-flat">取消</a>
                <a href="#!" id="ia-region-confirm" class="waves-effect waves-green btn blue">确认修改</a>
            </div>
        </div>`;

    document.getElementById('ia-prev')?.addEventListener('click', () => nav.goTo('credential'));
    document.getElementById('ia-next')?.addEventListener('click', onNext);

    // 初始化地域弹窗
    let regionModal;
    if (typeof M !== 'undefined') {
        regionModal = M.Modal.init(document.getElementById('ia-region-modal'), { dismissible: false });
    }
    let pendingRegionChange = null; // { aliRegion, tcRegion }

    // ── 加载地域列表 ────────────────────────────────
    Promise.all([api.get('/api/aliyun/regions'), api.get('/api/tencent/regions')]).then(([a, t]) => {
        const aliSel = document.getElementById('ia-ali-region');
        const tcSel = document.getElementById('ia-tc-region');

        if (aliSel && a.data?.regions) {
            aliSel.innerHTML = '<option value="">选择地域</option>' + a.data.regions.map(r =>
                `<option value="${esc(r.id)}">${esc(r.name)}</option>`
            ).join('');
            if (currentAliRegion) aliSel.value = currentAliRegion;
        }
        if (tcSel && t.data?.regions) {
            tcSel.innerHTML = '<option value="">选择地域</option>' + t.data.regions.map(r =>
                `<option value="${esc(r.id)}">${esc(r.name)}</option>`
            ).join('');
            if (currentTcRegion) tcSel.value = currentTcRegion;
        }

        // 如果已有地域，立即加载实例
        if (currentAliRegion && currentTcRegion) loadInstances();
    }).catch(() => {});

    // ── 地域变更处理 ────────────────────────────────
    document.getElementById('ia-ali-region')?.addEventListener('change', (e) => {
        const newVal = e.target.value;
        if (!newVal || newVal === currentAliRegion) return;
        pendingRegionChange = { ...pendingRegionChange, aliRegion: newVal };
        if (regionModal) regionModal.open();
    });

    document.getElementById('ia-tc-region')?.addEventListener('change', (e) => {
        const newVal = e.target.value;
        if (!newVal || newVal === currentTcRegion) return;
        pendingRegionChange = { ...pendingRegionChange, tcRegion: newVal };
        if (regionModal) regionModal.open();
    });

    document.getElementById('ia-region-cancel')?.addEventListener('click', () => {
        // 恢复下拉框原值
        if (currentAliRegion) document.getElementById('ia-ali-region').value = currentAliRegion;
        if (currentTcRegion) document.getElementById('ia-tc-region').value = currentTcRegion;
        pendingRegionChange = null;
    });

    document.getElementById('ia-region-confirm')?.addEventListener('click', () => {
        if (!pendingRegionChange) return;
        if (regionModal) regionModal.close();

        // 应用新地域值
        if (pendingRegionChange.aliRegion !== undefined) {
            currentAliRegion = pendingRegionChange.aliRegion;
            document.getElementById('ia-ali-region').value = currentAliRegion;
        }
        if (pendingRegionChange.tcRegion !== undefined) {
            currentTcRegion = pendingRegionChange.tcRegion;
            document.getElementById('ia-tc-region').value = currentTcRegion;
        }

        // 级联重置后续状态
        cascadeReset();

        // 重新加载实例
        loadInstances();
        pendingRegionChange = null;

        M.toast({html: '地域已变更，实例列表已重新加载', classes: 'teal'});
    });

    // ── 加载实例列表 ─────────────────────────────────
    function loadInstances() {
        if (!currentAliRegion || !currentTcRegion) return;

        // 显示 loading，隐藏旧数据
        const loadingEl = document.getElementById('ia-src-loading');
        const listEl = document.getElementById('ia-src-list');
        const tgtInfo = document.getElementById('ia-tgt-info');
        if (loadingEl) loadingEl.style.display = 'block';
        if (listEl) listEl.style.display = 'none';
        if (tgtInfo) tgtInfo.innerHTML = '<span class="grey-text" style="padding:16px">请先在左侧勾选源端实例</span>';

        srcInstances = [];
        tgtInstances = [];

        Promise.all([
            api.get('/api/aliyun/clb/instances', { region: currentAliRegion }),
            api.get('/api/tencent/clb/instances', { region: currentTcRegion }),
        ]).then(([srcRes, tgtRes]) => {
            srcInstances = srcRes.data?.instances || [];
            tgtInstances = tgtRes.data?.instances || [];
            renderSrcList();
        }).catch(e => {
            const el = document.getElementById('ia-src-loading');
            if (el) el.innerHTML = `<div class="card-panel red lighten-4">加载失败: ${esc(e.message)}</div>`;
        });
    }

    // ── 级联重置 ─────────────────────────────────────
    function cascadeReset() {
        state.set('instanceMappings', []);
        state.set('sourceConfigs', {});
        state.set('sourceInstances', []);
        state.set('mappingResults', {});
        state.set('planItems', []);
        state.set('executionStatus', null);
        // 更新凭证中的地域信息
        state.set('credentials', {
            aliyun: { configured: true, region: currentAliRegion },
            tencent: { configured: true, region: currentTcRegion },
        });
    }

    // ════════════════════════════════════════════════
    // 以下为原有实例关联逻辑（与之前基本一致）
    // ════════════════════════════════════════════════

    function renderSrcList() {
        const loading = document.getElementById('ia-src-loading');
        const list = document.getElementById('ia-src-list');
        if (!loading || !list) return;

        if (!srcInstances.length) {
            loading.innerHTML = '<div class="card-panel orange lighten-4">该地域无 CLB 实例</div>';
            return;
        }

        loading.style.display = 'none';
        list.style.display = 'block';

        list.innerHTML = `
            <table class="striped highlight" style="font-size:13px">
                <thead><tr>
                    <th style="width:35px"><label><input type="checkbox" id="ia-selall"><span></span></label></th>
                    <th>实例</th><th>VIP</th><th>监听器</th>
                </tr></thead>
                <tbody>${srcInstances.map(i => `<tr>
                    <td><label><input type="checkbox" class="ia-src-cb" value="${esc(i.instance_id)}"
                        data-name="${esc(i.instance_name)}"><span></span></label></td>
                    <td><strong>${esc(i.instance_name || i.instance_id)}</strong><br>
                        <code style="font-size:11px">${esc(i.instance_id)}</code></td>
                    <td>${esc(i.address || '-')}</td>
                    <td><span class="badge grey white-text" style="float:none">${esc(i.network_type || '-')}</span></td>
                </tr>`).join('')}</tbody>
            </table>`;

        document.getElementById('ia-selall')?.addEventListener('change', e => {
            list.querySelectorAll('.ia-src-cb').forEach(c => c.checked = e.target.checked);
            onSelectionChange();
        });
        list.addEventListener('change', e => {
            if (e.target.classList.contains('ia-src-cb')) onSelectionChange();
        });
    }

    function onSelectionChange() {
        const selected = getSelected();
        const tgtInfo = document.getElementById('ia-tgt-info');
        if (!tgtInfo) return;

        if (!selected.length) {
            tgtInfo.innerHTML = '<span class="grey-text" style="padding:16px">请先在左侧勾选源端实例</span>';
            updateNextBtn();
            return;
        }

        if (!tgtInstances.length) {
            tgtInfo.innerHTML = `
                <div class="card-panel orange lighten-4" style="margin:0">
                    <i class="material-icons left orange-text">info_outline</i>
                    <strong>目标端地域暂无 CLB 实例</strong>
                    <p style="margin:8px 0 0;font-size:13px">
                        腾讯云 ${currentTcRegion} 地域下没有已有 CLB 实例。<br>
                        请先在腾讯云控制台创建 CLB 实例，然后刷新此页面。
                    </p>
                </div>`;
            updateNextBtn();
            return;
        }

        const tgtOptions = tgtInstances.map(t =>
            `<option value="${esc(t.instance_id)}" data-name="${esc(t.instance_name)}">${esc(t.instance_id)} (${esc(t.instance_name || '无名称')})</option>`
        ).join('');

        tgtInfo.innerHTML = selected.map(s => `
            <div class="card-panel" style="padding:12px;margin-bottom:8px">
                <div style="margin-bottom:6px">
                    <strong>${esc(s.name || s.id)}</strong>
                    <code style="font-size:11px;margin-left:8px">${esc(s.id)}</code>
                    <span style="float:right">&rarr;</span>
                </div>
                <select class="browser-default ia-tgt-select" data-source-id="${esc(s.id)}" data-source-name="${esc(s.name)}">
                    <option value="">选择目标实例</option>
                    ${tgtOptions}
                </select>
            </div>`).join('');

        tgtInfo.querySelectorAll('.ia-tgt-select').forEach(sel => {
            sel.addEventListener('change', () => {
                detectConflicts();
                updateNextBtn();
            });
        });

        updateNextBtn();
    }

    function getSelected() {
        const result = [];
        document.querySelectorAll('.ia-src-cb:checked').forEach(c => {
            result.push({ id: c.value, name: c.dataset.name || '' });
        });
        return result;
    }

    function getMappings() {
        const mappings = [];
        document.querySelectorAll('.ia-tgt-select').forEach(sel => {
            const sourceId = sel.dataset.sourceId;
            const sourceName = sel.dataset.sourceName || '';
            const targetId = sel.value;
            if (!targetId) return;
            const targetOpt = sel.selectedOptions[0];
            const targetName = targetOpt?.dataset.name || '';
            mappings.push({ sourceId, sourceName, targetId, targetName });
        });
        return mappings;
    }

    function detectConflicts() {
        const conflictEl = document.getElementById('ia-conflict');
        if (!conflictEl) return;

        const mappings = getMappings();
        const byTarget = {};
        for (const m of mappings) {
            if (!byTarget[m.targetId]) byTarget[m.targetId] = [];
            byTarget[m.targetId].push(m);
        }

        const conflicts = [];
        for (const [targetId, sources] of Object.entries(byTarget)) {
            if (sources.length < 2) continue;
            const portMap = {};
            for (const src of sources) {
                const cfg = srcConfigs[src.sourceId] || state.get('sourceConfigs')?.[src.sourceId];
                if (!cfg?.listeners) continue;
                for (const l of cfg.listeners) {
                    const key = `${(l.listener_protocol||'').toLowerCase()}:${l.listener_port}`;
                    if (portMap[key]) {
                        conflicts.push({
                            key, targetId,
                            srcA: portMap[key],
                            srcB: src.sourceId,
                            protocol: l.listener_protocol,
                            port: l.listener_port,
                        });
                    } else {
                        portMap[key] = src.sourceId;
                    }
                }
            }
        }

        if (!conflicts.length) {
            conflictEl.style.display = 'none';
            return;
        }

        conflictEl.style.display = 'block';
        conflictEl.innerHTML = `
            <div class="card-panel red lighten-5">
                <h6 class="red-text"><i class="material-icons left">warning</i>端口冲突 (${conflicts.length})</h6>
                <table class="striped" style="font-size:13px">
                    <thead><tr><th>协议:端口</th><th>实例A</th><th>实例B</th><th>处理方式</th></tr></thead>
                    <tbody>${conflicts.map((c, i) => `<tr>
                        <td><strong>${esc(c.protocol)}:${c.port}</strong></td>
                        <td><code>${esc(c.srcA)}</code></td>
                        <td><code>${esc(c.srcB)}</code></td>
                        <td>
                            <select class="browser-default ia-conflict-resolve" data-idx="${i}" style="width:auto">
                                <option value="keepA">保留 A</option>
                                <option value="keepB">保留 B</option>
                                <option value="skip">跳过</option>
                            </select>
                        </td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>`;
    }

    function updateNextBtn() {
        const btn = document.getElementById('ia-next');
        if (!btn) return;
        const selected = getSelected();
        const mappings = getMappings();
        btn.disabled = !selected.length || mappings.length < selected.length;
    }

    async function onNext() {
        const selected = getSelected();
        const mappings = getMappings();

        if (mappings.length < selected.length) {
            M.toast({ html: '请为所有选中实例关联目标端', classes: 'orange' });
            return;
        }

        // 确保所有源端配置已拉取
        const cfgs = state.get('sourceConfigs') || {};
        for (const m of mappings) {
            if (!cfgs[m.sourceId]) {
                try {
                    const r = await api.get(`/api/aliyun/clb/instances/${m.sourceId}/config`, { region: currentAliRegion });
                    cfgs[m.sourceId] = { listeners: r.data?.listeners || [], instance: r.data?.instance };
                } catch (e) {
                    console.error(`拉取 ${m.sourceId} 配置失败:`, e);
                }
            }
        }
        state.set('sourceConfigs', cfgs);

        // 构建 instanceMappings
        const instanceMappings = mappings.map(m => ({
            sourceId: m.sourceId,
            targetId: m.targetId,
            sourceName: m.sourceName,
            targetName: m.targetName,
            listeners: cfgs[m.sourceId]?.listeners || [],
        }));

        state.set('instanceMappings', instanceMappings);
        state.set('sourceInstances', selected.map(s => ({ instance_id: s.id, instance_name: s.name })));
        nav.completeStep('select_source');
    }
}

function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
