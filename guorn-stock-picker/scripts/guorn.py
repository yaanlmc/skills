#!/usr/bin/env python3
"""
果仁网（guorn.com）选股查询脚本

功能：
1. 登录果仁网
2. 点击"一键更新"刷新数据
3. 查看策略列表
4. 进入策略详情
5. 查看策略定义
6. 执行每日选股
7. 查看持仓

依赖：websocket-client
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request

import websocket


# 策略 SID 映射
STRATEGY_SIDS = {
    "yaanlmc-v-1.9": "2478414.R.357840722257958",
    "yaanlmc-v-1.8": None,  # 需要补充
    "yaanlmc-v-1.7": None,  # 需要补充
    "王春花": None,  # 需要补充
}


def get_websocket():
    """获取 Chrome 调试 websocket 连接"""
    try:
        tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
        if not tabs:
            raise Exception("Chrome not running or no tabs")
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=15)
        return ws
    except Exception as e:
        print(f"连接 Chrome 失败: {e}")
        print("请先启动 Chrome: --remote-debugging-port=9222")
        sys.exit(1)


def cdp(ws, method, params=None, cid=1):
    """发送 CDP 命令"""
    req = {"id": cid, "method": method, "params": params or {}}
    ws.send(json.dumps(req))
    return json.loads(ws.recv())


def click(ws, x, y):
    """模拟鼠标点击"""
    cdp(ws, "Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1
    })
    time.sleep(0.05)
    cdp(ws, "Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1
    })


def type_text(ws, text):
    """模拟键盘输入"""
    for ch in text:
        cdp(ws, "Input.dispatchKeyEvent", {"type": "keyDown", "text": ch})
        cdp(ws, "Input.dispatchKeyEvent", {"type": "keyUp", "text": ch})
        time.sleep(0.03)


def find_element(ws, text):
    """查找页面元素位置"""
    js = f"""
    (function() {{
        const allEls = document.querySelectorAll('*');
        for (const el of allEls) {{
            if (el.innerText && el.innerText.trim() === '{text}' && el.children.length === 0) {{
                const rect = el.getBoundingClientRect();
                if (rect.width > 5 && rect.height > 5) {{
                    return JSON.stringify({{
                        text: el.innerText.trim(),
                        tag: el.tagName,
                        x: Math.round(rect.x + rect.width/2),
                        y: Math.round(rect.y + rect.height/2),
                        visible: true
                    }});
                }}
            }}
        }}
        return 'not found';
    }})()
    """
    r = cdp(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    val = r.get("result", {}).get("result", {}).get("value")
    if val and val != "not found":
        return json.loads(val)
    return None


def screenshot(path="/tmp/guorn_screenshot.png"):
    """截取屏幕"""
    subprocess.run(["screencapture", "-x", path], check=True, capture_output=True)
    return path


def click_one_key_update(ws):
    """点击"一键更新"按钮刷新数据"""
    print("3. 点击"一键更新"...")
    btn = find_element(ws, "一键更新")
    if btn:
        click(ws, btn["x"], btn["y"])
        time.sleep(5)
        print("   已点击一键更新，等待数据刷新...")
        return True
    else:
        print("   警告: 未找到"一键更新"按钮，跳过")
        return False


def login(ws, phone, password):
    """登录果仁网"""
    print("1. 导航到果仁网...")
    cdp(ws, "Page.navigate", {"url": "https://guorn.com/"})
    time.sleep(5)

    print("2. 点击登录按钮...")
    login_btn = find_element(ws, "登录")
    if login_btn:
        click(ws, login_btn["x"], login_btn["y"])
        time.sleep(3)
    else:
        print("   警告: 未找到登录按钮")

    print("3. 填写手机号...")
    cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                if (inp.offsetParent !== null && (inp.placeholder?.includes('手机') || inp.placeholder?.includes('账号'))) {
                    inp.focus();
                    inp.click();
                    return 'found';
                }
            }
            return 'not found';
        })()
        """
    })
    time.sleep(0.5)
    type_text(ws, phone)

    print("4. 填写密码...")
    cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const inputs = document.querySelectorAll('input[type="password"]');
            for (const inp of inputs) {
                if (inp.offsetParent !== null) {
                    inp.focus();
                    inp.click();
                    return 'found';
                }
            }
            return 'not found';
        })()
        """
    })
    time.sleep(0.5)
    type_text(ws, password)

    print("5. 点击登录...")
    r = cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const btns = document.querySelectorAll('button, [role=button]');
            for (const btn of btns) {
                if (btn.innerText && btn.innerText.trim() === '登录' && btn.offsetParent !== null) {
                    btn.click();
                    return 'clicked';
                }
            }
            return 'not found';
        })()
        """
    })
    print(f"   {r.get('result',{}).get('result',{}).get('value')}")

    time.sleep(5)

    # 检查登录状态
    r = cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const text = document.body.innerText;
            if (text.includes('我的主页') || text.includes('我的策略') || text.includes('一键更新')) return 'LOGGED_IN';
            return 'NOT_LOGGED_IN';
        })()
        """
    })
    status = r.get("result", {}).get("result", {}).get("value")
    print(f"6. 登录状态: {status}")

    # 登录成功后，点击"一键更新"
    if status == "LOGGED_IN":
        click_one_key_update(ws)

    return status == "LOGGED_IN"


def get_strategy_sid(strategy_name):
    """获取策略 SID"""
    if strategy_name in STRATEGY_SIDS:
        return STRATEGY_SIDS[strategy_name]
    # 如果传入的是完整 SID
    if ".R." in strategy_name:
        return strategy_name
    return None


def go_to_strategy(ws, strategy_name_or_id):
    """进入策略详情页"""
    print(f"进入策略: {strategy_name_or_id}...")

    sid = get_strategy_sid(strategy_name_or_id)
    if sid:
        url = f"https://guorn.com/stock/strategy?sid={sid}"
        cdp(ws, "Page.navigate", {"url": url})
        time.sleep(5)
        print(f"   已导航到 {url}")
        return True

    # 尝试在当前页面查找策略链接
    r = cdp(ws, "Runtime.evaluate", {
        "expression": f"""
        (function() {{
            const links = document.querySelectorAll('a');
            for (const el of links) {{
                if (el.innerText && el.innerText.trim().includes('{strategy_name_or_id}')) {{
                    const rect = el.getBoundingClientRect();
                    return JSON.stringify({{
                        text: el.innerText.trim(),
                        x: Math.round(rect.x + rect.width/2),
                        y: Math.round(rect.y + rect.height/2)
                    }});
                }}
            }}
            return 'not found';
        }})()
        """,
        "returnByValue": True
    })
    val = r.get("result", {}).get("result", {}).get("value")
    if val and val != "not found":
        data = json.loads(val)
        click(ws, data["x"], data["y"])
        time.sleep(5)
        print(f"   已点击进入策略详情")
        return True

    print(f"   未找到策略: {strategy_name_or_id}")
    return False


def view_strategy_definition(ws):
    """查看策略定义（进入策略编辑页面）"""
    print("查看策略定义...")

    r = cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                if (el.innerText && el.innerText.trim() === '查看定义' && el.children.length === 0) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 5 && rect.width < 200 && rect.height > 5 && rect.height < 60) {
                        return JSON.stringify({
                            x: Math.round(rect.x + rect.width/2),
                            y: Math.round(rect.y + rect.height/2)
                        });
                    }
                }
            }
            return 'not found';
        })()
        """,
        "returnByValue": True
    })
    val = r.get("result", {}).get("result", {}).get("value")
    if val and val != "not found":
        data = json.loads(val)
        click(ws, data["x"], data["y"])
        time.sleep(4)
        print("   已打开策略定义")
        return True
    return False


