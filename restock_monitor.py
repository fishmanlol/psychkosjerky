#!/usr/bin/env python3
"""
Psych Ko's Jerky 库存监控脚本

用法:
    python restock_monitor.py           # 只采集数据
    python restock_monitor.py --notify  # 采集数据 + 发送通知
"""

import os
import sys
import json
import re
import csv
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.parse
from pathlib import Path

# ============== 配置 ==============

# 固定使用 PST 时区 (UTC-8)
PST = timezone(timedelta(hours=-8))

def now():
    """获取当前时间（PST）"""
    return datetime.now(PST)

PRODUCTS = {
    "crispy-savory": {
        "name": "Medium Crispy Savory",
        "url": "https://www.psychkosjerky.com/shop/p/crispy-savory",
    },
    "crispy-lean": {
        "name": "Extra Crispy Lean", 
        "url": "https://www.psychkosjerky.com/shop/p/crispy-lean",
    },
}

HISTORY_FILE = Path("stock_history.csv")
LOW_STOCK_THRESHOLD = 5

# ============== 正则 ==============

RE_CONTEXT = re.compile(
    r'Static\.SQUARESPACE_CONTEXT\s*=\s*(\{.+?\});\s*</script>', 
    re.DOTALL
)

# ============== 函数 ==============

def fetch_html(url: str) -> str:
    req = urllib.request.Request(
        url, 
        headers={"User-Agent": "restock-watch/2.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_variants(html: str) -> dict:
    """解析页面中的 variant 库存信息"""
    m = RE_CONTEXT.search(html)
    if not m:
        return {}
    
    ctx = json.loads(m.group(1))
    variants = ctx.get("product", {}).get("variants", [])
    
    result = {}
    for v in variants:
        spice = v.get("attributes", {}).get("Spice Level", "").lower()
        if not spice:
            continue
        stock = v.get("stock", {})
        result[spice] = {
            "quantity": stock.get("quantity", 0),
            "unlimited": stock.get("unlimited", False),
        }
    
    return result


def save_history(product_slug: str, product_name: str, spice: str, stock_info: dict):
    """追加库存记录到历史文件"""
    file_exists = HISTORY_FILE.exists()
    
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        if not file_exists:
            writer.writerow([
                "timestamp", "unix_ts", "product_slug", "product_name",
                "spice_level", "quantity", "unlimited", "sold_out",
            ])
        
        current_time = now()
        qty = stock_info.get("quantity", 0)
        unlimited = stock_info.get("unlimited", False)
        sold_out = not unlimited and qty == 0
        
        writer.writerow([
            current_time.isoformat(),
            int(current_time.timestamp()),
            product_slug,
            product_name,
            spice,
            qty,
            unlimited,
            sold_out,
        ])


def notify_wechat(title: str, content: str):
    """通过 Server 酱推送通知"""
    send_key = os.environ.get("SERVERCHAN_SENDKEY")
    if not send_key:
        print(f"[NOTIFY] {title}\n{content}\n")
        return
    
    api = f"https://sctapi.ftqq.com/{send_key}.send"
    try:
        data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
        req = urllib.request.Request(api, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"[API Response] {result}")
            if result.get("code") == 0:
                print(f"[NOTIFIED] {title}")
            else:
                print(f"[NOTIFY FAILED] {result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"[NOTIFY ERROR] {e}")


def build_daily_report(all_stock: dict) -> str:
    """生成每日库存报告"""
    lines = []
    lines.append(f"📅 **{now().strftime('%Y-%m-%d %H:%M')}**\n")
    
    for slug, product_info in PRODUCTS.items():
        product_name = product_info["name"]
        url = product_info["url"]
        variants = all_stock.get(slug, {})
        
        lines.append(f"## 📦 {product_name}\n")
        
        for spice in ["mild", "medium", "spicy"]:
            stock = variants.get(spice, {})
            qty = stock.get("quantity", 0)
            unlimited = stock.get("unlimited", False)
            
            if unlimited:
                status = "∞ 无限"
            elif qty == 0:
                status = "❌ **缺货**"
            elif qty <= LOW_STOCK_THRESHOLD:
                status = f"⚠️ **{qty}** (低库存)"
            else:
                status = f"✅ {qty}"
            
            lines.append(f"- {spice.title()}: {status}")
        
        lines.append(f"\n🔗 [查看商品]({url})\n")
    
    return "\n".join(lines)


def main():
    # 检查是否需要发送通知
    send_notify = "--notify" in sys.argv
    
    print(f"\n{'='*50}")
    print(f"Psych Ko's Jerky 库存检查 - {now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模式: {'采集+通知' if send_notify else '仅采集'}")
    print(f"{'='*50}\n")
    
    all_stock = {}
    
    for slug, product_info in PRODUCTS.items():
        product_name = product_info["name"]
        url = product_info["url"]
        
        print(f"📦 {product_name}")
        
        try:
            html = fetch_html(url)
            variants = parse_variants(html)
        except Exception as e:
            print(f"   ❌ 获取失败: {e}\n")
            continue
        
        all_stock[slug] = variants
        
        for spice in ["mild", "medium", "spicy"]:
            stock = variants.get(spice, {})
            qty = stock.get("quantity", 0)
            unlimited = stock.get("unlimited", False)
            
            if unlimited:
                print(f"   - {spice.title()}: ∞ 无限")
            elif qty == 0:
                print(f"   - {spice.title()}: ❌ 缺货")
            elif qty <= LOW_STOCK_THRESHOLD:
                print(f"   - {spice.title()}: ⚠️ {qty} (低库存)")
            else:
                print(f"   - {spice.title()}: ✅ {qty}")
            
            # 保存历史
            save_history(slug, product_name, spice, stock)
        
        print()
    
    # 发送每日报告（仅在 --notify 模式下）
    if send_notify:
        report = build_daily_report(all_stock)
        notify_wechat("🥩 Psych Ko's Jerky 库存日报", report)
    
    print(f"历史已追加到 {HISTORY_FILE.resolve()}")


if __name__ == "__main__":
    main()
