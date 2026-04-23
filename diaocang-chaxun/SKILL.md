---
name: diaocang-chaxun
description: |
  一创果仁网（ycgr.fcsc.com）实盘策略与持仓查询。

  当用户需要查询一创果仁网的实盘策略、持仓明细、调仓指令时使用此 skill。

  触发关键词：一创果仁、果仁网、调仓、持仓查询、策略查询、ycgr、fcsc、实盘管家。

  支持功能：
  1. 登录一创果仁网（需要账号密码）
  2. 查看账户总览（总资产、持仓市值、可用现金）
  3. 查看所有策略列表及收益
  4. 进入指定策略查看详情
  5. 查看持仓明细和调仓指令
---

# 调仓查询 — 一创果仁网实盘查询

## 概述

此 skill 用于自动化操作一创果仁网（ycgr.fcsc.com），实现实盘策略与持仓的查询。

## 前置条件

1. **Chrome 浏览器**：需要安装 Chrome 并启用远程调试
2. **登录凭证**：需要用户提供手机号和密码
3. **websocket-client**：Python 依赖，用于 CDP 通信

## 快速开始

### 1. 启动 Chrome（远程调试模式）

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --user-data-dir=/tmp/chrome-debug

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --remote-allow-origins=* ^
  --user-data-dir=%TEMP%\chrome-debug
```

### 2. 登录并查询

使用脚本自动登录并获取数据：

```bash
python3 "{SKILL_DIR}/scripts/ycgr.py" --login --phone <手机号> --password <密码>
python3 "{SKILL_DIR}/scripts/ycgr.py" --holdings
python3 "{SKILL_DIR}/scripts/ycgr.py" --strategy <策略名或ID>
```

## 工作流程

### 登录流程

1. 导航到 https://ycgr.fcsc.com
2. 检测是否已登录（用户名显示）
3. 若未登录，点击登录按钮
4. 填写手机号和密码（使用键盘模拟，适配 React 表单）
5. 提交登录，验证成功

### 查询流程

**账户总览**：
- URL: `https://ycgr.fcsc.com/trader/home?id=<账户ID>&page=holdings`
- 提取：当前净值、总资产、持仓市值、可用现金
- 提取：策略列表（名称、市值、收益率）

**策略详情**：
- URL: `https://ycgr.fcsc.com/stock/strategy?sid=<策略ID>`
- 提取：策略概览（创建日期、调仓时点、持仓股票数）
- 提取：收益统计（年化收益、夏普比率、最大回撤）
- 提取：最新持仓（股票、仓位、买入价、涨幅）
- 提取：调仓指令（买入/卖出/持有）

## 命令参考

### `scripts/ycgr.py`

```bash
# 登录
python3 ycgr.py --login --phone 18080155660 --password xxxxxxxx

# 查看账户总览
python3 ycgr.py --overview

# 查看所有策略
python3 ycgr.py --strategies

# 查看指定策略详情
python3 ycgr.py --strategy "yaanlmc-v-1.9"

# 查看当前持仓
python3 ycgr.py --holdings

# 查看调仓指令
python3 ycgr.py --rebalance
```

## 注意事项

1. **表单填写**：一创果仁网使用 React，简单的 `.value` 赋值不会触发事件，必须使用键盘模拟
2. **验证码**：当前不支持验证码自动识别，如有验证码需用户手动输入
3. **会话保持**：Chrome 调试模式会保持登录状态，无需重复登录
4. **策略 ID**：策略链接包含 `sid` 参数，格式为 `sid=105503.R.xxxxx`

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| WebSocket 403 | 缺少 `--remote-allow-origins` | 启动 Chrome 时加上此参数 |
| 元素未找到 | 页面未加载完成 | 增加等待时间 |
| 登录失败 | 密码错误或验证码 | 检查凭证，手动处理验证码 |

## 资源文件

- `scripts/ycgr.py` - 主脚本，封装所有操作
- `references/fields.md` - 页面字段映射参考
