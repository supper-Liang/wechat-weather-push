#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信测试号每日天气推送脚本
功能：
    1. 通过和风天气 API 获取指定城市的实时天气与未来天气
    2. 通过微信公众平台测试号模板消息接口推送给指定用户
    3. 支持恋爱天数计算与随机情话推送

所有敏感配置均通过环境变量读取，适配 GitHub Actions Secrets。
"""

import os
import sys
import random
import logging
import datetime
from typing import Dict, Any, Optional

import requests

# ----------------------------------------------------------------------
# 日志配置
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("weather-push")


# ----------------------------------------------------------------------
# 常量：星期、情话
# ----------------------------------------------------------------------
WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

LOVE_SAYINGS = [
    "遇见你，是我此生最美的意外。",
    "你是我心头那一抹挥之不去的温柔。",
    "愿你三冬暖，愿你春不寒；愿你天黑有灯，下雨有伞。",
    "我所有的勇敢，都是因为有你。",
    "山有木兮木有枝，心悦君兮君不知，但我希望你知道。",
    "你是我清晨的第一缕阳光，也是我夜里最亮的星。",
    "陪你走过的每一天，都值得纪念。",
    "余生很长，请多指教，我亲爱的姑娘。",
    "我喜欢你，没有理由，没有原因，只因为是你。",
    "在这个世界上，我最想做的事，就是和你共度余生。",
    "你笑起来真好看，像春天的花一样。",
    "想把世界上所有的好东西都送给你，但发现，我自己就是最好的。",
    "时光匆匆，我只想牵着你的手，慢慢走完这一生。",
    "今天也想和你说一声：我爱你。",
    "无论今天天气如何，记得带上我的爱出门哦。",
    "愿我成为你的小确幸，每天都让你开心一点点。",
    "想你的风，又吹了一整天。",
    "你是我枯燥生活里的一束光。",
    "你若安好，便是晴天；你若快乐，便是终年。",
    "因为你，我愿意做一个更好的人。",
]


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def get_env(key: str, required: bool = True, default: Optional[str] = None) -> str:
    """读取环境变量，必填项缺失时直接退出。"""
    value = os.environ.get(key, default)
    if required and (value is None or value.strip() == ""):
        logger.error(f"缺少必需的环境变量：{key}")
        sys.exit(1)
    return value or ""


def today_str() -> str:
    """返回 yyyy年MM月dd日 星期X 格式的日期字符串。"""
    now = datetime.datetime.now()
    return f"{now.strftime('%Y年%m月%d日')} {WEEKDAY_CN[now.weekday()]}"


def love_days(start_date: str) -> int:
    """计算从起始日期到今天的恋爱天数。"""
    try:
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"LOVE_DATE 格式错误，应为 YYYY-MM-DD，实际为：{start_date}")
        return 0
    today = datetime.date.today()
    return (today - start).days


def make_tips(temp: float, weather_text: str) -> str:
    """根据温度和天气状况生成穿衣/出行建议。"""
    tips = []

    # 温度建议
    if temp <= 0:
        tips.append("天气严寒，记得穿羽绒服并戴好围巾手套~")
    elif temp <= 10:
        tips.append("天气较冷，外套加毛衣会更暖和哦~")
    elif temp <= 18:
        tips.append("微凉，记得添件薄外套，别着凉啦~")
    elif temp <= 26:
        tips.append("温度宜人，长袖衬衫或薄卫衣都很合适~")
    elif temp <= 32:
        tips.append("有点小热，短袖透气最舒服啦~")
    else:
        tips.append("天气炎热，注意防晒补水，避免长时间户外活动~")

    # 天气建议
    weather = weather_text or ""
    if any(k in weather for k in ["雨", "雷"]):
        tips.append("今天有雨，出门记得带把伞哦☂️")
    if "雪" in weather:
        tips.append("今天有雪，路面湿滑，注意保暖与脚下安全~")
    if any(k in weather for k in ["雾", "霾"]):
        tips.append("能见度较低，出行注意交通安全，建议戴口罩~")
    if "晴" in weather and temp >= 28:
        tips.append("阳光强烈，记得涂防晒霜哦～")

    return "、".join(tips)


# ----------------------------------------------------------------------
# 和风天气 API
# ----------------------------------------------------------------------
QWEATHER_HOST = os.getenv("QWEATHER_HOST", "api.qweather.com")
QWEATHER_NOW_URL = f"https://{QWEATHER_HOST}/v7/weather/now"
QWEATHER_3D_URL = f"https://{QWEATHER_HOST}/v7/weather/3d"


def fetch_weather(city_id: str, key: str) -> Dict[str, Any]:
    """获取实时天气与未来三天天气信息。"""
    logger.info(f"开始请求和风天气 API，城市ID：{city_id}")

    try:
        now_resp = requests.get(
            QWEATHER_NOW_URL,
            params={"location": city_id, "key": key},
            timeout=10,
        )
        now_data = now_resp.json()
        if now_data.get("code") != "200":
            raise RuntimeError(f"实时天气接口返回异常：{now_data}")

        forecast_resp = requests.get(
            QWEATHER_3D_URL,
            params={"location": city_id, "key": key},
            timeout=10,
        )
        forecast_data = forecast_resp.json()
        if forecast_data.get("code") != "200":
            raise RuntimeError(f"未来天气接口返回异常：{forecast_data}")

    except requests.RequestException as e:
        logger.error(f"请求和风天气 API 网络异常：{e}")
        raise

    now = now_data["now"]
    today = forecast_data["daily"][0]

    result = {
        "weather": now.get("text", "未知"),       # 当前天气状况
        "temp": float(now.get("temp", 0)),         # 当前温度
        "wind_dir": now.get("windDir", ""),        # 风向
        "wind_scale": now.get("windScale", ""),    # 风力等级
        "humidity": now.get("humidity", ""),       # 湿度
        "high": today.get("tempMax", ""),          # 今日最高温
        "low": today.get("tempMin", ""),           # 今日最低温
    }
    logger.info(f"天气数据获取成功：{result}")
    return result


# ----------------------------------------------------------------------
# 微信测试号 API
# ----------------------------------------------------------------------
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_TEMPLATE_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"


def get_access_token(app_id: str, app_secret: str) -> str:
    """获取微信公众平台 access_token。"""
    logger.info("开始获取微信 access_token")
    try:
        resp = requests.get(
            WECHAT_TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret,
            },
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"获取 access_token 网络异常：{e}")
        raise

    if "access_token" not in data:
        raise RuntimeError(f"获取 access_token 失败：{data}")

    logger.info("access_token 获取成功")
    return data["access_token"]


def send_template_message(
    access_token: str,
    template_id: str,
    user_id: str,
    data: Dict[str, Dict[str, str]],
) -> None:
    """调用模板消息接口发送消息。"""
    logger.info(f"开始向用户 {user_id} 推送模板消息")
    payload = {
        "touser": user_id,
        "template_id": template_id,
        "data": data,
    }
    try:
        resp = requests.post(
            WECHAT_TEMPLATE_URL,
            params={"access_token": access_token},
            json=payload,
            timeout=10,
        )
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"推送模板消息网络异常：{e}")
        raise

    if result.get("errcode") != 0:
        raise RuntimeError(f"推送模板消息失败：{result}")
    logger.info(f"模板消息推送成功，msgid={result.get('msgid')}")


# ----------------------------------------------------------------------
# 模板消息数据组装
# ----------------------------------------------------------------------
def build_template_data(
    city: str,
    weather: Dict[str, Any],
    love_start: str,
) -> Dict[str, Dict[str, str]]:
    """组装符合模板要求的数据字段，并附带颜色。"""

    saying = random.choice(LOVE_SAYINGS)
    tips = make_tips(weather["temp"], weather["weather"])
    days = love_days(love_start) if love_start else 0

    return {
        "date": {
            "value": today_str(),
            "color": "#173177",
        },
        "city": {
            "value": city,
            "color": "#1E90FF",
        },
        "weather": {
            "value": weather["weather"],
            "color": "#00BFFF",
        },
        "temp": {
            "value": f"{weather['temp']}℃",
            "color": "#FF6347",
        },
        "high": {
            "value": f"{weather['high']}℃",
            "color": "#FF4500",
        },
        "low": {
            "value": f"{weather['low']}℃",
            "color": "#1E90FF",
        },
        "wind": {
            "value": f"{weather['wind_dir']} {weather['wind_scale']}级",
            "color": "#32CD32",
        },
        "humidity": {
            "value": f"{weather['humidity']}%",
            "color": "#20B2AA",
        },
        "tips": {
            "value": tips,
            "color": "#FF8C00",
        },
        "love_days": {
            "value": f"我们已经在一起 {days} 天啦 ❤️",
            "color": "#FF1493",
        },
        "saying": {
            "value": saying,
            "color": "#C71585",
        },
    }


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------
def main() -> None:
    logger.info("===== 每日天气推送任务开始 =====")

    app_id = get_env("APP_ID")
    app_secret = get_env("APP_SECRET")
    template_id = get_env("TEMPLATE_ID")
    user_id = get_env("USER_ID")
    qweather_key = get_env("QWEATHER_KEY")
    city = get_env("CITY")
    city_id = get_env("CITY_ID")
    love_date = get_env("LOVE_DATE", required=False, default="")

    try:
        weather = fetch_weather(city_id, qweather_key)
        access_token = get_access_token(app_id, app_secret)
        data = build_template_data(city, weather, love_date)
        send_template_message(access_token, template_id, user_id, data)
    except Exception as e:
        logger.exception(f"推送任务失败：{e}")
        sys.exit(1)

    logger.info("===== 每日天气推送任务完成 =====")


if __name__ == "__main__":
    main()
