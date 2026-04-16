"""
真实数据全流程测试 v3
- 步骤1: 凭证配置（真实 AK/SK）
- 步骤2: 实例关联（测试页面加载 + 源端实例展示，腾讯云无实例时验证提示）
- 步骤3+: 通过 API 直接测试映射/计划/执行/报告流程
- 严格只读：不创建/修改任何云端资源
"""
import time, json, requests, os
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:10041"

# 从环境变量读取凭证（运行测试前需配置 .env 或设置环境变量）
import os as _os

ALI_AK = _os.getenv('TEST_ALI_AK', '')
ALI_SK = _os.getenv('TEST_ALI_SK', '')
TC_SID = _os.getenv('TEST_TC_SID', '')
TC_SK  = _os.getenv('TEST_TC_SK', '')


def log(step, msg):
    print(f"[步骤{step}] {msg}")


def test_api_flow():
    """后端 API 全流程测试（真实数据）"""
    session = requests.Session()
    results = {}

    print("\n" + "="*60)
    print("后端 API 测试")
    print("="*60)

    # 1. 验证凭证
    r = session.post(BASE_URL + '/api/credentials/aliyun/verify',
                     json={"access_key_id": ALI_AK, "access_key_secret": ALI_SK})
    ok = r.json()['success']
    results['凭证-阿里云'] = '✓' if ok else '✗'
    print(f"[API] 阿里云凭证: {'✓' if ok else '✗'}")

    r = session.post(BASE_URL + '/api/credentials/tencent/verify',
                     json={"secret_id": TC_SID, "secret_key": TC_SK})
    ok = r.json()['success']
    results['凭证-腾讯云'] = '✓' if ok else '✗'
    print(f"[API] 腾讯云凭证: {'✓' if ok else '✗'}")

    # 2. 拉取实例列表
    r = session.get(BASE_URL + '/api/aliyun/clb/instances', params={"region": "cn-guangzhou"})
    d = r.json()
    instances = d['data']['instances']
    results['阿里云实例列表'] = f'✓ ({len(instances)}个)' if d['success'] else '✗'
    print(f"[API] 阿里云广州实例: {len(instances)} 个")

    r = session.get(BASE_URL + '/api/tencent/clb/instances', params={"region": "ap-guangzhou"})
    d = r.json()
    tc_insts = d['data']['instances'] if d['success'] else []
    results['腾讯云实例列表'] = f'✓ ({len(tc_insts)}个)' if d['success'] else '✗'
    print(f"[API] 腾讯云广州实例: {len(tc_insts)} 个（注：0个为正常，测试账号无实例）")

    # 3. 拉取阿里云配置（只读）
    ali_configs = {}
    for inst in instances[:3]:
        iid = inst['instance_id']
        r = session.get(BASE_URL + f'/api/aliyun/clb/instances/{iid}/config',
                        params={"region": "cn-guangzhou"})
        d = r.json()
        if d['success']:
            ali_configs[iid] = {
                'listeners': d['data']['listeners'],
                'instance': d['data']['instance'],
            }
    results['阿里云配置拉取'] = f'✓ ({len(ali_configs)}个)' if ali_configs else '✗'
    print(f"[API] 阿里云配置拉取: {len(ali_configs)} 个实例")
    for iid, cfg in ali_configs.items():
        ls = cfg['listeners']
        print(f"  {iid}: {len(ls)} 个监听器")
        for l in ls:
            print(f"    {l.get('listener_protocol','').upper()}:{l.get('listener_port')} rules={len(l.get('forwarding_rules',[]))}")

    # 4. 执行映射（使用 placeholder 目标 ID，只读测试）
    if instances and ali_configs:
        instance_mappings = []
        for inst in instances:
            iid = inst['instance_id']
            if iid in ali_configs:
                instance_mappings.append({
                    "sourceId": iid,
                    "targetId": "lb-test-readonly-target",  # 占位，只读测试
                    "sourceName": inst['instance_name'] or iid,
                    "targetName": "测试目标实例（只读）",
                    "listeners": ali_configs[iid]['listeners'],
                })

        r = session.post(BASE_URL + '/api/mapping/execute-by-instance',
                         json={"instanceMappings": instance_mappings})
        d = r.json()
        if d['success']:
            summary = d['data']['summary']
            groups = d['data']['groups']
            results['按实例映射'] = f'✓ (total={summary["total"]})'
            print(f"[API] 按实例映射: {summary}")
            for sid, group in groups.items():
                s = group['summary']
                print(f"  {group['sourceName']} → {group['targetName']}")
                print(f"    mapped={s['mapped']}, partial={s['partial']}, incompatible={s['incompatible']}")
                for res in group['results'][:5]:
                    incomp = ' '.join([f"[{i['config_name']}:rec={i.get('recommendation','')} alts={len(i.get('alternatives',[]))}]"
                                      for i in res.get('incompatible_items', [])])
                    print(f"    {res['source_description']}: {res['status']} {incomp}")
        else:
            results['按实例映射'] = '✗ ' + d.get('message', '')
            print(f"[API] 映射失败: {d.get('message')}")

    # 5. 传统映射接口（向后兼容）
    if ali_configs:
        all_listeners = []
        for cfg in ali_configs.values():
            all_listeners.extend(cfg['listeners'])
        r = session.post(BASE_URL + '/api/mapping/tasks/0/execute',
                         json={"listeners": all_listeners})
        d = r.json()
        results['传统映射'] = f'✓ (total={d["data"]["summary"]["total"]})' if d['success'] else '✗'
        print(f"[API] 传统映射接口(兼容): success={d['success']} summary={d['data']['summary'] if d['success'] else d.get('message')}")

    # 6. .env 加载
    r = session.post(BASE_URL + '/api/credentials/load-env')
    d = r.json()
    results['.env加载'] = '✓' if d['success'] else '✗'
    ak = d['data'].get('aliyun_ak', '')
    print(f"[API] .env 加载: {d.get('message')} AK前10={ak[:10] if ak else '无'}...")

    return results, ali_configs, instances


