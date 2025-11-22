"""Weather lookup using open-meteo without API key."""

from __future__ import annotations

from typing import Any, Dict

from qwen_agent.tools.base import register_tool
from tools.base import QwenAgentBaseTool

from tools.common import dump, safe_get_json

GEOCODE_API = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"

@register_tool("weather")
class WeatherTool(QwenAgentBaseTool):
    description = "查询城市当前天气与预报（使用 open-meteo 公共接口）。"
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，必填，如 Beijing、Shanghai、San Francisco"
            }
        },
        "required": ["city"],
    }

    def _execute_tool(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        city = args["city"]
        geo = _geocode_city(city)
        if geo.get("status") == "error":
            return dump(geo)

        lat = geo["lat"]
        lon = geo["lon"]
        status, forecast = safe_get_json(
            f"{FORECAST_API}?latitude={lat}&longitude={lon}&current_weather=true&hourly=temperature_2m,relativehumidity_2m,weathercode"
        )
        if status == "error":
            return dump({"task": "weather", "status": status, "error": forecast.get("error")})

        current = forecast.get("current_weather") or {}
        temp = current.get("temperature")
        wind = current.get("windspeed")
        code = current.get("weathercode")
        return (
            f"{geo['name']} 当前天气\n"
            f"- 温度: {temp}°C\n"
            f"- 风速: {wind} km/h\n"
            f"- 天气代码: {code}\n"
            f"(lat={lat}, lon={lon})"
        )


def _geocode_city(city: str) -> Dict:
    status, payload = safe_get_json(f"{GEOCODE_API}?name={city}&count=1&language=zh&format=json")
    if status == "error":
        return {"task": "weather", "status": status, "error": payload.get("error")}
    results = payload.get("results") or []
    if not results:
        return {"task": "weather", "status": "error", "error": f"未找到城市: {city}"}
    item = results[0]
    return {
        "task": "weather",
        "status": "ok",
        "name": item.get("name") or city,
        "lat": item.get("latitude"),
        "lon": item.get("longitude"),
    }
