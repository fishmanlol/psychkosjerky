import os, json, time, pathlib
import requests

URL = "https://www.psychkosjerky.com/shop/p/crispy-savory"
# CHECK_KEYWORD = "Sold Out"
CHECK_KEYWORD = "dflksjdflkajf3rdflk;l"
STATE_FILE = pathlib.Path("restock_state.json")

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
    return CHECK_KEYWORD in html

def load_prev():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"sold_out": None}

def save_state(sold_out: bool):
    STATE_FILE.write_text(json.dumps({"sold_out": sold_out, "ts": int(time.time())}))

def main():
    prev = load_prev()["sold_out"]
    now = is_sold_out(fetch_html())

    # 第一次运行：只记录，不推送
    if prev is None:
        save_state(now)
        return

    # 缺货 -> 有货：推送一次
    if prev is True and now is False:
        notify_wechat("🛒 Psychko’s Jerky 补货提醒", f"商品已补货！\n\n{URL}")

    save_state(now)

if __name__ == "__main__":
    main()