def test_playwright_flow(ali_configs, instances):
    """Playwright 前端测试（步骤1+步骤2 UI 验证）"""
    print("\n" + "="*60)
    print("前端 Playwright 测试")
    print("="*60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)

        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        time.sleep(3)

        # ===== 步骤1 =====
        log(1, "凭证配置...")
        if page.locator("#c-aliyun-ak").count() == 0:
            log(1, "❌ 表单不存在")
            browser.close()
            return {"步骤1": "✗ 表单不存在"}

        page.click("#c-btn-load-env")
        time.sleep(2)
        page.select_option("#c-aliyun-region", "cn-guangzhou")
        page.select_option("#c-tencent-region", "ap-guangzhou")

        page.click("#c-btn-verify-ali")
        time.sleep(7)
        ali_ok = "check_circle" in page.locator("#c-ali-status").inner_html()
        page.click("#c-btn-verify-tc")
        time.sleep(7)
        tc_ok = "check_circle" in page.locator("#c-tc-status").inner_html()
        log(1, f"阿里云: {'✓' if ali_ok else '✗'}, 腾讯云: {'✓' if tc_ok else '✗'}")

        page.screenshot(path="tests/screenshots/v3_step1.png")

        if not ali_ok or not tc_ok:
            browser.close()
            return {"步骤1": f"✗ 验证失败 ali={ali_ok} tc={tc_ok}"}

        next_btn = page.locator("#c-btn-next")
        btn_disabled_js = page.evaluate("() => document.getElementById('c-btn-next').disabled")
        log(1, f"下一步按钮 disabled={btn_disabled_js}")

        if btn_disabled_js:
            log(1, "❌ 下一步禁用（可能地域未选择）")
            browser.close()
            return {"步骤1": "✗ 下一步禁用"}

        next_btn.click()
        time.sleep(6)
        page.screenshot(path="tests/screenshots/v3_step2_init.png")
        log(1, "✓ 步骤1完成 → 步骤2")

        # ===== 步骤2: 实例关联 =====
        log(2, "实例关联页面检查...")
        time.sleep(3)
        page.screenshot(path="tests/screenshots/v3_step2_loaded.png")

        content = page.locator("#step-content").inner_text()

        if "功能开发中" in content or "渲染错误" in content:
            log(2, "❌ 页面加载失败")
            for e in errors: log(2, f"  {e}")
            browser.close()
            return {"步骤2": "✗ 渲染失败"}

        # 检查标题
        h5_text = page.locator("h5").first.text_content()
        log(2, f"页面标题: {h5_text}")

        # 检查源端实例数
        cbs = page.locator(".ia-src-cb")
        src_count = cbs.count()
        log(2, f"源端实例数: {src_count}")

        if src_count != len(instances):
            log(2, f"⚠ 期望 {len(instances)} 个，实际 {src_count} 个")

        # 检查实例内容
        for i in range(src_count):
            val = cbs.nth(i).get_attribute("value")
            name = cbs.nth(i).get_attribute("data-name")
            log(2, f"  实例{i+1}: {val} ({name})")

        # 全选勾选
        page.locator("#ia-selall").check(force=True)
        time.sleep(1)
        page.screenshot(path="tests/screenshots/v3_step2_selected.png")

        # 检查右栏
        tgt_text = page.locator("#ia-tgt-info").inner_text()
        log(2, f"右栏内容: {tgt_text[:150]}")

        # 检查腾讯云无实例时的友好提示
        if "暂无 CLB 实例" in tgt_text or "没有已有 CLB 实例" in tgt_text:
            log(2, "✓ 正确显示'目标端暂无实例'友好提示")
            step2_result = "✓ (目标端无实例，友好提示正常)"
        elif "选择目标实例" in tgt_text:
            log(2, "✓ 下拉框显示（有目标端实例）")
            step2_result = "✓ (下拉框正常)"
        else:
            step2_result = f"⚠ 未知状态: {tgt_text[:50]}"

        # 检查下一步按钮状态（JS 级别）
        btn_disabled = page.evaluate("() => document.getElementById('ia-next').disabled")
        log(2, f"下一步按钮 disabled={btn_disabled} (应为 true，因无目标端或未选择)")

        log(2, "✓ 步骤2 UI 验证完成")

        # 步骤2 向导导航条名称验证
        step_labels = page.locator(".step-label").all_text_contents()
        log(2, f"导航条步骤名: {step_labels}")
        assert "实例关联" in step_labels, "步骤2名称应为'实例关联'"
        assert "配置对比" in step_labels, "步骤3名称应为'配置对比'"
        log(2, "✓ 步骤名称正确: 实例关联 / 配置对比")

        browser.close()
        return {
            "步骤1": "✓ 凭证验证+下一步",
            "步骤2": step2_result,
            "步骤名称": "✓ 实例关联/配置对比",
            "源端实例": f"✓ {src_count}个",
        }


if __name__ == "__main__":
    os.makedirs("tests/screenshots", exist_ok=True)

    # 后端测试
    api_results, ali_configs, instances = test_api_flow()

    # 前端测试
    ui_results = test_playwright_flow(ali_configs, instances)

    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    all_results = {**api_results, **ui_results}
    passed = sum(1 for v in all_results.values() if "✓" in str(v))
    failed = sum(1 for v in all_results.values() if "✗" in str(v))

    for name, result in all_results.items():
        print(f"  {result}  {name}")

    print(f"\n总计: {len(all_results)} 项, {passed} 通过, {failed} 失败")
    print(f"截图: tests/screenshots/v3_*.png")