def daily_stock_pick(ws, date=None):
    """执行每日选股"""
    print(f"执行每日选股... (日期: {date or '前一天'})")

    # 滚动查找"每日选股"标签
    print("   查找'每日选股'标签...")
    for i in range(10):
        cdp(ws, "Runtime.evaluate", {"expression": f"window.scrollTo(0, {i * 200})"})
        time.sleep(0.5)

        r = cdp(ws, "Runtime.evaluate", {
            "expression": """
            (function() {
                const allEls = document.querySelectorAll('a, span, div');
                for (const el of allEls) {
                    if (el.innerText?.trim() === '每日选股') {
                        const rect = el.getBoundingClientRect();
                        if (rect.top >= 0 && rect.top < window.innerHeight) {
                            return JSON.stringify({
                                x: Math.round(rect.x + rect.width/2),
                                y: Math.round(rect.y + rect.height/2)
                            });
                        }
                    }
                }
                return 'not found';
            })()
            """,
            "returnByValue": True
        })
        val = r.get("result", {}).get("result", {}).get("value")
        if val and val != "not found":
            data = json.loads(val)
            print(f"   找到！坐标: ({data['x']}, {data['y']})")
            click(ws, data["x"], data["y"])
            time.sleep(3)
            break
    else:
        print("   未找到'每日选股'标签")
        return False

    # 点击"开始选股"按钮
    print("   点击'开始选股'...")
    r = cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.innerText && btn.innerText.trim() === '开始选股') {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 5 && rect.height > 5) {
                        return JSON.stringify({
                            x: Math.round(rect.x + rect.width/2),
                            y: Math.round(rect.y + rect.height/2)
                        });
                    }
                }
            }
            return 'not found';
        })()
        """,
        "returnByValue": True
    })
    val = r.get("result", {}).get("result", {}).get("value")
    if val and val != "not found":
        data = json.loads(val)
        print(f"   找到！坐标: ({data['x']}, {data['y']})")
        click(ws, data["x"], data["y"])
        time.sleep(8)
        print("   已执行选股")
        return True

    print("   未找到'开始选股'按钮")
    return False


def get_stock_pick_results(ws):
    """获取选股结果"""
    print("获取选股结果...")

    r = cdp(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            const bodyText = document.body.innerText;
            const idx = bodyText.indexOf('符合条件的股票');
            if (idx >= 0) {
                return bodyText.substring(idx, idx + 3000);
            }
            return 'not found';
        })()
        """,
        "returnByValue": True
    })
    val = r.get("result", {}).get("result", {}).get("value")
    if val and val != "not found":
        print(f"\n{val}")
        return val
    return "未找到选股结果"


