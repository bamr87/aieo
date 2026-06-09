# Publishing

Publishing adapters live in `backend/app/publishers/`.

## WordPress

`WordPressPublisher` publishes to `wp-json/wp/v2/posts` using app-password auth.

### Required environment variables

- `WP_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`

### API endpoint

- `POST /api/v1/aieo/publish/wordpress`

Body:

```json
{
  "draft_path": "drafts/example.md",
  "title": "Example Post",
  "metadata": {
    "status": "draft",
    "yoast": {
      "yoast_title": "Example",
      "yoast_metadesc": "Example description"
    }
  }
}
```

WordPress helper snippets are in `wordpress/`.
