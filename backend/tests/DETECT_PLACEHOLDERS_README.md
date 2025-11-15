# Placeholder Detection Tool

## Overview

This tool automatically detects placeholders in your Google Slides presentation and helps you configure them for content generation.

## How to Use

### Option 1: Interactive Mode

Simply run the script:

```bash
cd backend
python detect_placeholders_standalone.py
```

Then enter your presentation ID when prompted.

### Option 2: Quick Test Mode

You can modify the script to use a hardcoded presentation ID. Open `detect_placeholders_standalone.py` and change line 206:

```python
presentation_id = "YOUR_PRESENTATION_ID_HERE"  # Hardcode your ID here
```

Then comment out line 207-210 (the input lines).

## What It Does

1. **Scans your presentation** for placeholders in the format `{{placeholder_name}}`
2. **Compares against existing configs** to identify new placeholders
3. **Auto-configures new placeholders** with default settings
4. **Updates configuration files**:
   - `templates/placeholder_mapping.json`
   - `config/placeholder_colors.json`
   - `config/ai_prompts.json`

## After Running

Once you've detected and configured your placeholders, you can:

1. **Customize the AI prompts** in `config/ai_prompts.json` to improve content generation
2. **Adjust color schemes** in `config/placeholder_colors.json` to match your brand
3. **Run your presentation generation** - all placeholders will be auto-filled!

## Example

```bash
$ python detect_placeholders_standalone.py
Enter your Google Slides Presentation ID: 1k7g7x8qjB4jImEXecYhY7mOLP5L4e4PH4zr5-btK4Q4

[*] Analyzing presentation: 1k7g7x8qjB4jImEXecYhY7mOLP5L4e4PH4zr5-btK4Q4
Please wait...

[OK] Found 25 placeholders in your presentation

[*] Summary:
   Total placeholders detected: 25
   Already configured: 20
   New placeholders: 5

[OK] Already configured placeholders:
   - projectName (TITLE)
   - companyName (SUBTITLE)
   - Heading_1 (TITLE)
   ...

[NEW] New placeholders found:
   - Heading_7 (TITLE)
   - Head7_para (PARAGRAPH)
   ...

Would you like to auto-configure these new placeholders? (y/n): y

[*] Auto-configuring new placeholders...

   [OK] Configured: Heading_7 (TITLE)
   [OK] Configured: Head7_para (PARAGRAPH)
   ...

[SUCCESS] Successfully configured 5 new placeholders!
```

## Configuration Files Explained

### placeholder_mapping.json
Defines what each placeholder represents and how to generate content for it.

### placeholder_colors.json
Defines the color scheme and styling for each placeholder.

### ai_prompts.json
Contains the AI prompts used to generate content for each placeholder type.

## Troubleshooting

**"No placeholders found"**
- Make sure your placeholders are in the format: `{{placeholder_name}}`
- Ensure you have edit access to the presentation

**"Authentication failed"**
- Check your `credentials/service_account.json` file exists
- Verify it has the correct permissions

**"Unicode errors"**
- Use Python 3.7+ for better Unicode support
- Set environment variable: `PYTHONIOENCODING=utf-8`

