# StockSense API Documentation

## System Health

### Get Health Status

Checks the operational status of the StockSense API backend.

- **URL:** `/api/health`
- **Method:** `GET`
- **Authentication:** None
- **Response Headers:** `Content-Type: application/json`

#### Success Response (200 OK)

```json
{
  "status": "ok",
  "app_name": "StockSense API",
  "environment": "development"
}
```

#### Fields

| Field | Type | Description |
|---|---|---|
| `status` | String | Health status indicator (`ok`) |
| `app_name` | String | Application title (`StockSense API`) |
| `environment` | String | Active deployment environment (`development`, `staging`, `production`) |
