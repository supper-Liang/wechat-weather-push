# -*- coding: utf-8 -*-
"""
配置模板（仅供本地调试参考）
请勿将真实密钥提交到仓库！

正式部署请使用 GitHub Actions Secrets，由 main.py 通过环境变量读取。
本地调试时可将下列变量复制到一个 .env 文件，并使用 python-dotenv 加载，
或在 PowerShell 中通过 $env:APP_ID="xxx" 的方式逐项设置。
"""

# ---------- 微信测试号 ----------
APP_ID = "你的微信测试号 appID"
APP_SECRET = "你的微信测试号 appSecret"
TEMPLATE_ID = "你的模板消息ID"
USER_ID = "接收者的 OpenID"

# ---------- 和风天气 ----------
QWEATHER_KEY = "你在和风天气控制台申请的 API Key"
CITY = "北京"
CITY_ID = "101010100"   # 和风天气城市ID，可在 https://github.com/qwd/LocationList 查询

# ---------- 恋爱起始日 ----------
LOVE_DATE = "2023-01-01"   # 格式必须为 YYYY-MM-DD
