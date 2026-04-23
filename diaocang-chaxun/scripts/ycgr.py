#!/usr/bin/env python3
"""
一创果仁网（ycgr.fcsc.com）实盘策略与持仓查询脚本

功能：
1. 登录一创果仁网
2. 查看账户总览
3. 查看策略列表
4. 查看策略详情
5. 查看持仓明细
6. 查看调仓指令

依赖：websocket-client
"""

import argparse
import json
import re
import sys
import time
import urllib.request

WS_URL = "ws://127.0.0.1:9222/devtools/page/{}"
JSON_LIST_URL = "http://127.0.0.1:9222/json/list"


def get_page_id():
    """获取当前活动页面的 ID"""
    try:
        with urllib.request.urlopen(JSON_LIST_URL, timeout=5) as resp:
            tabs = json.loads(resp.read().decode())
            for tab in tabs:
                if "ycgr.fcsc.com" in tab.get("url", ""):
                    return tab["id"]
            # 如果没有找到 ycgr 页面，返回第一个页面
            if tabs:
                return tabs[0]["id"]
    except Exception as e:
        print(f"获取页面 ID 失败: {e}")
    return None


def create_ws():
    """创建 WebSocket 连接"""
    try:
        import websocket
    except ImportError:
        print("错误: 需要安装 websocket-client")
        print("运行: pip3 install websocket-client")
        sys.exit(1)

    page_id = get_page_id()
    if not page_id:
        print("错误: 未找到可用的 Chrome 页面")
        sys.exit(1)

    return websocket.create_connection(WS_URL.format(page_id), timeout=30)


def ws_command(ws, method, params=None, cmd_id=1):
    """发送 CDP 命令"""
    cmd = {"id": cmd_id, "method": method}
    if params:
        cmd["params"] = params
    ws.send(json.dumps(cmd))
    return json.loads(ws.recv())


def navigate(url):
    """导航到指定 URL"""
    ws = create_ws()
    ws_command(ws, "Page.navigate", {"url": url}, 1)
    ws.close()


def get_page_content():
    """获取页面内容"""
    ws = create_ws()
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": "document.body.innerText"
    }, 1)
    ws.close()
    return resp.get("result", {}).get("result", {}).get("value", "")


def get_page_url():
    """获取当前页面 URL"""
    ws = create_ws()
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": "location.href"
    }, 1)
    ws.close()
    return resp.get("result", {}).get("result", {}).get("value", "")


def check_login():
    """检查是否已登录"""
    content = get_page_content()
    # 检查是否显示用户名（LLLMMM 等）
    if re.search(r"[A-Z]{3,}", content) and "实盘" in content:
        return True
    return False