def main():
    parser = argparse.ArgumentParser(description="果仁网选股查询工具")
    parser.add_argument("--login", action="store_true", help="登录果仁网（包含一键更新）")
    parser.add_argument("--phone", default="18080155660", help="手机号")
    parser.add_argument("--password", default="Lmc351020", help="密码")
    parser.add_argument("--strategy", help="进入指定策略（如 yaanlmc-v-1.9）")
    parser.add_argument("--definition", action="store_true", help="查看策略定义")
    parser.add_argument("--daily-pick", action="store_true", help="执行每日选股")
    parser.add_argument("--results", action="store_true", help="获取选股结果")
    parser.add_argument("--screenshot", help="保存截图路径")

    args = parser.parse_args()

    if args.login:
        ws = get_websocket()
        success = login(ws, args.phone, args.password)
        ws.close()
        sys.exit(0 if success else 1)

    if args.strategy:
        ws = get_websocket()
        go_to_strategy(ws, args.strategy)
        if args.definition:
            view_strategy_definition(ws)
        if args.daily_pick:
            daily_stock_pick(ws)
        if args.results:
            get_stock_pick_results(ws)
        if args.screenshot:
            screenshot(args.screenshot)
        ws.close()
        return

    if args.daily_pick:
        ws = get_websocket()
        daily_stock_pick(ws)
        if args.results:
            get_stock_pick_results(ws)
        if args.screenshot:
            screenshot(args.screenshot)
        ws.close()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
