# Japan OTAKU Insider

Your Database of Japanese Otaku Culture. This is a statically generated site that aggregates the latest news, announcements, and limited-time events from Japan for overseas otaku.

## Directory Structure
- `index.html` - Main database page
- `about.html` - About page
- `css/` - Stylesheets
- `js/` - Frontend logic
- `data/` - JSON data files (`entries.json`, `sources.json`)
- `scripts/` - Python automation scripts for fetching and updating data
- `prompts/` - Markdown files for AI prompt templates

## Daily Operation Workflow
1. Use `prompts/perplexity_daily.md` to get the latest news via Perplexity AI.
2. Feed the results to Gemini using `prompts/gemini_json_convert.md`.
3. Save the resulting JSON and use `python scripts/add_entry.py <file.json>`.
4. Run `python scripts/update_status.py` to sync status based on dates.
5. Push to GitHub!
