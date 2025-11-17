## PPT Automation — Application Flow and Process

### Overview
This application generates professional Google Slides presentations using AI-driven text, themed imagery, and brand-aware styling. It supports both interactive and CLI-driven flows.

Key components:
- `backend/main.py`: CLI entrypoint and mode selection
- `backend/interactive_mode.py`: Guided interactive flow
- `backend/core/automation.py` (`PPTAutomation`): Orchestration of analysis, AI content, image generation, and Slides updates
- `backend/core/generator.py` (`ContentGenerator`): Gemini-based text, theme, and image generation (+ logo extraction fallback)
- `backend/core/slides_client.py` (`SlidesClient`): Google Slides/Drive API operations
- Utilities: placeholder matching, analysis, prompts, colors, and logging

---

### Running the App
1) Interactive mode (guided prompts)
```bash
python backend/interactive.py
# or
python backend/main.py --interactive --template-id <SLIDES_TEMPLATE_ID>
```

2) Non-interactive mode (CLI args)
```bash
python backend/main.py \
  --company "Acme Corp" \
  --project-name "AI Platform" \
  --proposal-type "Technical Proposal" \
  --template-id <SLIDES_TEMPLATE_ID> \
  [--auto-detect] [--fallback] [--company-website https://acme.com] \
  [--image IMAGE_KEY=URL ...] [--title "Custom Deck Title"]
```

Required:
- `--template-id` (or set `TEMPLATE_PRESENTATION_ID` in env)
- For non-interactive mode: `--company`, `--project-name`

Flags:
- `--interactive`: Guided Q&A for inputs
- `--auto-detect`: Use analyzer-driven detection of placeholders and types
- `--fallback`: Disable AI content generation (not typical; AI required by `PPTAutomation`)
- `--image`: Override specific image placeholders (`IMAGE_KEY=URL`)

---

### High-Level Flow
1) Entrypoint parses args and configures logging (`backend/main.py`).
2) Mode selection:
   - Interactive: launches `InteractiveMode.run()` for step-by-step data collection.
   - Non-interactive: validates `company`, `project-name`, etc.
3) Instantiate `PPTAutomation(use_ai=...)` which sets up `SlidesClient`, `PlaceholderMatcher`, and `ContentGenerator` (if AI enabled).
4) Choose generation path:
   - Standard: `generate_presentation(...)`
   - Auto-detect: `generate_presentation_auto(...)`
5) Replace placeholders (text, images, colors), apply theme-based styling, and return presentation URL.

---

### Standard Generation Path (`generate_presentation`)
1) Analyze template placeholders
   - `SlidesClient.find_placeholders(template_id)` scans shapes and tables for `{{...}}`.
2) Match placeholders
   - `PlaceholderMatcher.match_placeholders` uses `templates/placeholder_mapping.json` to classify each placeholder (TEXT/IMAGE/etc.), and identify unmatched ones (logged for visibility).
3) Content generation
   - If AI enabled, attempt comprehensive JSON generation via `ContentGenerator.generate_comprehensive_content(...)` (one-shot). Map keys to actual placeholders with `_map_comprehensive_to_placeholders(...)`.
   - If comprehensive fails, fall back to targeted generation:
     - Generate `Heading_1..6` sequentially, then `Head1_para..Head6_para` using heading context.
     - Generate remaining text placeholders via `PlaceholderMatcher.generate_content_for_placeholders(...)` which calls `ContentGenerator.generate_content(...)` with prompts from `config/prompts_text.json`.
   - Auto-fill known fields when present: `companyName`, `projectName`, `proposalName`.
4) Theme and brand styling
   - If profile is `company`, derive a theme:
     - Prefer name-first theme via `generate_company_theme(...)` (may enhance with logo analysis if available), else `generate_company_theme_name_only(...)`.
   - Theme includes primary/secondary/accent colors, text color, and descriptive metadata.
5) Images
   - Generate `image_1` first and reuse its style for `backgroundImage` if present.
   - For each image placeholder (`image_2`, `image_3`, `logo`, `companyLogo`, `chart_1`, `scope_img*`, `d_i_image*`):
     - Determine placeholder dimensions from template.
     - For `companyLogo`: try extracting from `--company-website` via `utils.scraper.extract_and_save_logo`; if not available, generate a transparent PNG logo using Gemini.
     - Other images use prompts from `config/prompts_image.json` and optional theme colors.
   - Upload to Drive and replace placeholders using `SlidesClient.replace_image_placeholder(...)`.
