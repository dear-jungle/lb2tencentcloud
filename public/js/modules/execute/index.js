/**
 * 迁移执行步骤 — 对接后端 API，二次确认弹窗，进度轮询
 */
import { ApiService } from '/js/modules/core/api-service.js';
import { StateManager } from '/js/modules/core/state-manager.js';

const api = ApiService.getInstance();

export function render(container, nav) {
    const state = StateManager.getInstance();
    const planItems = state.get('planItems') || [];

    container.innerHTML = `
        <div class="row"><div class="col s12">
            <h5><i class="material-icons left">sync</i>执行迁移</h5>
            <p class="grey-text">共 ${planItems.length} 个迁移项待执行。</p>
        </div></div>
        <div class="row">
            <div class="col s12 m6">
                <label>失败处理模式</label>
                <p><label><input name="ex-mode" type="radio" value="pause" checked><span>失败暂停（推荐）</span></label></p>
                <p><label><input name="ex-mode" type="radio" value="continue"><span>失败继续</span></label></p>
            </div>
            <div class="col s12 m6 right-align" style="padding-top:16px">
                <button id="ex-start" class="btn-large waves-effect green"><i class="material-icons left">play_arrow</i>开始执行</button>
            </div>
        </div>
        <div class="row"><div class="col s12">
            <div class="progress" style="height:8px"><div id="ex-bar" class="determinate" style="width:0%"></div></div>
            <p id="ex-status" class="center-align grey-text">就绪 — ${planItems.length} 项待执行</p>
        </div></div>
        <div class="row"><div class="col s12">
            <div id="ex-log" class="log-panel" style="min-height:250px;max-height:400px;overflow-y:auto"></div>
        </div></div>
        <div class="row" style="margin-top:20px">
            <div class="col s6"><button id="ex-prev" class="btn-flat waves-effect"><i class="material-icons left">arrow_back</i>上一步</button></div>
            <div class="col s6 right-align"><button id="ex-next" class="btn-large waves-effect blue" disabled>查看报告<i class="material-icons right">arrow_forward</i></button></div>
        </div>

        <!-- 二次确认弹窗 (4.3) -->
        <div id="ex-confirm-modal" class="modal" style="max-width:600px;max-height:80vh">
            <div class="modal-content">
                <h5 id="ex-confirm-title"><i class="material-icons left orange-text">warning</i>操作确认</h5>
                <div id="ex-confirm-body"></div>
                <p style="margin-top:12px">
                    <label><input type="checkbox" id="ex-batch-cb"><span>批量确认后续同类操作</span></label>
                </p>
            </div>
            <div class="modal-footer">
                <a id="ex-confirm-skip" class="btn-flat waves-effect">跳过</a>
                <a id="ex-confirm-ok" class="btn waves-effect green">确认执行</a>
            </div>
        </div>

        <!-- 失败处理弹窗 (4.5) -->
        <div id="ex-fail-modal" class="modal" style="max-width:500px">
            <div class="modal-content">
                <h5><i class="material-icons left red-text">error</i>执行失败</h5>
                <p id="ex-fail-msg"></p>
            </div>
            <div class="modal-footer">
                <a id="ex-fail-skip" class="btn-flat waves-effect">跳过此项</a>
                <a id="ex-fail-stop" class="btn-flat waves-effect red-text">终止迁移</a>
                <a id="ex-fail-retry" class="btn waves-effect orange">重试</a>
            </div>
        </div>`;

    // 初始化 Materialize Modal
    const confirmModalEl = document.getElementById('ex-confirm-modal');
    const failModalEl = document.getElementById('ex-fail-modal');
    let confirmModal, failModal;
    if (typeof M !== 'undefined') {
        confirmModal = M.Modal.init(confirmModalEl, { dismissible: false });
        failModal = M.Modal.init(failModalEl, { dismissible: false });
    }

    // 导航按钮
    document.getElementById('ex-prev')?.addEventListener('click', () => nav.goTo('plan'));
    document.getElementById('ex-next')?.addEventListener('click', () => nav.completeStep('execute'));

    let taskId = null;
    let pollTimer = null;
    const stepConfirm = state.get('stepConfirm') || false;  // 是否逐项确认

    // ─── 4.1 开始执行 ──────────────────────────────────────────

    document.getElementById('ex-start')?.addEventListener('click', async () => {
        const btn = document.getElementById('ex-start');
        btn.disabled = true;
        btn.textContent = '准备中...';

        const failMode = document.querySelector('input[name="ex-mode"]:checked')?.value || 'pause';

        try {
            // 构建 plan items 数据
            const apiPlanItems = buildPlanItemsForApi(planItems);
            if (!apiPlanItems.length) {
                appendLog('error', '无有效迁移项');
                btn.disabled = false;
                btn.textContent = '开始执行';
                return;
            }

            // 创建任务
            appendLog('info', '正在创建迁移任务...');
            const createResp = await api.post('/api/migration/tasks', {
                planItems: apiPlanItems,
                failureMode: failMode,
            });
            taskId = createResp.data.task_id;
            appendLog('info', `任务创建成功: ${createResp.data.task_no} (ID: ${taskId})`);

            // 启动执行（传递 auto_confirm）
            const autoConfirm = !stepConfirm;
            appendLog('info', `启动迁移执行（${autoConfirm ? '自动执行' : '逐项确认'}）...`);
            await api.post(`/api/migration/tasks/${taskId}/execute`, {
                auto_confirm: autoConfirm,
            });
            appendLog('info', '迁移已启动，轮询进度中...');

            btn.textContent = '执行中...';

            // 4.2 开始轮询
            startPolling();

        } catch (e) {
            appendLog('error', `启动失败: ${e.message || e}`);
            btn.disabled = false;
            btn.textContent = '开始执行';
        }
    });

    // ─── 4.2 进度轮询 ──────────────────────────────────────────

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(async () => {
            if (!taskId) return;
            try {
                const resp = await api.get(`/api/migration/tasks/${taskId}/progress`);
                const d = resp.data;
                updateProgress(d);

                // 4.3 检测待确认项
                if (d.pending_confirm) {
                    showConfirmModal(d.pending_confirm);
                }

                // 4.5 检测失败暂停
                if (d.status === 'paused') {
                    const failedItem = d.items?.find(i => i.status === 'failed');
                    if (failedItem) {
                        showFailModal(failedItem);
                    }
                }

                // 完成或取消时停止轮询
                if (['completed', 'failed', 'cancelled'].includes(d.status)) {
                    stopPolling();
                    onComplete(d);
                }
            } catch (e) {
                appendLog('warn', `轮询异常: ${e.message || e}`);
            }
        }, 2000);
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function updateProgress(d) {
        const pct = d.progress || 0;
        const bar = document.getElementById('ex-bar');
        const status = document.getElementById('ex-status');
        if (bar) bar.style.width = pct + '%';

        const done = d.success_count + d.failed_count + d.skipped_count;
        if (status) {
            if (d.status === 'waiting_confirm' || d.pending_confirm) {
                status.textContent = `等待确认 — ${done}/${d.total_items} 已处理 (${pct}%)`;
                status.className = 'center-align orange-text';
            } else if (d.status === 'paused') {
                status.textContent = `已暂停 — ${done}/${d.total_items} 已处理`;
                status.className = 'center-align red-text';
            } else {
                status.textContent = `执行中 ${done}/${d.total_items} (${pct}%)`;
                status.className = 'center-align grey-text';
            }
        }

        // 更新日志
        if (d.logs?.length) {
            const logPanel = document.getElementById('ex-log');
            if (logPanel) {
                logPanel.innerHTML = '';
                d.logs.forEach(log => {
                    const cls = { error: 'log-error', warn: 'log-warn', info: 'log-info' }[log.level] || 'log-info';
                    const t = log.time ? new Date(log.time).toLocaleTimeString() : '';
                    logPanel.insertAdjacentHTML('beforeend',
                        `<div class="${cls}">[${t}] ${esc(log.message)}</div>`);
                });
                logPanel.scrollTop = logPanel.scrollHeight;
            }
        }
    }

    // ─── 4.3 二次确认弹窗 ──────────────────────────────────────

    function showConfirmModal(pendingItem) {
        if (!confirmModal || confirmModalEl.classList.contains('open')) return;

        const title = document.getElementById('ex-confirm-title');
        const body = document.getElementById('ex-confirm-body');
        if (!body) return;

        const opDesc = pendingItem.operation_desc || pendingItem.operation_type;
        const params = pendingItem.request_params || {};
        const hasConflict = pendingItem.has_conflict;

        title.innerHTML = `<i class="material-icons left ${hasConflict ? 'red-text' : 'orange-text'}">warning</i>` +
            (hasConflict ? '冲突警告 — 需要确认' : '操作确认');

        let conflictHtml = '';
        if (hasConflict && pendingItem.conflict_detail?.existing_listener) {
            const el = pendingItem.conflict_detail.existing_listener;
            conflictHtml = `
                <div class="card-panel red lighten-5" style="margin:8px 0">
                    <strong>⚠ 端口冲突</strong>：目标实例已有
                    <code>${el.Protocol}:${el.Port}</code> 监听器
                    (${el.ListenerId})
                </div>`;
        }

        const paramRows = Object.entries(params)
            .filter(([k]) => !k.startsWith('_'))
            .map(([k, v]) => `<tr><td>${esc(k)}</td><td><code>${esc(String(v))}</code></td></tr>`)
            .join('');

        body.innerHTML = `
            <p><strong>操作类型：</strong>${esc(pendingItem.operation_type)}</p>
            <p><strong>描述：</strong>${esc(opDesc)}</p>
            <p><strong>目标实例：</strong><code>${esc(pendingItem.target_instance_id)}</code></p>
            ${conflictHtml}
            <table class="striped" style="font-size:13px">
                <thead><tr><th>参数</th><th>值</th></tr></thead>
                <tbody>${paramRows}</tbody>
            </table>`;

        // 重置 batch checkbox
        const batchCb = document.getElementById('ex-batch-cb');
        if (batchCb) batchCb.checked = false;

        // 绑定按钮
        const okBtn = document.getElementById('ex-confirm-ok');
        const skipBtn = document.getElementById('ex-confirm-skip');

        const handleConfirm = async (action) => {
            okBtn.removeEventListener('click', onOk);
            skipBtn.removeEventListener('click', onSkip);
            confirmModal.close();

            const batch = batchCb?.checked;

            try {
                if (batch) {
                    // 4.4 批量确认
                    await api.post(`/api/migration/tasks/${taskId}/batch-confirm`, {
                        action,
                        operation_type: pendingItem.operation_type,
                    });
                    appendLog('info', `批量${action === 'confirm' ? '确认' : '跳过'}同类操作`);
                } else {
                    await api.post(`/api/migration/tasks/${taskId}/confirm`, {
                        item_id: pendingItem.item_id,
                        action,
                    });
                }
            } catch (e) {
                appendLog('error', `确认操作失败: ${e.message || e}`);
            }
        };

        const onOk = () => handleConfirm('confirm');
        const onSkip = () => handleConfirm('skip');

        okBtn.addEventListener('click', onOk);
        skipBtn.addEventListener('click', onSkip);

        confirmModal.open();
    }

    // ─── 4.5 失败处理弹窗 ──────────────────────────────────────

    function showFailModal(failedItem) {
        if (!failModal || failModalEl.classList.contains('open')) return;

        const msg = document.getElementById('ex-fail-msg');
        if (msg) {
            msg.innerHTML = `
                <strong>${esc(failedItem.operation_desc)}</strong><br>
                <span class="red-text">${esc(failedItem.error_message || '未知错误')}</span>`;
        }

        const retryBtn = document.getElementById('ex-fail-retry');
        const skipBtn = document.getElementById('ex-fail-skip');
        const stopBtn = document.getElementById('ex-fail-stop');

        const cleanup = () => {
            retryBtn.removeEventListener('click', onRetry);
            skipBtn.removeEventListener('click', onSkip);
            stopBtn.removeEventListener('click', onStop);
            failModal.close();
        };

        const onRetry = async () => {
            cleanup();
            try {
                // 跳过当前失败项（重试 = resume 继续）
                await api.post(`/api/migration/tasks/${taskId}/resume`);
                appendLog('info', '已恢复执行');
            } catch (e) {
                appendLog('error', `恢复失败: ${e.message}`);
            }
        };

        const onSkip = async () => {
            cleanup();
            try {
                await api.post(`/api/migration/tasks/${taskId}/confirm`, {
                    item_id: failedItem.id,
                    action: 'skip',
                });
                await api.post(`/api/migration/tasks/${taskId}/resume`);
                appendLog('info', '已跳过失败项并继续');
            } catch (e) {
                appendLog('error', `操作失败: ${e.message}`);
            }
        };

        const onStop = async () => {
            cleanup();
            try {
                await api.post(`/api/migration/tasks/${taskId}/pause`);
                stopPolling();
                appendLog('error', '用户终止迁移');
                document.getElementById('ex-status').textContent = '已终止';
                document.getElementById('ex-start').disabled = false;
                document.getElementById('ex-start').textContent = '重新开始';
            } catch (e) {
                appendLog('error', `终止失败: ${e.message}`);
            }
        };

        retryBtn.addEventListener('click', onRetry);
        skipBtn.addEventListener('click', onSkip);
        stopBtn.addEventListener('click', onStop);

        failModal.open();
    }

    // ─── 执行完成 ──────────────────────────────────────────────

    function onComplete(d) {
        document.getElementById('ex-bar').style.width = '100%';
        const status = document.getElementById('ex-status');
        status.textContent = `完成 — 成功 ${d.success_count}, 失败 ${d.failed_count}, 跳过 ${d.skipped_count}`;
        status.className = d.failed_count > 0 ? 'center-align orange-text' : 'center-align green-text';

        appendLog('info', '\n===== 执行完成 =====');
        appendLog('info', `总计: ${d.total_items}, 成功: ${d.success_count}, ` +
            `失败: ${d.failed_count}, 跳过: ${d.skipped_count}`);

        // 保存报告数据
        const reportItems = (d.items || []).map(item => ({
            desc: item.operation_desc,
            status: item.status,
            result: item.status,
            error: item.error_message || '',
            operation_type: item.operation_type,
        }));

        state.set('executionStatus', {
            total: d.total_items,
            success: d.success_count,
            failed: d.failed_count,
            skipped: d.skipped_count,
            items: reportItems,
            taskId: taskId,
        });

        // 启用下一步
        const nextBtn = document.getElementById('ex-next');
        if (nextBtn) nextBtn.disabled = false;
    }

    // ─── 辅助函数 ──────────────────────────────────────────────

    function buildPlanItemsForApi(items) {
        return items.filter(item => item.status !== 'incompatible' || item.target).map(item => {
            // 根据 source_type 判断操作类型
            const opType = item.type === 'forwarding_rule' ? 'create_rule' : 'create_listener';

            return {
                operation_type: item.operation_type || opType,
                operation_desc: item.desc || '',
                target_instance_id: item.targetId || '',
                request_params: item.target || {},
                mapping_id: item.mappingId || 0,
            };
        });
    }
}

function appendLog(level, msg) {
    const panel = document.getElementById('ex-log');
    if (!panel) return;
    const t = new Date().toLocaleTimeString();
    const cls = { error: 'log-error', warn: 'log-warn', success: 'log-success', info: 'log-info' }[level] || 'log-info';
    panel.insertAdjacentHTML('beforeend', `<div class="${cls}">[${t}] ${msg}</div>`);
    panel.scrollTop = panel.scrollHeight;
}

function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
