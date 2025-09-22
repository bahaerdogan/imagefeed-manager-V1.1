# API Documentation

## Overview
This document describes the API endpoints available in the Django Frame Processor application.

## Authentication
All API endpoints require authentication using Django's session-based authentication.

## Endpoints

### Health Check Endpoints

#### GET /health/
Basic health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0"
}
```

#### GET /health/db/
Database connectivity health check.

**Response:**
```json
{
    "status": "healthy",
    "service": "database",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /health/redis/
Redis connectivity health check.

**Response:**
```json
{
    "status": "healthy",
    "service": "redis",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

### Frame Management

#### POST /frames/create/
Create a new frame project.

**Parameters:**
- `name` (string): Frame project name
- `frame_image` (file): JPG/JPEG frame image (max 10MB)
- `feed_url` (string): XML feed URL (optional, defaults to case study feed)

**Response:** Redirects to preview page on success.

#### GET /frames/{id}/preview/
Preview and coordinate adjustment page.

#### POST /frames/{id}/preview-image/
Generate preview image with specified coordinates.

**Request Body:**
```json
{
    "x": 100,
    "y": 50,
    "width": 200,
    "height": 150
}
```

**Response:**
```json
{
    "success": true,
    "image": "data:image/jpeg;base64,..."
}
```

#### GET /frames/{id}/outputs-data/
DataTables-compatible endpoint for frame outputs.

**Parameters:**
- `draw` (int): DataTables draw counter
- `start` (int): Starting record number
- `length` (int): Number of records to return
- `search[value]` (string): Search term for product ID

**Response:**
```json
{
    "draw": 1,
    "recordsTotal": 100,
    "recordsFiltered": 50,
    "data": [
        ["product_id", "<img src='...' />", "2024-01-01 12:00", "<a href='...'>View</a>"]
    ]
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (authentication required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

Error responses include a JSON object with error details:
```json
{
    "error": "Error description",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Health checks: 60 requests per minute
- Preview generation: 30 requests per minute
- Other endpoints: 100 requests per minute

## Security

- All file uploads are validated for type and size
- URLs are validated to prevent SSRF attacks
- Input parameters are sanitized and validated
- CSRF protection is enabled for all POST requests