6) Colors
   - Fill color placeholders (`color1`, `color2`, `circle_1`, `circle_2`) using theme colors first, else AI-detected, else defaults. Executed via `SlidesClient.replace_color_placeholder(...)`.
7) Text replacement and styling
   - Replace text placeholders via `SlidesClient.replace_placeholders(...)` (or mixed path uses `replace_mixed_placeholders`).
   - Build a text styling map from `utils/color_manager.color_manager.create_text_styling_map(...)` and apply with `SlidesClient.apply_text_styling(...)`. Special styling for “Project” and “Overview” is applied via `_apply_special_text_styling(...)`.
8) Output
   - Return `{'success': True, 'presentation_url': https://docs.google.com/presentation/d/<ID>/edit, ...}`.

---

### Auto-Detect Path (`generate_presentation_auto`)
1) Placeholder detection
   - `utils.placeholder_analyzer.analyze_presentation(template_id)` inspects slides and tables, normalizes placeholder names, infers types (TEXT/IMAGE/COLOR/EMOJI/TITLE/PARAGRAPH), and returns a detailed report (also supports special `u0022` quote placeholders).
2) Matching and content plan
   - Build a minimal structure for the matcher; log unmatched items (by slide) for inspection.
   - Generate a `content_map` for matched placeholders. Auto-fill common fields and handle `u0022` substitutions.
3) Images
   - First generate/replace `image_1`, then `backgroundImage` leveraging `image_1` as reference.
  - `company_website` is accepted for backward compatibility but no longer triggers automatic logo extraction.
4) Colors and emojis
   - Color placeholders filled using theme or AI-detected colors; certain `logo*` text placeholders treated as emoji text.
5) Text and styling
   - Replace text placeholders; apply theme-based text styling map and special styling just like standard path.
6) Output
   - Same structure with counts of replaced placeholders.

---

### Interactive Flow (`InteractiveMode`)
Steps displayed to user:
1) Welcome and template selection (uses `TEMPLATE_PRESENTATION_ID` if set).
2) Company presentation mode inputs: `company_name`, optional `company_website` (informational only), `project_name`, `project_description`.
3) Auto-sets `output_title` to "<company> - <project>".
4) Confirms settings, then calls `PPTAutomation.generate_presentation(...)` (or auto-detect variant when enabled).
5) Prints success with the final Slides URL.

---

### Configuration
File: `backend/config.py`
- Auth: `AUTH_MODE` = `oauth` (default) or `service_account`
- OAuth files: `credentials/credentials.json` + `token.json`
- Service account: `credentials/service_account.json`
- Scopes: `presentations`, `drive.file`
- Gemini: `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_IMAGE_MODEL`
- Template: `TEMPLATE_PRESENTATION_ID`
- Optional: `BING_IMAGE_SEARCH_KEY`, `BING_IMAGE_SEARCH_ENDPOINT`

Prompts and styling:
- Text prompts: `backend/config/prompts_text.json`
- Image prompts: `backend/config/prompts_image.json`
- Theme prompts: `backend/config/prompts_theme.json`
- Colors: `backend/config/colors_theme_based.json`, `colors_custom.json`, `colors_auto_contrast.json`

Logging:
- `LOG_LEVEL` (default `INFO`), `LOG_FILE` (console-only by default)

---

### Google API Integration
`SlidesClient` handles:
- Authentication (OAuth or service account)
- Read presentation, find placeholders
- Batch update text
- Upload images to Drive and insert into Slides
- Set slide background for `backgroundImage` placeholders
- Apply text styling with colors, font sizes, and emphasis

Notes:
- Google Slides REST API does not support z-index reordering. Backgrounds should be actual slide backgrounds or designed in the template to avoid overlay issues.

---

### Files and Directories
- `backend/core/`: automation orchestrator, content generator, Slides client
- `backend/utils/`: placeholder matcher and analyzer, color manager, prompt manager, scraper, logger
- `backend/templates/`: `placeholder_mapping.json` and related config
- `backend/generated_images/`: output images (logos/backgrounds/photos), also uploaded to Drive
- `logs/placeholder_report.json`: analyzer output

---

### Error Handling and Fallbacks
- If comprehensive content fails, the system falls back to targeted generation per placeholder.
- For logos: tries website extraction; if fails, generates a transparent PNG via Gemini.
- Theme generation includes retries and defaults when AI responses are blocked or malformed.
- Color placeholders prefer theme, then AI-detected, then safe defaults.

---