def login(phone, password):
    """登录一创果仁网"""
    print(f"正在登录一创果仁网...")

    ws = create_ws()

    # 导航到首页
    print("1. 导航到 ycgr.fcsc.com")
    ws_command(ws, "Page.navigate", {"url": "https://ycgr.fcsc.com"}, 1)
    time.sleep(3)

    # 检查是否已登录
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": "document.body.innerText.indexOf('LLLMMM') >= 0 ? 'LOGGED_IN' : 'NOT_LOGGED_IN'"
    }, 2)
    if resp.get("result", {}).get("result", {}).get("value") == "LOGGED_IN":
        print("已登录")
        ws.close()
        return True

    # 点击登录按钮
    print("2. 点击登录按钮")
    ws_command(ws, "Runtime.evaluate", {
        "expression": """
        var btns = document.querySelectorAll('a, button, span, div');
        for(var i=0; i<btns.length; i++){
            if(btns[i].innerText.trim() === '登录'){
                btns[i].click();
                break;
            }
        }
        """
    }, 3)
    time.sleep(2)

    # 填写手机号（使用键盘模拟）
    print(f"3. 填写手机号: {phone}")
    ws_command(ws, "Runtime.evaluate", {
        "expression": f"""
        var input = document.querySelector('input[placeholder*="手机"], input[type="tel"], input.phone');
        if(input){{
            input.focus();
            input.click();
        }}
        """
    }, 4)
    time.sleep(0.5)

    # 使用键盘输入手机号
    for char in phone:
        ws_command(ws, "Input.dispatchKeyEvent", {
            "type": "keyDown",
            "text": char
        }, 0)
        ws_command(ws, "Input.dispatchKeyEvent", {
            "type": "keyUp",
            "text": char
        }, 0)
        time.sleep(0.05)

    time.sleep(0.5)

    # 填写密码
    print("4. 填写密码")
    ws_command(ws, "Runtime.evaluate", {
        "expression": """
        var inputs = document.querySelectorAll('input[type="password"]');
        if(inputs.length > 0){
            inputs[0].focus();
            inputs[0].click();
        }
        """
    }, 5)
    time.sleep(0.5)

    for char in password:
        ws_command(ws, "Input.dispatchKeyEvent", {
            "type": "keyDown",
            "text": char
        }, 0)
        ws_command(ws, "Input.dispatchKeyEvent", {
            "type": "keyUp",
            "text": char
        }, 0)
        time.sleep(0.05)

    time.sleep(0.5)

    # 点击登录按钮
    print("5. 提交登录")
    ws_command(ws, "Runtime.evaluate", {
        "expression": """
        var btns = document.querySelectorAll('button, input[type="submit"], a.btn, div.btn');
        for(var i=0; i<btns.length; i++){
            if(btns[i].innerText.indexOf('登录') >= 0 || btns[i].innerText.indexOf('确定') >= 0){
                btns[i].click();
                break;
            }
        }
        """
    }, 6)

    time.sleep(5)

    # 验证登录
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": "document.body.innerText.indexOf('LLLMMM') >= 0 ? 'SUCCESS' : 'FAILED'"
    }, 7)
    result = resp.get("result", {}).get("result", {}).get("value", "FAILED")

    ws.close()

    if result == "SUCCESS":
        print("✅ 登录成功")
        return True
    else:
        print("❌ 登录失败，请检查账号密码或验证码")
        return False


