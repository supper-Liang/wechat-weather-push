#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信测试号每日天气推送脚本（增强版）

功能：
    1. 通过和风天气 API 获取指定城市的实时天气与未来天气
       （API Host 通过 QWEATHER_HOST 环境变量配置，兼容新版 devapi/api 域名）
    2. 通过微信公众平台测试号模板消息接口推送给指定用户
    3. 支持恋爱天数计算（LOVE_DATE）
    4. 支持女友生日倒计时（BIRTHDAY，可选）
    5. 每日甜蜜提醒、每日问候、丰富情话池

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
# 常量：星期、情话、提醒、问候
# ----------------------------------------------------------------------
WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# 情话池（35+ 条，原有 20 条 + 新增 17 条）
LOVE_SAYINGS = [
    # ---- 原有 20 条 ----
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
    # ---- 新增 17 条（更接地气）----
    "做你的专属天气预报员，是我最甜蜜的工作。",
    "想和你一起淋一场雨，然后一起感冒，一起吃药。",
    "你知道吗？每次写这条消息的时候，我都在偷偷想你。",
    "如果可以的话，我想把整个世界的温柔都给你。",
    "今天的天气不如你好看。",
    "你是限定的，也是唯一的。",
    "我的宇宙里全是你闪烁的光。",
    "见到你的那天，星河与夏蝉共鸣。",
    "你是所有美好的代名词。",
    "有你的日子，连阴天都觉得温暖。",
    "余生不用你指教了，都听你的。",
    "全世界都在赶路，你却温暖了我的心。",
    "遇到你之后，生活变甜了。",
    "今天的风好温柔，就像你看着我的眼神。",
    "我这一生，唯一不可以辜负的，就是你。",
    "想牵你的手，从清晨牵到日暮，从初春牵到深冬。",
    "一辈子那么长，我想一直把你放在心上。",
]

# 每日甜蜜提醒池（18 条）
DAILY_REMINDERS = [
    "记得想我哦~ 💭",
    "今天也要开开心心的呀~ 🌈",
    "无论多忙，都要好好吃饭哦~ 🍚",
    "记得多喝水呀，别等渴了再喝~ 💧",
    "工作再忙也要注意休息哦~ 💤",
    "出门在外注意安全，到了跟我说一声~ 🏠",
    "今天有没有想我呀？反正我很想你~ 💕",
    "保持好心情，你笑起来最好看了~ 😊",
    "不开心的时候来找我，我随时都在~ 🤗",
    "今天也是爱你的一天~ ❤️",
    "记得早点睡觉，熬夜对皮肤不好哦~ 🌙",
    "你是我今天份的小幸运~ 🍀",
    "累了就停下来歇一会儿，世界不会因此停下~ ☕",
    "天冷加衣，天热防晒，宝贝要照顾好自己~ 🌸",
    "记得抬头看看天空，云很美，但没你美~ ☁️",
    "今天也要元气满满呀，加油鸭！🦆",
    "想你想得睡不着，又想你想得睡得很香~ 🌟",
    "亲爱的，别忘了对自己好一点哦~ 🎀",
]

