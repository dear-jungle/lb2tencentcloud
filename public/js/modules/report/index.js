/**
 * 步骤5 — 迁移报告管理页：历史报告列表 + 详情查看 + 导出/删除
 *
 * 如果有当前执行的 executionStatus（内存态），优先展示；
 * 否则展示持久化的历史报告列表
 */
import { StateManager } from '/js/modules/core/state-manager.js';
import { ApiService } from '/js/modules/core/api-service.js';

export function render(container, nav) {
    const state = StateManager.getInstance();
    const api = ApiService.getInstance();

    // 检查是否有当前执行结果（内存态）
    const execStatus = state.get('executionStatus');

    container.innerHTML = `
        <div class="row"><div class="col s12">
            <h5><i class="material-icons left">assessment</i>迁移报告</h5>
        </div></div>

        <!-- 当前执行结果区（如果有） -->
        <div id="rpt-current" style="display:none">
            <div class="card-panel teal lighten-4" style="margin-bottom:12px">
                <strong><i class="material-icons tiny left">schedule</i>本次执行结果</strong>
            </div>
        </div>

        <!-- 历史报告列表区 -->
        <div id="rpt-history">
            <div class="row">
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number blue-text" id="rpt-total-reports">-</span><div class="stat-label">总报告数</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number green-text" id="rpt-total-success">-</span><div class="stat-label">累计成功项</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number red-text" id="rpt-total-failed">-</span><div class="stat-label">累计失败项</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number grey-text" id="rpt-total-skipped">-</span><div class="stat-label">累计跳过项</div></div></div>
            </div>
            <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center">
                <h6>历史报告列表</h6>
                <div>
                    <button id="rpt-batch-dl" class="btn-flat waves-effect blue-text" style="display:none"><i class="material-icons left">archive</i>批量下载</button>
                    <button id="rpt-refresh" class="btn-flat waves-effect"><i class="material-icons left">refresh</i>刷新</button>
                </div>
            </div>
            <div id="rpt-loading" class="center-align" style="padding:30px"><div class="preloader-wrapper small active"><div class="spinner-layer spinner-blue-only"><div class="circle-clipper left"><div class="circle"></div></div><div class="gap-patch"><div class="circle"></div></div><div class="circle-clipper right"><div class="circle"></div></div></div></div></div>
            <div id="rpt-list" style="display:none"></div>
        </div>

        <div class="row" style="margin-top:20px"><div class="col s12 center-align">
            <button id="rpt-new" class="btn-flat waves-effect blue-text"><i class="material-icons left">add</i>新建迁移</button>
        </div></div>

        <!-- 报告详情弹窗 -->
        <div id="rpt-detail-modal" class="modal modal-fixed-footer" style="max-width:800px">
            <div class="modal-content">
                <h5 id="rpt-detail-title">报告详情</h5>
                <div id="rpt-detail-stats" style="margin:12px 0"></div>
                <ul class="tabs">
                    <li class="tab col s3"><a href="#dt-all" class="active">全部</a></li>
                    <li class="tab col s3"><a href="#dt-ok">成功</a></li>
                    <li class="tab col s3"><a href="#dt-fail">失败/跳过</a></li>
                </ul>
                <div id="dt-all" class="col s12"></div>
                <div id="dt-ok" class="col s12"></div>
                <div id="dt-fail" class="col s12"></div>
            </div>
            <div class="modal-footer">
                <a href="#!" id="rpt-detail-download" class="btn waves-effect green darken-1"><i class="material-icons left">file_download</i>下载 Excel</a>
                <a href="#!" class="modal-close waves-effect btn-flat">关闭</a>
            </div>
        </div>`;

    let currentDetailId = null;

    // ── 当前执行结果（内存态）─────────────────────
    if (execStatus && (execStatus.total || execStatus.items?.length)) {
        renderCurrentResult(execStatus);
    }

    // ── 加载历史报告列表 ────────────────────────
    loadReportList();

    document.getElementById('rpt-refresh')?.addEventListener('click', loadReportList);
    document.getElementById('rpt-new')?.addEventListener('click', () => {
        state.set('sourceInstances', []); state.set('sourceConfigs', {});
        state.set('instanceMappings', []); state.set('mappingResults', {});
        state.set('planItems', []); state.set('executionStatus', null);
        nav.goTo('credential');
    });

    // 批量下载
    document.getElementById('rpt-batch-dl')?.addEventListener('click', async () => {
        const selected = [];
        document.querySelectorAll('.rpt-cb:checked').forEach(cb => selected.push(parseInt(cb.value));
        if (!selected.length) {
            M.toast({html: '请先勾选要下载的报告', classes: 'orange'}); return;
        }
        try {
            await api.post('/api/report/batch-download', { ids: selected });
            M.toast({html: 'ZIP 文件已开始下载', classes: 'green'});
        } catch(e) {
            M.toast({html: '批量下载失败: ' + e.message, classes: 'red'});
        }
    });

    // 详情弹窗
    if (typeof M !== 'undefined') {
        M.Modal.init(document.querySelectorAll('.modal'));
    }

    document.getElementById('rpt-detail-download')?.addEventListener('click', async () => {
        if (!currentDetailId) return;
        try {
            window.location.href = `/api/report/reports/${currentDetailId}/download?format=excel`;
        } catch(e) {
            M.toast({html: '下载失败: ' + e.message, classes: 'red'});
        }
    });

    // ══════════════════════════════════════════════

    function renderCurrentResult(status) {
        const el = document.getElementById('rpt-current');
        el.style.display = 'block';
        const total = status.total || 0;
        const success = status.success || 0;
        const failed = status.failed || 0;
        const skipped = status.skipped || 0;
        el.innerHTML += `
            <div class="row">
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number blue-text">${total}</span><div class="stat-label">总计</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number green-text">${success}</span><div class="stat-label">成功</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number red-text">${failed}</span><div class="stat-label">失败</div></div></div>
                <div class="col s3"><div class="card-panel stat-card"><span class="stat-number grey-text">${skipped}</span><div class="stat-label">跳过</div></div></div>
            </div>
            <table class="striped" style="font-size:13px;margin-top:8px">
                <thead><tr><th>#</th><th>描述</th><th>结果</th><th>详情</th></tr></thead>
                <tbody>${(status.items || []).map((it, i) => `
                    <tr>
                        <td>${i+1}</td><td>${esc(it.desc)}</td>
                        <td><span class="badge ${it.result === 'success' ? 'green' : it.result === 'skipped' ? 'grey' : 'red'} white-text" style="float:none">${it.result === 'success' ? '成功' : it.result === 'skipped' ? '跳过' : '失败'}</span></td>
                        <td>${it.error ? '<span class="red-text">' + esc(it.error) + '</span>' : '-'}</td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
    }

    async function loadReportList() {
        const loadingEl = document.getElementById('rpt-loading');
        const listEl = document.getElementById('rpt-list');
        const batchBtn = document.getElementById('rpt-batch-dl');

        try {
            const res = await api.get('/api/report/reports?page=1&page_size=50');
            const data = res.data || {};
            const items = data.items || [];

            loadingEl.style.display = 'none';
            listEl.style.display = items.length ? 'block' : 'none';
            batchBtn.style.display = items.length > 1 ? 'inline-block' : 'none';

            // 统计汇总
            let tSuccess = 0, tFailed = 0, tSkipped = 0;
            for (const r of items) {
                tSuccess += r.success_count || 0;
                tFailed += r.failed_count || 0;
                tSkipped += r.skipped_count || 0;
            }
            setText('rpt-total-reports', data.total || 0);
            setText('rpt-total-success', tSuccess);
            setText('rpt-total-failed', tFailed);
            setText('rpt-total-skipped', tSkipped);

            if (!items.length) {
                listEl.innerHTML = '<p class="grey-text center-align" style="padding:20px">暂无历史迁移报告。完成一次迁移后将自动生成。</p>';
                return;
            }

            listEl.innerHTML = `
                <table class="striped highlight" style="font-size:13px">
                    <thead><tr>
                        <th style="width:35px"><label><input type="checkbox" id="rpt-selall"><span></span></label></th>
                        <th>ID</th><th>时间</th><th>摘要</th><th>统计</th><th style="width:200px">操作</th>
                    </tr></thead>
                    <tbody>${items.map(r => `
                        <tr>
                            <td><label><input type="checkbox" class="rpt-cb" value="${r.id}"><span></span></label></td>
                            <td><code>${r.id}</code></td>
                            <td>${esc((r.created_at || '').replace('T', ' ').slice(0, 16))}</td>
                            <td>${esc(r.report_summary || '-')}</td>
                            <td>
                                <span class="green-text">${r.success_count||0}&#x2713;</span>
                                ${r.failed_count > 0 ? `<span class="red-text">${r.failed_count}&#x2717;</span>` : ''}
                                ${r.skipped_count > 0 ? `<span class="grey-text">${r.skipped_count}&#x21B8;</span>` : ''}
                            </td>
                            <td>
                                <button class="btn-small waves-effect blue rpt-view-btn" data-id="${r.id}">详情</button>
                                <button class="btn-small waves-effect green darken-1 rpt-dl-btn" data-id="${r.id}" style="margin-left:4px">Excel</button>
                                <button class="btn-small waves-effect red lighten-3 rpt-del-btn" data-id="${r.id}" style="margin-left:4px">删除</button>
                            </td>
                        </tr>`).join('')}
                </tbody></table>`;

            // 全选
            document.getElementById('rpt-selall')?.addEventListener('change', e => {
                listEl.querySelectorAll('.rpt-cb').forEach(c => c.checked = e.target.checked);
                batchBtn.style.display = listEl.querySelectorAll('.rpt-cb:checked').length > 1 ? 'inline-block' : 'none';
            });
            listEl.addEventListener('change', e => {
                if (e.target.classList.contains('rpt-cb')) {
                    batchBtn.style.display = listEl.querySelectorAll('.rpt-cb:checked').length > 1 ? 'inline-block' : 'none';
                }
            });

            // 详情按钮
            listEl.querySelectorAll('.rpt-view-btn')?.forEach(btn => {
                btn.addEventListener('click', () => openReportDetail(parseInt(btn.dataset.id)));
            });
            // 下载按钮
            listEl.querySelectorAll('.rpt-dl-btn')?.forEach(btn => {
                btn.addEventListener('click', () => {
                    window.location.href = `/api/report/reports/${btn.dataset.id}/download?format=excel`;
                });
            });
            // 删除按钮
            listEl.querySelectorAll('.rpt-del-btn')?.forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (!confirm(`确定删除报告 #${btn.dataset.id}?`)) return;
                    try {
                        await api.request('DELETE', `/api/report/reports/${btn.dataset.id}`);
                        M.toast({html: '报告已删除', classes: 'teal'});
                        loadReportList();
                    } catch(e) {
                        M.toast({html: '删除失败: ' + e.message, classes: 'red'});
                    }
                });
            });

        } catch(e) {
            loadingEl.innerHTML = `<div class="card-panel red lighten-4">加载失败: ${esc(e.message)}</div>`;
        }
    }

    async function openReportDetail(reportId) {
        currentDetailId = reportId;
        try {
            const res = await api.get(`/api/report/reports/${reportId}`);
            const report = res.data || {};

            document.getElementById('rpt-detail-title').textContent =
                `报告 #${reportId} — ${report.report_summary || ''}`;

            const details = report.details || [];
            const successItems = details.filter(d => d.category === 'success');
            const failItems = details.filter(d => d.category !== 'success');

            // 统计
            document.getElementById('rpt-detail-stats').innerHTML = `
                <div style="display:flex;gap:16px;flex-wrap:wrap">
                    <span><strong>总计:</strong> ${details.length} 项</span>
                    <span class="green-text"><strong>成功:</strong> ${successItems.length}</span>
                    <span class="red-text"><strong>失败:</strong> ${(details.filter(d=>d.category==='failed')).length}</span>
                    <span class="grey-text"><strong>跳过:</strong> {(details.filter(d=>d.category==='skipped')).length}</span>
                </div>`;

            document.getElementById('dt-all').innerHTML = renderDetailTable(details);
            document.getElementById('dt-ok').innerHTML = renderDetailTable(successItems);
            document.getElementById('dt-fail').innerHTML = renderDetailTable(failItems);

            setTimeout(() => M.Tabs.init(document.querySelectorAll('#rpt-detail-modal .tabs')), 100);

            const modal = document.getElementById('rpt-detail-modal');
            if (modal && typeof M !== 'undefined') {
                M.Modal.getInstance(modal)?.open();
            }
        } catch(e) {
            M.toast({html: '加载报告详情失败: ' + e.message, classes: 'red'});
        }
    }

    function renderDetailTable(items) {
        if (!items.length) return '<p class="grey-text center-align" style="padding:20px">无数据</p>';
        return `<table class="striped" style="font-size:12px">
            <thead><tr><th>#</th><th>类型</th><th>描述</th><th>状态</th><th>耗时</th><th>错误</th></tr></thead>
            <tbody>${items.map((d, i) => `
                <tr>
                    <td>${i+1}</td>
                    <td><code>${esc(d.operation_type)}</code></td>
                    <td>${esc(d.operation_desc)}</td>
                    <td><span class="badge ${d.category === 'success' ? 'green' : d.category === 'failed' ? 'red' : 'grey'} white-text" style="float:none;font-size:10px">${d.category}</span></td>
                    <td>${(d.duration_ms || 0) + 'ms'}</td>
                    <td class="red-text" style="font-size:11px">${esc(d.error_message || d.incompatible_reason || '')}</td>
                </tr>`).join('')}
            </tbody></table>`;
    }

    function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
}

function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
