/**
 * 步骤3 — 配置映射与计划：合并原配置对比 + 迁移计划功能
 *
 * 上方：统计卡片 + 按实例分组的字段级对比（Collapsible）
 * 中间：目标端冲突警告面板
 * 下方：迁移计划表格（复选框勾选）
 * 底部："确认并开始执行"按钮 → 二次确认弹窗
 */
import { ApiService } from '/js/modules/core/api-service.js';
import { StateManager } from '/js/modules/core/state-manager.js';
import { JsonDrawer } from '/js/modules/components/json-drawer.js';

let drawer = null;

export function render(container, nav) {
    const api = ApiService.getInstance();
    const state = StateManager.getInstance();
    const instanceMappings = state.get('instanceMappings') || [];

    if (drawer) drawer.destroy();
    drawer = new JsonDrawer();

    container.innerHTML = `
        <div class="row"><div class="col s12">
            <h5><i class="material-icons left">compare_arrows</i>配置映射与计划</h5>
            <p class="grey-text">按实例分组展示映射结果，不兼容项可选择替代方案。下方可勾选要执行的迁移项。</p>
        </div></div>

        <!-- 统计卡片 -->
        <div class="row" id="cd-stats">
            <div class="col s3"><div class="card-panel stat-card"><span class="stat-number blue-text" id="cd-total">-</span><div class="stat-label">总项</div></div></div>
            <div class="col s3"><div class="card-panel stat-card"><span class="stat-number green-text" id="cd-ok">-</span><div class="stat-label">完全映射</div></div></div>
            <div class="col s3"><div class="card-panel stat-card"><span class="stat-number orange-text" id="cd-partial">-</span><div class="stat-label">需确认</div></div></div>
            <div class="col s3"><div class="card-panel stat-card"><span class="stat-number red-text" id="cd-fail">-</span><div class="stat-label">不兼容</div></div></div>
        </div>

        <!-- 映射结果区域 -->
        <div id="cd-loading" class="center-align" style="padding:30px"><div class="preloader-wrapper active"><div class="spinner-layer spinner-blue-only"><div class="circle-clipper left"><div class="circle"></div></div><div class="gap-patch"><div class="circle"></div></div><div class="circle-clipper right"><div class="circle"></div></div></div></div><p class="grey-text">正在执行配置映射...</p></div>
        <div id="cd-groups" style="display:none"></div>

        <!-- 冲突警告面板 -->
        <div id="cd-target-conflict" style="display:none;margin-top:12px"></div>

        <!-- 迁移计划表格 -->
        <div id="cd-plan-section" style="display:none">
            <h6 style="margin-top:16px"><i class="material-icons tiny left">playlist_add_check</i>迁移执行计划</h6>
            <p class="grey-text" style="font-size:12px">以下为待执行的迁移项，取消勾选可跳过不需要的项。</p>
            <div id="cd-plan-table"></div>
        </div>

        <!-- 操作栏 -->
        <div class="row" style="margin-top:20px">
            <div class="col s6"><button id="cd-prev" class="btn-flat waves-effect"><i class="material-icons left">arrow_back</i>上一步</button></div>
            <div class="col s6 right-align"><button id="cd-next" class="btn-large waves-effect green darken-1"><i class="material-icons left">play_arrow</i>确认并开始执行</button></div>
        </div>

        <!-- 二次确认弹窗 -->
        <div id="cd-confirm-modal" class="modal" style="max-width:560px">
            <div class="modal-content">
                <h5><i class="material-icons left orange-text">warning</i>确认开始迁移</h5>
                <p>以下操作将<strong>真实写入腾讯云</strong>，请仔细确认：</p>
                <div id="cd-confirm-stats" style="margin:16px 0"></div>
                <p style="margin-top:12px">
                    <label>
                        <input type="checkbox" id="cd-step-confirm-cb">
                        <span style="font-size:13px">执行过程中每一步写操作弹窗逐项确认（可随时跳过或终止）</span>
                    </label>
                </p>
                <div class="card-panel grey lighten-4" style="margin:8px 0;padding:10px;font-size:12px">
                    <i class="material-icons tiny grey-text">info</i>
                    不勾选则全部自动执行，勾选后每步都需手动确认。
                </div>
            </div>
            <div class="modal-footer">
                <a href="#!" id="cd-modal-cancel" class="btn-flat waves-effect">取消</a>
                <a href="#!" id="cd-modal-go" class="btn waves-effect green darken-1">确认执行</a>
            </div>
        </div>`;

    // ── 事件绑定 ────────────────────────────────
    document.getElementById('cd-prev')?.addEventListener('click', () => nav.goTo('select_source'));

    let confirmModal;
    if (typeof M !== 'undefined') {
        confirmModal = M.Modal.init(document.getElementById('cd-confirm-modal'), { dismissible: true });
    }

    document.getElementById('cd-next')?.addEventListener('click', onConfirmExecute);

    document.getElementById('cd-modal-cancel')?.addEventListener('click', () => {
        if (confirmModal) confirmModal.close();
    });

    document.getElementById('cd-modal-go')?.addEventListener('click', () => {
        if (confirmModal) confirmModal.close();
        const selectedItems = getSelectedPlanItems();
        const stepConfirm = document.getElementById('cd-step-confirm-cb')?.checked || false;
        state.set('planItems', selectedItems);
        state.set('stepConfirm', stepConfirm);
        nav.completeStep('mapping');
    });

    // ── 执行映射 API ────────────────────────────
    api.post('/api/mapping/execute-by-instance', { instanceMappings }).then(res => {
        const loading = document.getElementById('cd-loading');
        const groupsEl = document.getElementById('cd-groups');
        if (!loading || !groupsEl) return;
        loading.style.display = 'none';
        groupsEl.style.display = 'block';

        const groups = res.data?.groups || {};
        const summary = res.data?.summary || {};

        // 统计卡片
        setText('cd-total', summary.total || 0);
        setText('cd-ok', summary.mapped || 0);
        setText('cd-partial', summary.partial || 0);
        setText('cd-fail', summary.incompatible || 0);

        // 保存映射结果到 state
        state.set('mappingResults', groups);

        // 渲染实例分组对比
        let html = '<ul class="collapsible expandable">';
        for (const [sourceId, group] of Object.entries(groups)) {
            const s = group.summary || {};
            const badges = [];
            if (s.mapped) badges.push(`<span class="badge green white-text" style="float:none">${s.mapped}&#x2713;</span>`);
            if (s.partial) badges.push(`<span class="badge orange white-text" style="float:none">${s.partial}&#x26A0;</span>`);
            if (s.incompatible) badges.push(`<span class="badge red white-text" style="float:none">${s.incompatible}&#x2717;</span>`);

            html += `<li>
                <div class="collapsible-header">
                    <i class="material-icons">storage</i>
                    <span><strong>${esc(group.sourceName || sourceId)}</strong> &rarr; <strong class="blue-text">${esc(group.targetName || group.targetId)}</strong></span>
                    <span style="margin-left:auto">${badges.join(' ')}
                        <a href="#!" class="cd-json-btn" data-source-id="${esc(sourceId)}" style="margin-left:8px"><i class="material-icons" style="font-size:18px">code</i>JSON</a>
                    </span>
                </div>
                <div class="collapsible-body" style="padding:8px">
                    ${renderGroupResults(group.results || [], sourceId)}
                </div>
            </li>`;
        }
        html += '</ul>';
        groupsEl.innerHTML = html;
        M.Collapsible.init(groupsEl.querySelectorAll('.collapsible'), { accordion: false });

        // JSON 抽屉按钮
        groupsEl.addEventListener('click', e => {
            const btn = e.target.closest('.cd-json-btn');
            if (!btn) return;
            e.preventDefault();
            e.stopPropagation();
            const sid = btn.dataset.sourceId;
            const group = groups[sid];
            if (!group) return;
            const sourceJson = group.results.map(r => r.source_config);
            const targetJson = group.results.map(r => r.target_config).filter(Boolean);
            drawer.open(sourceJson, targetJson, `${group.sourceName || sid} -> ${group.targetName || group.targetId}`);
        });

        // 替代方案下拉框变化
        groupsEl.addEventListener('change', e => {
            if (!e.target.classList.contains('cd-alt-select')) return;
            const sourceId = e.target.dataset.sourceId;
            const itemIdx = parseInt(e.target.dataset.itemIdx);
            const field = e.target.dataset.field;
            const newValue = e.target.value;
            const g = groups[sourceId];
            if (g?.results[itemIdx]?.target_config) {
                const keyMap = { scheduler: 'Scheduler', sticky_session_type: 'StickySessionType' };
                const targetKey = keyMap[field] || field;
                g.results[itemIdx].target_config[targetKey] = newValue;
                state.set('mappingResults', groups);
            }
        });

        // 渲染迁移计划表格
        renderPlanTable(groups);

        // 目标端冲突检测
        detectTargetConflicts(groups, instanceMappings);

    }).catch(e => {
        const el = document.getElementById('cd-loading');
        if (el) el.innerHTML = `<div class="card-panel red lighten-4">映射失败: ${esc(e.message)}</div>`;
    });

    // ══════════════════════════════════════════════
    // 渲染函数
    // ══════════════════════════════════════════════

    function renderGroupResults(results, sourceId) {
        if (!results.length) return '<p class="grey-text">无映射项</p>';
        return results.map((r, idx) => {
            const icon = r.status === 'mapped' ? 'check_circle' : r.status === 'partial' ? 'warning' : 'error';
            const color = r.status === 'mapped' ? 'green-text' : r.status === 'partial' ? 'orange-text' : 'red-text';
            const isListener = r.source_type === 'listener';
            return `<div class="card" style="margin:8px 0">
                <div class="card-content" style="padding:12px">
                    <span class="card-title" style="font-size:16px">
                        <i class="material-icons ${color}" style="font-size:20px">${icon}</i>
                        ${esc(r.source_description || '未知')}
                        <span class="badge ${color.replace('-text','')}" style="float:right;font-size:12px">${esc(r.status)}</span>
                    </span>
                    ${isListener ? renderListenerFields(r, idx, sourceId) : renderRuleFields(r)}
                </div>
            </div>`;
        }).join('');
    }

    function renderListenerFields(r, idx, sourceId) {
        const src = r.source_config || {};
        const tgt = r.target_config || {};
        const incompMap = {};
        (r.incompatible_items || []).forEach(i => { incompMap[i.config_name] = i; });

        const fields = [
            { name: '协议', srcKey: 'listener_protocol', tgtKey: 'Protocol', configName: 'listener_protocol' },
            { name: '端口', srcKey: 'listener_port', tgtKey: 'ListenerPort', configName: 'listener_port' },
            { name: '调度算法', srcKey: 'scheduler', tgtKey: 'Scheduler', configName: 'scheduler' },
            { name: '健康检查', srcKey: 'health_check', tgtKey: 'HealthCheck', configName: 'health_check',
              format: (s, t) => [s === 'on' ? '开启' : '关闭', t === 1 ? '开启' : '关闭'] },
            { name: '会话保持', srcKey: 'sticky_session', tgtKey: 'StickySessionType', configName: 'sticky_session_type',
              format: (s, t) => [s || 'off', t || '关闭'] },
            { name: '带宽', srcKey: 'bandwidth', tgtKey: 'Bandwidth', configName: 'bandwidth',
              format: (s, t) => [s === -1 ? '不限' : s + 'M', t ? t + 'M' : '不限'] },
        ];

        let html = '<table class="field-diff-table" style="font-size:13px;margin-top:8px"><thead><tr><th>配置项</th><th>阿里云</th><th></th><th>腾讯云</th><th></th></tr></thead><tbody>';

        for (const f of fields) {
            const srcVal = src[f.srcKey];
            const tgtVal = tgt[f.tgtKey];
            const incomp = incompMap[f.configName];
            let srcDisplay = srcVal ?? '-';
            let tgtDisplay = tgtVal ?? '-';

            if (f.format) {
                const [s, t] = f.format(srcVal, tgtVal);
                srcDisplay = s;
                tgtDisplay = t;
            }

            let statusIcon, statusClass, tgtCell;

            if (incomp) {
                if (incomp.recommendation && incomp.alternatives?.length) {
                    statusIcon = '\u26A0';
                    statusClass = 'field-warn';
                    const opts = incomp.alternatives.map(a =>
                        `<option value="${esc(a.value)}" ${a.value === incomp.recommendation ? 'selected' : ''}>${esc(a.label)}</option>`
                    ).join('');
                    tgtCell = `<select class="browser-default cd-alt-select" data-source-id="${esc(sourceId)}" data-item-idx="${idx}" data-field="${esc(f.configName)}" style="width:auto;font-size:12px">${opts}</select>`;
                } else {
                    statusIcon = '\u2717';
                    statusClass = 'field-error';
                    tgtCell = `<span class="red-text">${esc(incomp.reason)}</span>`;
                }
            } else {
                statusIcon = '\u2713';
                statusClass = 'field-ok';
                tgtCell = esc(String(tgtDisplay));
            }

            html += `<tr class="${statusClass}">
                <td>${esc(f.name)}</td>
                <td><code>${esc(String(srcDisplay))}</code></td>
                <td class="center-align grey-text">&rarr;</td>
                <td>${tgtCell}</td>
                <td class="center-align">${statusIcon}</td>
            </tr>`;
        }
        html += '</tbody></table>';

        // 转发规则平铺
        const rules = src.forwarding_rules || [];
        if (rules.length) {
            html += `<div style="margin-top:8px;padding-left:16px;border-left:3px solid #e0e0e0">
                <strong style="font-size:12px;color:#666">转发规则 (${rules.length})</strong>`;
            html += rules.map(rule => `
                <div style="font-size:12px;padding:4px 0;border-bottom:1px solid #f5f5f5">
                    <code>${esc(rule.domain || '*')}${esc(rule.url || rule.url_path || '/')}</code>
                    <span class="green-text" style="margin-left:8px">&#x2713;</span>
                </div>`).join('');
            html += '</div>';
        }
        return html;
    }

    function renderRuleFields(r) {
        const src = r.source_config || {};
        const tgt = r.target_config || {};
        return `<table class="field-diff-table" style="font-size:13px;margin-top:8px"><tbody>
            <tr class="field-ok"><td>域名</td><td><code>${esc(src.domain || '*')}</code></td><td class="center-align grey-text">&rarr;</td><td><code>${esc(tgt.Domain || '*')}</code></td><td class="center-align">&#x2713;</td></tr>
            <tr class="field-ok"><td>路径</td><td><code>${esc(src.url || src.url_path || '/')}</code></td><td class="center-align grey-text">&rarr;</td><td><code>${esc(tgt.Url || '/')}</code></td><td class="center-align">&#x2713;</td></tr>
        </tbody></table>`;
    }

    // ══════════════════════════════════════════════
    // 迁移计划表格
    // ══════════════════════════════════════════════

    function renderPlanTable(groups) {
        let allItems = [];
        let seq = 0;
        for (const [sourceId, group] of Object.entries(groups)) {
            const results = group.results || [];
            for (const r of results) {
                if (r.status === 'incompatible' && !r.target_config) continue;
                seq++;
                allItems.push({
                    seq,
                    sourceId,
                    targetId: group.targetId || '',
                    sourceName: group.sourceName || sourceId,
                    targetName: group.targetName || group.targetId,
                    type: r.source_type || 'listener',
                    desc: r.source_description || `迁移项 ${seq}`,
                    source: r.source_config,
                    target: r.target_config,
                    status: r.status,
                    selected: r.status !== 'incompatible',
                });
            }
        }

        if (!allItems.length) {
            document.getElementById('cd-plan-section').style.display = 'none';
            return;
        }

        const section = document.getElementById('cd-plan-section');
        section.style.display = 'block';

        const tableHtml = `
            <table class="striped highlight" style="font-size:13px">
                <thead><tr>
                    <th style="width:35px"><label><input type="checkbox" id="cd-selall" checked><span></span></label></th>
                    <th>#</th><th>实例</th><th>类型</th><th>描述</th><th>状态</th>
                </tr></thead><tbody>${renderPlanRows(allItems)}</tbody>
            </table>`;
        document.getElementById('cd-plan-table').innerHTML = tableHtml;

        // 全选
        document.getElementById('cd-selall')?.addEventListener('change', e => {
            document.querySelectorAll('.cd-chk').forEach(c => c.checked = e.target.checked);
        });
    }

    function renderPlanRows(items) {
        let lastSource = '';
        return items.map(item => {
            const instanceLabel = item.sourceId !== lastSource
                ? `<strong>${esc(item.sourceName)}</strong> &rarr; <span class="blue-text">${esc(item.targetName)}</span>`
                : '';
            lastSource = item.sourceId;
            return `<tr>
                <td><label><input type="checkbox" class="cd-chk" data-seq="${item.seq}" ${item.selected ? 'checked' : ''}><span></span></label></td>
                <td>${item.seq}</td>
                <td style="font-size:12px">${instanceLabel}</td>
                <td><span class="chip" style="font-size:11px">${esc(item.type)}</span></td>
                <td>${esc(item.desc)}</td>
                <td><span class="badge ${item.status === 'mapped' ? 'green' : item.status === 'partial' ? 'orange' : 'red'} white-text" style="float:none;font-size:11px">${esc(item.status)}</span></td>
            </tr>`;
        }).join('');
    }

    function getSelectedPlanItems() {
        const selected = [];
        document.querySelectorAll('.cd-chk:checked').forEach(c => {
            // 从已构建的 items 中查找（需要从 state 获取）
            const seq = parseInt(c.dataset.seq);
            const groups = state.get('mappingResults') || {};
            for (const [sid, grp] of Object.entries(groups)) {
                const results = grp.results || [];
                let localSeq = 0;
                for (const r of results) {
                    if (r.status === 'incompatible' && !r.target_config) continue;
                    localSeq++;
                    if (localSeq === seq) {
                        selected.push({
                            seq,
                            sourceId: sid,
                            targetId: grp.targetId || '',
                            sourceName: grp.sourceName || sid,
                            targetName: grp.targetName || grp.targetId,
                            type: r.source_type || 'listener',
                            desc: r.source_description || `迁移项 ${seq}`,
                            source: r.source_config,
                            target: r.target_config,
                            status: r.status,
                        });
                        break;
                    }
                }
            }
        });
        return selected;
    }

    // ══════════════════════════════════════════════
    // 二次确认
    // ══════════════════════════════════════════════

    function onConfirmExecute() {
        const selectedItems = getSelectedPlanItems();
        if (!selectedItems.length) {
            if (typeof M !== 'undefined') M.toast({ html: '请至少勾选一个迁移项', classes: 'orange' });
            return;
        }

        // 检查是否有未解决的目标端冲突
        const conflictPanel = document.getElementById('cd-target-conflict');
        if (conflictPanel && conflictPanel.style.display !== 'none') {
            if (typeof M !== 'undefined') M.toast({ html: '存在未解决的冲突，请先处理后再继续', classes: 'orange' });
            return;
        }

        // 统计信息
        const stats = computeStats(selectedItems);
        const statsEl = document.getElementById('cd-confirm-stats');
        if (statsEl) {
            statsEl.innerHTML = `
                <table class="striped" style="font-size:14px;margin:0">
                    <tbody>
                        <tr><td style="width:50%"><i class="material-icons tiny grey-text">dns</i> 涉及实例</td>
                            <td><strong>${stats.instanceCount}</strong> 对（源端 &rarr; 目标端）</td></tr>
                        <tr><td><i class="material-icons tiny grey-text">hearing</i> 创建监听器</td>
                            <td><strong>${stats.listenerCount}</strong> 个</td></tr>
                        <tr><td><i class="material-icons tiny grey-text">call_split</i> 创建转发规则</td>
                            <td><strong>${stats.ruleCount}</strong> 条</td></tr>
                        <tr><td><i class="material-icons tiny grey-text">check_circle</i> 完全映射</td>
                            <td><span class="green-text"><strong>${stats.mappedCount}</strong></span> 项</td></tr>
                        ${stats.partialCount ? `<tr><td><i class="material-icons tiny grey-text">warning</i> 需确认（部分映射）</td>
                            <td><span class="orange-text"><strong>${stats.partialCount}</strong></span> 项</td></tr>` : ''}
                        ${stats.incompatibleCount ? `<tr><td><i class="material-icons tiny grey-text">cancel</i> 不兼容（已选）</td>
                            <td><span class="red-text"><strong>${stats.incompatibleCount}</strong></span> 项</td></tr>` : ''}
                        <tr style="border-top:2px solid #e0e0e0"><td><strong>合计执行</strong></td>
                            <td><strong>${selectedItems.length}</strong> 项操作</td></tr>
                    </tbody>
                </table>`;
        }

        if (confirmModal) {
            confirmModal.open();
        } else {
            if (confirm(`即将执行 ${selectedItems.length} 项迁移操作（${stats.instanceCount} 对实例），确认开始？`)) {
                state.set('planItems', selectedItems);
                nav.completeStep('mapping');
            }
        }
    }

    function computeStats(items) {
        const instances = new Set();
        let listenerCount = 0, ruleCount = 0;
        let mappedCount = 0, partialCount = 0, incompatibleCount = 0;
        for (const item of items) {
            instances.add(item.sourceId);
            if (item.type === 'listener') listenerCount++;
            else if (item.type === 'forwarding_rule') ruleCount++;
            else listenerCount++;

            if (item.status === 'mapped') mappedCount++;
            else if (item.status === 'partial') partialCount++;
            else if (item.status === 'incompatible') incompatibleCount++;
            else mappedCount++;
        }
        return { instanceCount: instances.size, listenerCount, ruleCount, mappedCount, partialCount, incompatibleCount };
    }

    // ══════════════════════════════════════════════
    // 目标端冲突检测
    // ══════════════════════════════════════════════

    async function detectTargetConflicts(groups, instanceMappings) {
        // 按 targetInstanceId 分组收集所有 listeners
        const byTarget = {};
        for (const m of instanceMappings) {
            if (!byTarget[m.targetId]) byTarget[m.targetId] = [];
            byTarget[m.targetId].push({
                listeners: m.listeners || [],
                sourceName: m.sourceName,
                sourceId: m.sourceId,
            });
        }

        const allConflicts = [];

        // 并行检测每个目标实例
        await Promise.all(Object.entries(byTarget).map(async ([targetId, sources]) => {
            try {
                const allListeners = sources.flatMap(s =>
                    (s.listeners || []).map(l => ({
                        ...l,
                        description: `${s.sourceName}: ${(l.listener_protocol||'').toUpperCase()}:${l.listener_port}`,
                    }))
                );

                const res = await api.post('/api/mapping/detect-target-conflicts', {
                    targetInstanceId: targetId,
                    listeners: allListeners,
                });

                const conflicts = res.data?.conflicts || [];
                allConflicts.push(...conflicts);
            } catch (e) {
                console.warn(`目标端冲突检测失败 (${targetId}):`, e);
            }
        }));

        renderConflictPanel(allConflicts);
    }

    function renderConflictPanel(conflicts) {
        const panel = document.getElementById('cd-target-conflict');
        if (!panel) return;

        if (!conflicts.length) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        panel.innerHTML = `
            <div class="card-panel red lighten-5">
                <h6 class="red-text"><i class="material-icons left">warning</i>目标端监听器冲突 (${conflicts.length})</h6>
                <p style="font-size:12px;margin:4px 0">以下协议:端口组合在目标实例上已存在监听器。建议修改源端配置或选择其他目标实例。</p>
                <table class="striped" style="font-size:13px">
                    <thead><tr><th>协议:端口</th><th>源端描述</th><th>目标已有监听器ID</th><th>已有名称</th></tr></thead>
                    <tbody>${conflicts.map(c => `<tr>
                        <td><strong>${esc(c.protocol)}:${c.port}</strong></td>
                        <td>${esc(c.source_description)}</td>
                        <td><code>${esc(c.existing_listener_id || '-')}</code></td>
                        <td>${esc(c.existing_name || '-')}</td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>`;
    }

    function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
}

function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