### Testing and Tools
- `backend/tests/test_basic.py`, `test_auth.py`: sanity and auth tests
- Placeholder analyzer tool:
  ```bash
  python backend/utils/placeholder_analyzer.py <TEMPLATE_PRESENTATION_ID> --out logs/placeholder_report.json
  ```

---

### Typical End-to-End (Non-Interactive)
1) Set environment: `GEMINI_API_KEY`, `TEMPLATE_PRESENTATION_ID`, Google auth files.
2) Run CLI with `--company`, `--project-name`, and optional `--company-website`.
3) App finds placeholders, generates content and images, fills colors, applies styling.
4) Receive the Google Slides URL to review and finalize.


---

### CLI Arguments (backend/main.py)
- `--template-id, -t` string: Google Slides template presentation ID. Falls back to `TEMPLATE_PRESENTATION_ID`.
- `--company` string: Company name; enables company profile flow and themeing.
- `--company-website` string: Optional informational URL (no longer triggers logo extraction).
- `--project-name` string: Sets `{{projectName}}` where present.
- `--proposal-type` string: Sets `{{proposalName}}`; default "Project Proposal" if missing.
- `--interactive` flag: Launch guided flow.
- `--fallback` flag: Intended to disable AI; `PPTAutomation` requires AI, so this should normally be omitted.
- `--auto-detect` flag: Use analyzer-based detection and typed processing.
- `--image` repeatable: `IMAGE_KEY=URL` pairs to force an image path/URL (translates to logical names like `IMAGE_image_2`).
- `--title, --output-title` string: Output presentation title override.
- `--log-level` string: `DEBUG|INFO|WARNING|ERROR`.
- `--log-file` string: Output file (default disabled).

Exit codes: `0` success, `1` on validation or runtime failure.

---

### Environment Variables and Config
- `AUTH_MODE`: `oauth` (default) or `service_account`.
- `GOOGLE_CREDENTIALS_FILE`: Service account JSON path (when `service_account`).
- `GOOGLE_OAUTH_CLIENT_FILE`: OAuth client secrets JSON (when `oauth`).
- `GOOGLE_TOKEN_FILE`: Path to user token cache JSON (created/updated at runtime).
- `GOOGLE_SCOPES`: `presentations`, `drive.file` (scoped in code).
- `GEMINI_API_KEY`: Required. If missing, `ContentGenerator` raises `ValueError`.
- `GEMINI_MODEL`: Defaults to `gemini-2.0-flash-001`.
- `GEMINI_IMAGE_MODEL`: Defaults to `gemini-2.5-flash-image-preview`.
- `TEMPLATE_PRESENTATION_ID`: Default template if CLI omits `--template-id`.
- Optional: `DEFAULT_IMAGE_URL`, `BING_IMAGE_SEARCH_KEY`, `BING_IMAGE_SEARCH_ENDPOINT`.

Logging:
- `LOG_LEVEL` defaults to `INFO`. `LOG_FILE` is `None` (console-only) by default.

---

### Authentication Flows (SlidesClient)
- OAuth (`AUTH_MODE=oauth`):
  1) Load `GOOGLE_TOKEN_FILE` if present; refresh if expired.
  2) If absent/invalid, launch local server flow using `GOOGLE_OAUTH_CLIENT_FILE` and persist `token.json`.
- Service Account (`AUTH_MODE=service_account`):
  1) Load `service_account.json` and build Slides/Drive services with scopes.

Both modes initialize:
- Slides service: `build('slides','v1', credentials)`
- Drive service: `build('drive','v3', credentials)`

---

### SlidesClient Operations
- `get_presentation(presentation_id)`: Returns Slides JSON.
- `find_placeholders(presentation_id)`: Regex `\{\{([^}]+)\}\}` over shapes and tables; returns list of dicts: `placeholder`, `element_id`, `slide_id`, `text_content`.
- `replace_placeholders(presentation_id, content_map)`: Builds `replaceAllText` requests; wraps keys not already wrapped (`{{key}}`).
- `replace_mixed_placeholders(presentation_id, text_map, image_map)`: Text part only (images handled separately), same wrapping rules.
- `upload_image_to_drive(image_path)`: Uploads file to Drive, sets `anyone:reader`, returns `(file_id, public_url)`.
- `replace_image_placeholder(presentation_id, placeholder_text, image_path, slide_id=None)`: Finds ALL shapes containing the raw placeholder string (e.g., `{{image_1}}`), deletes shape(s), creates image(s) with preserved size/transform. Note: Slides API has no z-index controls; newly created images may surface above other elements.
- `replace_background_placeholder(...)`: Sets slide `pageBackgroundFill.stretchedPictureFill.contentUrl` and deletes the original placeholder shape if found.
- `replace_color_placeholder(presentation_id, placeholder_text, color, slide_id=None)`: Locates the shape by placeholder text, fills its `shapeBackgroundFill.solidFill`, then deletes all text in that shape.
- `apply_text_styling(presentation_id, text_styling_map, theme=None)`: Recomputes element text presence, applies `updateTextStyle` with `foregroundColor`, `fontSize`, `bold`, `italic`, `fontFamily`. Cleans duplicates, skips missing elements.
- `batch_update_requests(presentation_id, requests)`: Executes arbitrary batch updates.
- `get_presentation_url(presentation_id)`: Returns `https://docs.google.com/presentation/d/<id>/edit`.