# 每日问候语（按星期几）
WEEKDAY_GREETINGS = [
    "新的一周开始了，加油鸭！💪",          # 周一
    "周二元气满满的一天～",                  # 周二
    "周三了，一周已过半，继续加油～",        # 周三
    "明天就是周五啦，再坚持一下～",          # 周四
    "周五！快乐的周末在向你招手～🎉",        # 周五
    "周末快乐！好好享受休息时光吧～🎈",      # 周六
    "周日愉快，为下周充充电～☀️",           # 周日
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


def birthday_countdown(birthday_md: str) -> Optional[int]:
    """
    计算距离下一次生日还有多少天。

    参数:
        birthday_md: MM-DD 格式的生日，如 "08-15"

    返回:
        - None: 解析失败
        - 0:    今天就是生日
        - N>0:  距离下次生日还有 N 天
    """
    try:
        month, day = birthday_md.strip().split("-")
        month, day = int(month), int(day)
    except (ValueError, AttributeError):
        logger.warning(f"BIRTHDAY 格式错误，应为 MM-DD，实际为：{birthday_md}")
        return None

    today = datetime.date.today()
    try:
        this_year_birthday = datetime.date(today.year, month, day)
    except ValueError:
        logger.warning(f"BIRTHDAY 日期不合法：{birthday_md}")
        return None

    if this_year_birthday == today:
        return 0
    if this_year_birthday < today:
        # 今年生日已过，计算到明年生日
        try:
            next_birthday = datetime.date(today.year + 1, month, day)
        except ValueError:
            # 处理 02-29 这种闰年特殊情况
            next_birthday = datetime.date(today.year + 1, month, 28)
    else:
        next_birthday = this_year_birthday

    return (next_birthday - today).days


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


def make_greeting(weather_text: str) -> str:
    """生成每日问候语：基于星期几，并融合天气元素。"""
    weekday = datetime.date.today().weekday()
    base = WEEKDAY_GREETINGS[weekday]

    # 根据天气追加一点应景的小尾巴
    weather = weather_text or ""
    if any(k in weather for k in ["雨", "雷"]):
        base += " 今天有雨，记得带伞~"
    elif "雪" in weather:
        base += " 外面下雪了，注意保暖~"
    elif "晴" in weather:
        base += " 阳光不错，心情也要明媚~"
    elif any(k in weather for k in ["雾", "霾"]):
        base += " 雾蒙蒙的，路上小心~"

    return base


def make_love_days_text(love_start: str) -> str:
    """生成"在一起天数"展示文本。"""
    if not love_start:
        return "每一天和你在一起都值得纪念 ❤️"
    days = love_days(love_start)
    if days <= 0:
        return "和你的故事，从今天开始 ❤️"
    return f"今天是我们在一起的第 {days} 天 ❤️"


def make_birthday_text(birthday_md: str) -> str:
    """生成生日倒计时展示文本。"""
    if not birthday_md:
        return "宝贝的每一天都是我心里的节日 🎂"
    days = birthday_countdown(birthday_md)
    if days is None:
        return "宝贝的每一天都是我心里的节日 🎂"
    if days == 0:
        return "今天是你的生日！祝宝贝生日快乐！🎂🎉"
    return f"距离宝贝生日还有 {days} 天 🎂"


# ----------------------------------------------------------------------
# 和风天气 API（Host 通过环境变量配置）
# ----------------------------------------------------------------------
QWEATHER_HOST = os.getenv("QWEATHER_HOST", "api.qweather.com")
QWEATHER_NOW_URL = f"https://{QWEATHER_HOST}/v7/weather/now"
QWEATHER_3D_URL = f"https://{QWEATHER_HOST}/v7/weather/3d"


def fetch_weather(city_id: str, key: str) -> Dict[str, Any]:
    """获取实时天气与未来三天天气信息。"""
    logger.info(f"开始请求和风天气 API，Host：{QWEATHER_HOST}，城市ID：{city_id}")

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
    birthday_md: str,
) -> Dict[str, Dict[str, str]]:
    """组装符合模板要求的数据字段，并附带颜色。"""

    saying = random.choice(LOVE_SAYINGS)
    reminder = random.choice(DAILY_REMINDERS)
    tips = make_tips(weather["temp"], weather["weather"])
    greeting = make_greeting(weather["weather"])
    love_days_text = make_love_days_text(love_start)
    birthday_text = make_birthday_text(birthday_md)

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
        "greeting": {
            "value": greeting,
            "color": "#7B68EE",
        },
        "love_days": {
            "value": love_days_text,
            "color": "#FF1493",
        },
        "birthday": {
            "value": birthday_text,
            "color": "#FF69B4",
        },
        "daily_reminder": {
            "value": reminder,
            "color": "#DA70D6",
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
    logger.info("===== 每日天气推送任务开始（增强版）=====")

    app_id = get_env("APP_ID")
    app_secret = get_env("APP_SECRET")
    template_id = get_env("TEMPLATE_ID")
    user_id = get_env("USER_ID")
    qweather_key = get_env("QWEATHER_KEY")
    city = get_env("CITY")
    city_id = get_env("CITY_ID")
    love_date = get_env("LOVE_DATE", required=False, default="")
    birthday = get_env("BIRTHDAY", required=False, default="")

    logger.info(
        f"配置概览：城市={city}，城市ID={city_id}，"
        f"LOVE_DATE={'已配置' if love_date else '未配置'}，"
        f"BIRTHDAY={'已配置' if birthday else '未配置'}，"
        f"QWEATHER_HOST={QWEATHER_HOST}"
    )

    try:
        weather = fetch_weather(city_id, qweather_key)
        access_token = get_access_token(app_id, app_secret)
        data = build_template_data(city, weather, love_date, birthday)
        send_template_message(access_token, template_id, user_id, data)
    except Exception as e:
        logger.exception(f"推送任务失败：{e}")
        sys.exit(1)

    logger.info("===== 每日天气推送任务完成 =====")


if __name__ == "__main__":
    main()


# ======================================================================
# 附加说明（用户操作指引）
# ======================================================================
#
# ----------------------------------------------------------------------
# 一、新的微信测试号模板消息格式（请到测试号后台替换）
# ----------------------------------------------------------------------
#
# 标题建议：每日天气与爱的提醒
#
# 模板内容（每行对应一个 {{字段.DATA}}，复制到测试号"新增测试模板"中）：
#
# {{greeting.DATA}}
#
# 📅 日期：{{date.DATA}}
# 📍 城市：{{city.DATA}}
# ☁️ 天气：{{weather.DATA}}
# 🌡️ 当前温度：{{temp.DATA}}
# 🔺 最高温：{{high.DATA}}
# 🔻 最低温：{{low.DATA}}
# 🍃 风况：{{wind.DATA}}
# 💧 湿度：{{humidity.DATA}}
#
# 👕 贴心提示：{{tips.DATA}}
#
# ❤️ {{love_days.DATA}}
# 🎂 {{birthday.DATA}}
# 💌 {{daily_reminder.DATA}}
#
# 💞 今日情话：{{saying.DATA}}
#
# ----------------------------------------------------------------------
# 二、新增的 GitHub Secrets 说明
# ----------------------------------------------------------------------
#
# 在 GitHub 仓库 Settings -> Secrets and variables -> Actions 中新增：
#
#   名称：BIRTHDAY
#   值：女友生日，格式 MM-DD（例如 08-15）
#   说明：可选 Secret。配置后将启用生日倒计时功能；
#         不配置时，birthday 字段会显示为友好的默认文案。
#
# （已有 Secrets 列表：APP_ID / APP_SECRET / TEMPLATE_ID / USER_ID /
#   QWEATHER_KEY / QWEATHER_HOST / CITY / CITY_ID / LOVE_DATE）
#
# ----------------------------------------------------------------------
# 三、workflow 文件（.github/workflows/weather-push.yml）需新增的环境变量行
# ----------------------------------------------------------------------
#
# 在 job 的 env 部分新增一行（与已有的 QWEATHER_HOST 等并列）：
#
#   env:
#     APP_ID:        ${{ secrets.APP_ID }}
#     APP_SECRET:    ${{ secrets.APP_SECRET }}
#     TEMPLATE_ID:   ${{ secrets.TEMPLATE_ID }}
#     USER_ID:       ${{ secrets.USER_ID }}
#     QWEATHER_KEY:  ${{ secrets.QWEATHER_KEY }}
#     QWEATHER_HOST: ${{ secrets.QWEATHER_HOST }}
#     CITY:          ${{ secrets.CITY }}
#     CITY_ID:       ${{ secrets.CITY_ID }}
#     LOVE_DATE:     ${{ secrets.LOVE_DATE }}
#     BIRTHDAY:      ${{ secrets.BIRTHDAY }}      # ← 新增此行
#
# ======================================================================