def get_overview():
    """获取账户总览"""
    print("正在获取账户总览...")

    ws = create_ws()

    # 检查当前页面
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": "location.href"
    }, 1)
    url = resp.get("result", {}).get("result", {}).get("value", "")

    # 如果不在持仓页面，导航过去
    if "page=holdings" not in url:
        # 先获取账户 ID
        resp = ws_command(ws, "Runtime.evaluate", {
            "expression": """
            var link = document.querySelector('a[href*="trader/home"]');
            link ? link.href : null;
            """
        }, 2)
        account_url = resp.get("result", {}).get("result", {}).get("value")

        if account_url:
            ws_command(ws, "Page.navigate", {"url": account_url + "&page=holdings"}, 3)
            time.sleep(3)

    # 提取数据
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            var text = document.body.innerText;
            var result = {};

            // 当前净值
            var netMatch = text.match(/当前净值[\\s\\S]*?(\\d+\\.\\d+)/);
            result.net_value = netMatch ? netMatch[1] : null;

            // 总资产
            var totalMatch = text.match(/总资产[\\s\\S]*?([\\d,]+\\.\\d{2})/);
            result.total_asset = totalMatch ? totalMatch[1] : null;

            // 持仓市值
            var holdingMatch = text.match(/持仓市值[\\s\\S]*?([\\d,]+\\.\\d{2})/);
            result.holding_value = holdingMatch ? holdingMatch[1] : null;

            // 可用现金
            var cashMatch = text.match(/可用现金[\\s\\S]*?([\\d,]+\\.\\d{2})/);
            result.available_cash = cashMatch ? cashMatch[1] : null;

            return JSON.stringify(result);
        })()
        """
    }, 10)

    ws.close()

    data = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))
    return data


def get_strategies():
    """获取策略列表"""
    print("正在获取策略列表...")

    content = get_page_content()

    strategies = []
    # 解析策略信息
    # 格式：策略名 持仓市值 可用现金 日收益率

    lines = content.split("\n")
    current_strategy = None

    for i, line in enumerate(lines):
        # 查找策略名（yaanlmc-v-x.x 或其他策略名）
        if re.match(r"^[a-zA-Z0-9_\-\u4e00-\u9fa5]+\s*$", line.strip()):
            name = line.strip()
            # 检查下一行是否有数字（市值）
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.search(r"\d+,\d+\.\d{2}", next_line):
                    current_strategy = {"name": name}

        if current_strategy:
            # 提取数据
            numbers = re.findall(r"([\d,]+\.\d{2}|[\d,]+|-?[\d.]+%)", line)
            if len(numbers) >= 4:
                current_strategy["holding_value"] = numbers[0]
                current_strategy["available_cash"] = numbers[1]
                current_strategy["daily_return"] = numbers[2]
                strategies.append(current_strategy)
                current_strategy = None

    return strategies


def get_strategy_detail(strategy_name_or_id):
    """获取策略详情"""
    print(f"正在获取策略详情: {strategy_name_or_id}...")

    ws = create_ws()

    # 如果传入的是策略名，先查找策略 ID
    if not strategy_name_or_id.startswith("105503"):
        resp = ws_command(ws, "Runtime.evaluate", {
            "expression": f"""
            (function() {{
                var links = document.querySelectorAll('a[href*="sid="]');
                for(var i=0; i<links.length; i++){{
                    if(links[i].innerText.indexOf('{strategy_name_or_id}') >= 0){{
                        var match = links[i].href.match(/sid=([0-9.R]+)/);
                        return match ? match[1] : null;
                    }}
                }}
                return null;
            }})()
            """
        }, 1)
        sid = resp.get("result", {}).get("result", {}).get("value")
        if sid:
            strategy_name_or_id = sid

    # 导航到策略页面
    strategy_url = f"https://ycgr.fcsc.com/stock/strategy?sid={strategy_name_or_id}"
    ws_command(ws, "Page.navigate", {"url": strategy_url}, 2)
    time.sleep(4)

    # 提取策略数据
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            var text = document.body.innerText;
            var result = {};

            // 策略名
            var nameMatch = text.match(/^(yaanlmc-v-[\\d.]+|王春花分享的策略|[^\\n]+)/m);
            result.name = nameMatch ? nameMatch[1].trim() : null;

            // 创建日期
            var createdMatch = text.match(/创建日期[:\\s]*(\\d{4}/\\d{2}/\\d{2})/);
            result.created_date = createdMatch ? createdMatch[1] : null;

            // 下个调仓
            var nextRebalanceMatch = text.match(/下个调仓[:\\s]*(\\d{4}/\\d{2}/\\d{2})/);
            result.next_rebalance = nextRebalanceMatch ? nextRebalanceMatch[1] : null;

            // 年化收益
            var annualMatch = text.match(/年化收益[^\\d]*([\\d.]+)%/);
            result.annual_return = annualMatch ? annualMatch[1] + "%" : null;

            // 夏普比率
            var sharpeMatch = text.match(/夏普比率[^\\d]*([\\d.]+)/);
            result.sharpe_ratio = sharpeMatch ? sharpeMatch[1] : null;

            // 最大回撤
            var drawdownMatch = text.match(/最大回撤[^\\d]*([\\d.]+)%/);
            result.max_drawdown = drawdownMatch ? drawdownMatch[1] + "%" : null;

            // 持仓股票数
            var holdingsMatch = text.match(/持仓股票[:\\s]*(\\d+)只/);
            result.holdings_count = holdingsMatch ? holdingsMatch[1] : null;

            return JSON.stringify(result);
        })()
        """
    }, 3)

    strategy_data = json.loads(resp.get("result", {}).get("result", {}).get("value", "{}"))

    # 提取持仓明细
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            var text = document.body.innerText;
            var holdings = [];

            // 查找持仓表格
            var lines = text.split('\\n');
            for(var i=0; i<lines.length; i++){
                var line = lines[i];
                // 匹配股票代码 (60xxxx, 00xxxx, 30xxxx)
                var codeMatch = line.match(/\\((\\d{6})\\)/);
                if(codeMatch){
                    var stock = {code: codeMatch[1]};
                    // 提取股票名
                    var nameMatch = line.match(/^([^(]+)\\(/);
                    stock.name = nameMatch ? nameMatch[1].trim() : null;

                    // 提取后面的数字
                    var nums = line.match(/[\\d,.]+%?/g);
                    if(nums && nums.length >= 3){
                        stock.position_pct = nums[0];
                        stock.cumulative_return = nums[nums.length - 1];
                    }

                    holdings.push(stock);
                }
            }

            return JSON.stringify(holdings);
        })()
        """
    }, 4)

    holdings = json.loads(resp.get("result", {}).get("result", {}).get("value", "[]"))

    # 提取调仓指令
    resp = ws_command(ws, "Runtime.evaluate", {
        "expression": """
        (function() {
            var text = document.body.innerText;
            var orders = [];

            // 查找调仓指令部分
            var idx = text.indexOf('调仓指令');
            if(idx >= 0){
                var orderText = text.substring(idx, idx + 2000);
                var lines = orderText.split('\\n');

                for(var i=0; i<lines.length; i++){
                    var line = lines[i];
                    var codeMatch = line.match(/\\((\\d{6})\\)/);
                    if(codeMatch && (line.indexOf('买入') >= 0 || line.indexOf('卖出') >= 0 || line.indexOf('持有') >= 0)){
                        var order = {code: codeMatch[1]};

                        if(line.indexOf('买入') >= 0) order.action = '买入';
                        else if(line.indexOf('卖出') >= 0) order.action = '卖出';
                        else order.action = '持有';

                        orders.push(order);
                    }
                }
            }

            return JSON.stringify(orders);
        })()
        """
    }, 5)

    orders = json.loads(resp.get("result", {}).get("result", {}).get("value", "[]"))

    ws.close()

    return {
        "strategy": strategy_data,
        "holdings": holdings,
        "orders": orders
    }


def main():
    parser = argparse.ArgumentParser(description="一创果仁网实盘查询工具")
    parser.add_argument("--login", action="store_true", help="登录一创果仁网")
    parser.add_argument("--phone", help="手机号")
    parser.add_argument("--password", help="密码")
    parser.add_argument("--overview", action="store_true", help="获取账户总览")
    parser.add_argument("--strategies", action="store_true", help="获取策略列表")
    parser.add_argument("--strategy", help="获取指定策略详情")
    parser.add_argument("--holdings", action="store_true", help="获取持仓明细")
    parser.add_argument("--rebalance", action="store_true", help="获取调仓指令")

    args = parser.parse_args()

    if args.login:
        if not args.phone or not args.password:
            print("错误: 登录需要 --phone 和 --password 参数")
            sys.exit(1)
        success = login(args.phone, args.password)
        sys.exit(0 if success else 1)

    elif args.overview:
        data = get_overview()
        print("\n📊 账户总览")
        print("-" * 30)
        for key, value in data.items():
            if value:
                print(f"{key}: {value}")

    elif args.strategies:
        strategies = get_strategies()
        print("\n📈 策略列表")
        print("-" * 50)
        for s in strategies:
            print(f"{s.get('name', 'N/A')}: 市值 {s.get('holding_value', 'N/A')}, 日收益 {s.get('daily_return', 'N/A')}")

    elif args.strategy:
        detail = get_strategy_detail(args.strategy)
        print("\n📊 策略详情")
        print("-" * 50)
        for key, value in detail["strategy"].items():
            if value:
                print(f"{key}: {value}")

        if detail["holdings"]:
            print("\n📋 持仓明细")
            for h in detail["holdings"]:
                print(f"  {h.get('name', 'N/A')} ({h.get('code', 'N/A')}): {h.get('position_pct', 'N/A')}")

        if detail["orders"]:
            print("\n🔄 调仓指令")
            for o in detail["orders"]:
                print(f"  {o.get('code', 'N/A')}: {o.get('action', 'N/A')}")

    elif args.holdings:
        # 获取持仓（需要先进入策略或账户总览）
        data = get_overview()
        print("\n📋 持仓数据")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
