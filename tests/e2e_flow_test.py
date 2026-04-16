"""
端到端自动化测试 v2：完整 6 步迁移流程
源端：阿里云广州(cn-guangzhou) → 目标端：腾讯云广州(ap-guangzhou)
"""
import time
import json
import sys
import os
from playwright.sync_api import sync_playwright


BASE_URL = "http://localhost:10041"


def log(step, msg):
    print(f"[步骤{step}] {msg}")


def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error",) else None)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc.message}"))

        # ============ 步骤 1: 凭证配置 ============
        log(1, "打开首页...")
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        time.sleep(3)
        page.screenshot(path="tests/screenshots/step1_init.png")

        if page.locator("#c-aliyun-ak").count() == 0:
            log(1, "❌ 凭证表单不存在")
            content = page.content()
            log(1, f"  页面片段: {content[:300]}")
            for e in console_errors: log(1, f"  {e}")
            browser.close()
            return False, "步骤1: 表单不存在"

        log(1, "✓ 凭证页面OK")

        # 先试 .env 加载
        page.click("#c-btn-load-env")
        time.sleep(3)
        ak_val = page.locator("#c-aliyun-ak").input_value()
        if not ak_val:
            log(1, "  .env未填充，手动填写")
            # 使用环境变量中的凭证（运行测试前需配置）
            import os as _os
            page.fill("#c-aliyun-ak", _os.getenv('TEST_ALI_AK', ''))
            page.fill("#c-aliyun-sk", _os.getenv('TEST_ALI_SK', ''))
            page.fill("#c-tencent-sid", _os.getenv('TEST_TC_SID', ''))
            page.fill("#c-tencent-sk", _os.getenv('TEST_TC_SK', ''))
        else:
            log(1, f"  ✓ .env已自动填充AK: {ak_val[:10]}...")

        page.select_option("#c-aliyun-region", "cn-guangzhou")
        page.select_option("#c-tencent-region", "ap-guangzhou")
        log(1, "✓ 地域: 广州/广州")

        # 验证
        page.click("#c-btn-verify-ali")
        time.sleep(6)
        ali_ok = "check_circle" in page.locator("#c-ali-status").inner_html()
        log(1, f"  阿里云验证: {'✓' if ali_ok else '✗'}")

        page.click("#c-btn-verify-tc")
        time.sleep(6)
        tc_ok = "check_circle" in page.locator("#c-tc-status").inner_html()
        log(1, f"  腾讯云验证: {'✓' if tc_ok else '✗'}")

        if not ali_ok or not tc_ok:
            page.screenshot(path="tests/screenshots/step1_verify_fail.png")
            browser.close()
            return False, "步骤1: 凭证验证失败"

        # 下一步
        next_btn = page.locator("#c-btn-next")
        if next_btn.get_attribute("disabled") is not None:
            log(1, "❌ 下一步禁用")
            browser.close()
            return False, "步骤1: 下一步禁用"

        next_btn.click()
        time.sleep(5)
        page.screenshot(path="tests/screenshots/step2_init.png")
        log(1, "✓ 步骤1完成 → 步骤2")

        # ============ 步骤 2: 选择源端实例 ============
        time.sleep(3)
        cbs = page.locator("input[type='checkbox']")
        count = cbs.count()
        log(2, f"找到 {count} 个checkbox")

        if count == 0:
            page.screenshot(path="tests/screenshots/step2_no_inst.png")
            log(2, f"  内容: {page.locator('#step-content').inner_text()[:300]}")
            for e in console_errors: log(2, f"  {e}")
            browser.close()
            return False, "步骤2: 无实例"

        for i in range(count):
            if not cbs.nth(i).is_checked():
                cbs.nth(i).check(force=True)
        log(2, f"✓ 全选 {count} 个")

        time.sleep(1)
        page.screenshot(path="tests/screenshots/step2_selected.png")

        next2 = page.locator("button:has-text('下一步')")
        if next2.count() == 0 or next2.first.get_attribute("disabled") is not None:
            log(2, "❌ 下一步不可用")
            browser.close()
            return False, "步骤2: 下一步不可用"

        next2.first.click()
        time.sleep(8)  # 映射可能需要时间
        page.screenshot(path="tests/screenshots/step3_init.png")
        log(2, "✓ 步骤2完成 → 步骤3")

        # ============ 步骤 3: 配置映射 ============
        content3 = page.locator("#step-content").inner_text()
        if "功能开发中" in content3 or "渲染错误" in content3:
            log(3, "❌ 映射页面失败")
            for e in console_errors: log(3, f"  {e}")
            browser.close()
            return False, "步骤3: 加载失败"

        # 检查统计
        if "映射" in content3:
            log(3, "✓ 映射结果展示OK")
        log(3, f"  内容摘要: {content3[:200]}")

        page.screenshot(path="tests/screenshots/step3_loaded.png")

        next3 = page.locator("button:has-text('下一步')")
        if next3.count() == 0:
            log(3, "❌ 无下一步按钮")
            browser.close()
            return False, "步骤3: 无下一步"

        next3.first.click()
        time.sleep(4)
        page.screenshot(path="tests/screenshots/step4_init.png")
        log(3, "✓ 步骤3完成 → 步骤4")

        # ============ 步骤 4: 迁移计划确认 ============
        content4 = page.locator("#step-content").inner_text()
        if "功能开发中" in content4 or "渲染错误" in content4:
            log(4, "❌ 计划页面失败")
            browser.close()
            return False, "步骤4: 加载失败"

        plan_cbs = page.locator(".pl-chk")
        log(4, f"计划项: {plan_cbs.count()} 个")
        page.screenshot(path="tests/screenshots/step4_loaded.png")

        confirm_btn = page.locator("#pl-confirm")
        if confirm_btn.count() == 0:
            log(4, "❌ 确认按钮不存在")
            browser.close()
            return False, "步骤4: 无确认按钮"

        confirm_btn.click()
        time.sleep(4)
        page.screenshot(path="tests/screenshots/step5_init.png")
        log(4, "✓ 步骤4完成 → 步骤5")

        # ============ 步骤 5: 迁移执行 ============
        content5 = page.locator("#step-content").inner_text()
        if "功能开发中" in content5 or "渲染错误" in content5:
            log(5, "❌ 执行页面失败")
            browser.close()
            return False, "步骤5: 加载失败"

        # 点击"开始执行"按钮！
        start_btn = page.locator("#ex-start")
        if start_btn.count() == 0:
            log(5, "❌ 开始执行按钮不存在")
            browser.close()
            return False, "步骤5: 无开始按钮"

        log(5, "点击'开始执行'...")
        start_btn.click()

        # 等待执行完成
        for i in range(30):
            time.sleep(2)
            status_text = page.locator("#ex-status").text_content() or ""
            if "完成" in status_text:
                log(5, f"✓ {status_text} (等了 {(i+1)*2}s)")
                break
        else:
            log(5, "⚠ 执行超时60s")

        page.screenshot(path="tests/screenshots/step5_done.png")

        # 检查"查看报告"按钮
        report_btn = page.locator("#ex-next")
        if report_btn.count() > 0:
            disabled = report_btn.get_attribute("disabled")
            if disabled is not None:
                log(5, "❌ 查看报告按钮仍禁用")
                # 检查日志面板
                log_text = page.locator("#ex-log").inner_text()
                log(5, f"  日志: {log_text[:300]}")
                browser.close()
                return False, "步骤5: 报告按钮禁用"

            report_btn.click()
            time.sleep(3)
        else:
            log(5, "❌ 查看报告按钮不存在")
            browser.close()
            return False, "步骤5: 无报告按钮"

        page.screenshot(path="tests/screenshots/step6_init.png")
        log(5, "✓ 步骤5完成 → 步骤6")

        # ============ 步骤 6: 迁移报告 ============
        time.sleep(3)
        content6 = page.locator("#step-content").inner_text()
        if "功能开发中" in content6 or "渲染错误" in content6:
            log(6, "❌ 报告页面失败")
            for e in console_errors: log(6, f"  {e}")
            browser.close()
            return False, "步骤6: 加载失败"

        page.screenshot(path="tests/screenshots/step6_loaded.png")
        log(6, f"报告内容摘要: {content6[:300]}")

        # 测试导出
        export_btn = page.locator("button:has-text('导出'), button:has-text('JSON')")
        if export_btn.count() > 0:
            log(6, "✓ 导出按钮存在")

        log(6, "✓ 步骤6完成 — 全流程通过！")

        page.screenshot(path="tests/screenshots/final.png")

        print("\n===== 控制台错误 =====")
        for e in console_errors:
            print(f"  {e}")

        browser.close()
        return True, "全流程通过"


if __name__ == "__main__":
    os.makedirs("tests/screenshots", exist_ok=True)
    success, msg = run_test()
    print(f"\n{'='*50}")
    print(f"测试结果: {'✓ 通过' if success else '✗ 失败'}")
    print(f"消息: {msg}")
    sys.exit(0 if success else 1)
