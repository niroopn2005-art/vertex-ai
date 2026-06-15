#!/usr/bin/env python3
"""
Model Context Protocol (MCP) Weather Server Example

This script runs an MCP server that exposes weather search tools. 
Since OpenClaw supports the Model Context Protocol, you can configure OpenClaw 
to run this server, immediately giving your AI agents access to real-time weather details.

Requirements:
    pip install mcp

Usage:
    # Run the server on standard IO (for OpenClaw config integration):
    python mcp_weather_server.py

Configuration in OpenClaw:
    Mount this server by adding it to your `~/.openclaw/openclaw.json` config under `mcp.servers`:
    {
      "mcp": {
        "servers": {
          "weather-service": {
            "command": "python",
            "args": ["/absolute/path/to/examples/python/mcp_weather_server.py"]
          }
        }
      }
    }
"""

import sys
import random
from typing import Dict, Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print(
        "Error: 'mcp' package is not installed. Please run: pip install mcp",
        file=sys.stderr
    )
    sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP("OpenClawWeatherService")

# Predefined mock database of cities
MOCK_WEATHER: Dict[str, Dict[str, Any]] = {
    "san francisco": {"temp": "62°F", "condition": "Sunny with light breeze", "humidity": "65%"},
    "new york": {"temp": "75°F", "condition": "Partly cloudy", "humidity": "50%"},
    "london": {"temp": "59°F", "condition": "Drizzle", "humidity": "88%"},
    "tokyo": {"temp": "68°F", "condition": "Clear sky", "humidity": "55%"},
    "sydney": {"temp": "71°F", "condition": "Windy", "humidity": "45%"},
    "paris": {"temp": "64°F", "condition": "Mostly cloudy", "humidity": "70%"},
}

@mcp.tool()
def get_weather(city: str) -> str:
    """
    Get the current weather conditions for a given city.
    
    Args:
        city: The name of the city (e.g. 'San Francisco', 'London')
    """
    normalized_city = city.strip().lower()
    
    if normalized_city in MOCK_WEATHER:
        data = MOCK_WEATHER[normalized_city]
        return (
            f"Current weather in {city.title()}:\n"
            f"- Temperature: {data['temp']}\n"
            f"- Conditions: {data['condition']}\n"
            f"- Humidity: {data['humidity']}"
        )
    else:
        # Fallback to simulated dynamic weather if city is not pre-registered
        temp = random.randint(45, 95)
        conditions = random.choice(["Sunny", "Cloudy", "Rainy", "Overcast", "Windy"])
        humidity = random.randint(30, 95)
        return (
            f"Current weather in {city.title()} (Simulated):\n"
            f"- Temperature: {temp}°F\n"
            f"- Conditions: {conditions}\n"
            f"- Humidity: {humidity}%"
        )

@mcp.tool()
def get_forecast(city: str, days: int = 3) -> str:
    """
    Retrieve a short-term weather forecast for a given city.
    
    Args:
        city: The name of the city (e.g. 'San Francisco', 'Paris')
        days: Number of forecast days (range 1-5, default 3)
    """
    days = max(1, min(5, days))
    normalized_city = city.strip().lower()
    
    conditions_pool = ["Sunny", "Partly Cloudy", "Rain Showers", "Thundershowers", "Foggy", "Overcast"]
    
    forecast_lines = [f"{days}-Day Weather Forecast for {city.title()}:"]
    
    for i in range(1, days + 1):
        day_temp_high = random.randint(60, 85)
        day_temp_low = day_temp_high - random.randint(10, 20)
        cond = random.choice(conditions_pool)
        forecast_lines.append(
            f"  Day {i}: High {day_temp_high}°F / Low {day_temp_low}°F | {cond}"
        )
        
    return "\n".join(forecast_lines)

if __name__ == "__main__":
    # Run the MCP server using standard input/output transport
    mcp.run()