Z-order note: No `bring_to_front/send_to_back` in REST; design templates so backgrounds are true slide backgrounds.

---

### Placeholder Analyzer (utils/placeholder_analyzer.py)
- Pattern: `PLACEHOLDER_PATTERN = re.compile(r"\{\{([^}]+)\}\}")`.
- Cleans names: strips whitespace/quotes, normalizes unicode quotes/dashes, removes special chars except `[A-Za-z0-9 _-]`, collapses spaces.
- Special handling: `u0022` placeholders flagged as `is_quote=True` and preserved with full `placeholder` text (e.g., `{{u0022}}`).
- Infers type when mapping missing: IMAGE for `logo/companyLogo/image_1..3/backgroundImage/chart_1/scope_img*/d_i_image*`, COLOR if name contains `color`, EMOJI for `logo*` (non-companyLogo), TITLE/SUBTITLE/PARAGRAPH heuristics, else TEXT.
- Returns per placeholder: `placeholder` (wrapped), `name`, `inferred_type`, `slide_id`, `element_id`, `size`, `transform`, `bounding_box`, `element_properties`, `source` (shape/table), `text_snippet`, `is_quote?`.
- CLI tool saves report to `logs/placeholder_report.json`.

---

### Placeholder Matcher (utils/placeholder_matcher.py)
- Loads `backend/templates/placeholder_mapping.json` → `placeholder_mappings`.
- `match_placeholders(found)` produces:
  - `matched`: `{name: {placeholder_info, mapping, type, description, ai_prompt, content_requirements, auto_fill}}`
  - `unmatched`: list of names
  - `total_found` / `total_matched`
- `generate_content_for_placeholders(...)`:
  - Auto-fill keys (companyName, projectName, proposalName) via mapping `auto_fill` rules.
  - Skips IMAGE/background types (handled elsewhere).
  - Batch-generate text via `ContentGenerator.generate_content(...)` using prompts; then `_optimize_content` (word limits, concise/professional style).

Mapping schema (excerpt):
```json
{
  "placeholder_mappings": {
    "Heading_1": { "type": "TEXT", "content_requirements": {"max_words": 6}, "description": "Main heading" },
    "image_1": { "type": "IMAGE", "description": "Hero image" },
    "companyName": { "type": "TEXT", "auto_fill": {} }
  }
}
```

---

### Content Generator (core/generator.py)
- Initialization: requires `GEMINI_API_KEY`. Configures `genai`, sets model names; holds `placeholder_colors` cache.

Text generation:
- `generate_content(placeholder_type, ...)`:
  - Loads `config/prompts_text.json`, tries variations of the key: original, underscored, lower, snake_case, etc.
  - Formats prompts with variables: `project_name`, `company_name`, `context`, `project_description`, plus dynamic heading context for `HeadN_para`.
  - Calls Gemini text model with `max_output_tokens`, `temperature`, `top_p/k`.
  - Safety: checks `candidate.safety_ratings`; on block → `_get_fallback_content` per placeholder.
  - Parses color hex if present; stores for later via `get_placeholder_color`. For scope placeholders, skips color storage (auto-contrast used downstream).
  - Simplifies output: removes markdown, punctuation normalization, repetition control, caps by placeholder-specific word limits.

Comprehensive generation:
- `generate_comprehensive_content(project_name, company_name, project_description, context)` returns a single JSON with many keys (headings, paras, bullets, features, scope, etc.). On block/parse failure → return `None` and fallback to targeted generation.
- `_map_comprehensive_to_placeholders(comprehensive_content, detected_placeholders)` maps keys to actual template names, includes aliases (e.g., `our_process_desc` → `out_process_desc`), and injects static values for common labels (e.g., `u0022` → left curly quote).

