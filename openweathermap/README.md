# OpenWeatherMap MCP Server

Weather data, forecasts, and air quality from [OpenWeatherMap](https://openweathermap.org/).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetCurrentWeather` | Yes | Get current weather conditions for a city |
| `GetCurrentWeatherByCoords` | Yes | Get current weather by geographic coordinates |
| `GetForecast` | Yes | Get 5-day / 3-hour weather forecast for a city |
| `GetAirQuality` | Yes | Get air quality data for a location |
| `GetUVIndex` | Yes | Get the current UV index for a location |
| `GetGeocode` | Yes | Geocode a city name to latitude/longitude coordinates |
| `GetReverseGeocode` | Yes | Reverse geocode coordinates to location names |
| `GetOneCall` | Yes | Get comprehensive weather data (current + forecast + alerts) |
| `GetHistoricalWeather` | Yes | Get historical weather data for a specific time |
| `GetWeatherMap` | Yes | Get weather map tile URL for overlay maps |

## Quick start

```bash
# Install
cd openweathermap
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
OPENWEATHERMAP_API_KEY=your-key uv run python main.py

# Run as CLI
uv run python main.py --cli OpenWeatherMapService GetCurrentWeather -r '{"city": "London"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Required. Set `OPENWEATHERMAP_API_KEY`. Get a free key at https://openweathermap.org/api.

## MCP config

```json
{
  "mcpServers": {
    "openweathermap": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/openweathermap", "python", "main.py"],
      "env": {
        "OPENWEATHERMAP_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
