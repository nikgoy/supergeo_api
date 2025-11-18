# Sitemap Import Guide

Complete guide for importing URLs from sitemaps into the AI Cache Layer.

## Overview

The sitemap import feature allows you to automatically discover and cache all URLs from a website by parsing its sitemap. This is essential for:

1. **Initial setup** - Quickly populate the database with all pages from a site
2. **Bulk imports** - Import thousands of URLs in one operation
3. **Discovery** - Find all pages to cache without manual URL entry
4. **Updates** - Re-import to find new pages

## Quick Start

### 1. Basic Import

Import all URLs from a sitemap:

```bash
curl -X POST http://localhost:5000/api/v1/sitemap/import \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-master-api-key" \
  -d '{
    "client_id": "your-client-uuid",
    "sitemap_url": "https://example.com/sitemap.xml"
  }'
```

### 2. Preview Before Import

Check what URLs will be imported:

```bash
curl -X POST http://localhost:5000/api/v1/sitemap/parse \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-master-api-key" \
  -d '{
    "sitemap_url": "https://example.com/sitemap.xml"
  }'
```

### 3. List Imported Pages

View pages that were imported:

```bash
curl -H "X-API-Key: your-master-api-key" \
  "http://localhost:5000/api/v1/sitemap/client/{client_id}/pages?limit=50"
```

## Sitemap Formats Supported

### Regular Sitemap

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2024-01-01</lastmod>
    <priority>0.8</priority>
    <changefreq>weekly</changefreq>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
  </url>
</urlset>
```

### Sitemap Index

For sites with multiple sitemaps:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
    <lastmod>2024-01-01</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>
```

**Automatic Detection**: The parser automatically detects whether a sitemap is an index or regular sitemap.

## Import Options

### Recursive Import (Default)

Follows sitemap index references:

```json
{
  "client_id": "...",
  "sitemap_url": "https://example.com/sitemap.xml",
  "recursive": true,
  "max_depth": 3
}
```

- `recursive: true` - Follow nested sitemaps (default)
- `max_depth: 3` - Maximum nesting level (prevents infinite loops)

### Non-Recursive Import

Parse only the specified sitemap:

```json
{
  "client_id": "...",
  "sitemap_url": "https://example.com/sitemap-posts.xml",
  "recursive": false
}
```

### Overwrite Existing Pages

Update pages that already exist:

```json
{
  "client_id": "...",
  "sitemap_url": "https://example.com/sitemap.xml",
  "overwrite": true
}
```

- `overwrite: false` (default) - Skip existing URLs
- `overwrite: true` - Update existing pages

## Import Response

### Success Response

```json
{
  "message": "Sitemap imported successfully",
  "summary": {
    "total_urls": 150,
    "created": 145,
    "skipped": 5,
    "updated": 0,
    "errors": 0
  },
  "client": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Example Corp",
    "domain": "example.com"
  },
  "sitemap_url": "https://example.com/sitemap.xml"
}
```

**Summary Fields:**
- `total_urls` - Total URLs found in sitemap
- `created` - New pages created
- `skipped` - Existing pages skipped (or duplicates)
- `updated` - Pages updated (when `overwrite: true`)
- `errors` - URLs that failed to import

### Error Responses

**Client not found:**
```json
{
  "error": "Client not found"
}
```

**Invalid sitemap:**
```json
{
  "error": "Failed to parse sitemap",
  "message": "Invalid XML sitemap: ..."
}
```

**URL limit exceeded:**
```json
{
  "error": "Failed to parse sitemap",
  "message": "Exceeded maximum URL limit (10000)"
}
```

## Safety Limits

### URL Limit

Maximum 10,000 URLs per import operation.

**Why?** Prevents memory issues and database overload.

**Workaround:** Import multiple sitemaps separately:
```bash
# Import each section separately
curl ... -d '{"sitemap_url": "https://example.com/sitemap-posts.xml"}'
curl ... -d '{"sitemap_url": "https://example.com/sitemap-pages.xml"}'
```