Theme generation:
- `generate_company_theme(company_name, project_name=None, logo_path=None)` prefers name-based theme then optionally enhances with logo analysis via Gemini Vision; falls back to dominant color extraction when Vision errors.
- `generate_company_theme_name_only(company_name, project_name=None)` skips logo analysis entirely.
- Theme JSON includes: `primary_color`, `secondary_color`, `accent_color`, `text_color`, `background_color`, font sizes/family, `theme_description`, `industry`, `brand_personality`, `target_audience`, `source`.

Image generation:
- `generate_image(placeholder_type, ..., placeholder_dimensions, reference_image_path=None)`:
  - Uses `_create_image_prompt` and exact placeholder dimensions from `config/prompts_image.json`; appends theme colors.
  - Calls Gemini image model; saves to `backend/generated_images/` as JPEG for photos (quality 85, progressive) or PNG when transparency is needed. Performs smart crop+resize to exact placeholder dimensions.
  - Company logos are no longer auto-generated—provide a manual override image if you need a logo inserted.

Background enhancement:
- `enhance_image_for_background(...)` and `_generate_enhanced_image_with_gemini(...)` support converting an image to a background-conducive version at target dimensions using Gemini or PIL.

Utilities:
- `_smart_resize_image`: crop-to-fit maintaining aspect ratio, then LANCZOS resize to exact dimensions.

---

### Orchestration Details (core/automation.py)
- Standard vs Auto-detect share goals but differ in how placeholders are sourced (`SlidesClient.find_placeholders` vs `analyze_presentation`).
- Auto-detect path prioritizes `image_1` first, then `backgroundImage` with `image_1` as reference, tracks `processed_images` to avoid duplicates, and merges themed styling after text replacement.
- Both paths:
  - Auto-fill `projectName`, `companyName`, `proposalName` when present.
  - Maintain `final_image_map` to coordinate Drive uploads and element replacements, skipping items already handled (e.g., `companyLogo`).
  - Build `text_styling_map` via `color_manager.create_text_styling_map(...)` and apply post text replacement. Special-case styling of elements containing words like "Project" and "Overview".

Returned structure (standard path):
```json
{
  "success": true,
  "presentation_id": "<template_id>",
  "presentation_url": "https://docs.google.com/presentation/d/<id>/edit",
  "placeholders_replaced": <int>,
  "content_map": { "...": "..." }
}
```

---

### Images, Dimensions, and Quality
- Placeholder dimensions come from Slides element `size` width/height magnitudes (unit typically PT), preserved via `elementProperties` during replacement.
- Logos are always saved as PNG (RGBA, no compression). Photos/backgrounds default to JPEG with reasonable quality to balance Drive upload speed vs clarity.
- For `backgroundImage`, slide-level background is set to avoid overlay issues and text overlay artifacts; the original placeholder shape is deleted.

---

### Styling and Color Management
- `utils/color_manager.color_manager.create_text_styling_map(placeholders, theme)` computes per-element styling from theme and config files (`colors_theme_based.json`, `colors_custom.json`, `colors_auto_contrast.json`).
- Auto-contrast logic ensures readable foregrounds on themed backgrounds.
- Special case: ensure `u0022` elements match `project_goals` color for visual coherence.

---

### Logging
- Centralized via `utils.logger.get_logger(name, level, file)`; module-level names used for granularity.
- Notable logs:
  - Unmatched placeholders report with per-slide grouping.
  - Theme generation attempts/retries and chosen colors.
  - Image uploads to Drive and replacement counts.
  - Styling application counts and skipped/missing elements.

---

### Limits and Quotas (Practical Notes)
- Google APIs: Slides and Drive rate limits apply; batching reduces calls.
- Gemini APIs: token and image generation limits apply; code includes retries and fallbacks for theme/content.
- No z-index programmatic control in Slides REST; design templates accordingly.

---

### Tests
- `backend/tests/test_auth.py`: verifies auth client initialization paths.
- `backend/tests/test_basic.py`: smoke tests for core flows.

---

### Troubleshooting
- Missing `GEMINI_API_KEY`: `ContentGenerator` raises error—set in environment.
- No placeholders found: ensure template contains `{{...}}` tokens; use Analyzer tool to inspect.
- OAuth failing: ensure `credentials/credentials.json` exists and `token.json` is writable.
- Logo extraction fails: provide `--company-website` with a public site or rely on AI-generated logo.
- Colors not applied: confirm placeholders `color1/color2/circle_1/circle_2` exist and are shapes with text (so they can be located and then filled).


