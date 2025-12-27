import os, json, time, pathlib, re
import requests

URL = "https://www.psychkosjerky.com/shop/p/crispy-savory"
STATE_FILE = pathlib.Path("restock_state.json")

# 只认这一种“明确缺货徽标”
RE_SOLD_OUT_BADGE = re.compile(
    r'<span[^>]*class="[^"]*\bproduct-mark\b[^"]*\bsold-out\b',
    re.IGNORECASE
)

def notify_wechat(title: str, content: str):
    send_key = os.environ["SERVERCHAN_SENDKEY"]
    api = f"https://sctapi.ftqq.com/{send_key}.send"
    r = requests.post(api, data={"title": title, "desp": content}, timeout=20)
    r.raise_for_status()

def fetch_html() -> str:
    headers = {"User-Agent": "restock-watch/1.0 (personal use)"}
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def is_sold_out(html: str) -> bool:
    # 只要出现明确的 sold-out 徽标，就认为缺货
    return bool(RE_SOLD_OUT_BADGE.search(html))

def load_prev():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"sold_out": None}

def save_state(sold_out: bool):
    STATE_FILE.write_text(json.dumps({
        "sold_out": sold_out,
        "ts": int(time.time())
    }))

def main():
    prev = load_prev()["sold_out"]

    html = fetch_html()
    now = is_sold_out(html)

    # 调试信息（只看真实信号）
    print(
        "STATE_FILE:", STATE_FILE.resolve(), "exists:", STATE_FILE.exists(),
        "| prev:", prev,
        "| now:", now,
        "| has_sold_out_badge:", bool(RE_SOLD_OUT_BADGE.search(html))
    )

    # 第一次运行：只记录，不推送
    if prev is None:
        save_state(now)
        return

    # 有货 -> 缺货
    if prev is False and now is True:
        notify_wechat(
            "❌ Psychko’s Jerky 缺货提醒",
            f"商品已缺货（Sold Out）。\n\n{URL}"
        )

    # 缺货 -> 有货
    if prev is True and now is False:
        notify_wechat(
            "✅ Psychko’s Jerky 补货提醒",
            f"商品已补货！\n\n{URL}"
        )

    save_state(now)

if __name__ == "__main__":
    main()