### Timeout

HTTP requests timeout after 30 seconds (configurable via `PAGE_TIMEOUT` env var).

### Max Depth

Sitemap nesting limited to 3 levels deep (configurable).

## Common Workflows

### Initial Site Setup

1. Create client
2. Parse sitemap (preview)
3. Import sitemap
4. List pages to verify

```bash
# 1. Create client
CLIENT_ID=$(curl -X POST http://localhost:5000/api/v1/clients \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"name": "Example Corp", "domain": "example.com"}' \
  | jq -r '.client.id')

# 2. Preview sitemap
curl -X POST http://localhost:5000/api/v1/sitemap/parse \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"sitemap_url\": \"https://example.com/sitemap.xml\"}"

# 3. Import
curl -X POST http://localhost:5000/api/v1/sitemap/import \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d "{\"client_id\": \"$CLIENT_ID\", \"sitemap_url\": \"https://example.com/sitemap.xml\"}"

# 4. List pages
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:5000/api/v1/sitemap/client/$CLIENT_ID/pages?limit=10"
```

### Find Pages to Scrape

List all pages without content (not yet scraped):

```bash
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:5000/api/v1/sitemap/client/$CLIENT_ID/pages?has_content=false&limit=100"
```

### Update from Sitemap

Re-import to find new pages:

```bash
# Import with overwrite=false to skip existing
curl -X POST http://localhost:5000/api/v1/sitemap/import \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{
    "client_id": "...",
    "sitemap_url": "https://example.com/sitemap.xml",
    "overwrite": false
  }'
```

New pages will be created, existing pages will be skipped.

## Pagination

When listing pages, use `limit` and `offset`:

```bash
# Get first 100 pages
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:5000/api/v1/sitemap/client/$CLIENT_ID/pages?limit=100&offset=0"

# Get next 100 pages
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:5000/api/v1/sitemap/client/$CLIENT_ID/pages?limit=100&offset=100"
```

## Troubleshooting

### Import Fails with Timeout

**Problem:** Large sitemaps take too long to fetch.

**Solution:** Increase timeout:
```bash
# In .env
PAGE_TIMEOUT=60
```

### Too Many URLs

**Problem:** "Exceeded maximum URL limit (10000)"

**Solutions:**
1. Import sitemaps separately (don't use sitemap index)
2. Split sitemap into smaller files
3. Increase limit (modify `max_urls` in code)

### Duplicate URLs Skipped

**Problem:** Re-import shows all URLs as "skipped"

**Expected behavior:** Existing URLs are skipped by default.

**Solution:** Use `overwrite: true` to update existing pages.

### Invalid XML Error

**Problem:** "Invalid XML sitemap"

**Causes:**
- Sitemap not valid XML
- URL returns HTML instead of XML
- Gzipped sitemap (not yet supported)

**Debug:**
```bash
curl https://example.com/sitemap.xml | head -20
```

### Client Not Found

**Problem:** "Client not found"

**Solution:** Verify client UUID:
```bash
curl -H "X-API-Key: $API_KEY" http://localhost:5000/api/v1/clients
```

## Best Practices

1. **Preview First** - Always use `/parse` before `/import` on new sitemaps
2. **Start Small** - Test with a small sitemap first
3. **Monitor Summary** - Check `errors` count in response
4. **Pagination** - Use pagination when listing many pages
5. **Regular Updates** - Re-import sitemaps weekly/monthly to find new content
6. **Filter by Content** - Use `has_content` filter to find unscraped pages

## Next Steps

After importing URLs:

1. **Scrape Pages** - Implement scraping to populate `raw_html`
2. **Process with Gemini** - Convert HTML to Markdown
3. **Upload to KV** - Store processed content in Cloudflare KV
4. **Track Visits** - Monitor which pages AI bots access

## API Reference

See [README.md](../README.md#sitemap-operations) for complete API documentation.
