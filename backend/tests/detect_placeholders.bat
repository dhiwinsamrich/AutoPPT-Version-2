@echo off
echo ================================================================================
echo   Placeholder Detection Tool
echo ================================================================================
echo.
echo This tool will scan your Google Slides presentation for placeholders
echo and help you configure them for automatic content generation.
echo.
echo To use:
echo   1. Run this script
echo   2. Enter your presentation ID when prompted
echo   3. Review detected placeholders
echo   4. Choose to auto-configure new placeholders
echo.
echo Press any key to continue...
pause >nul

python detect_placeholders_standalone.py

echo.
echo ================================================================================
echo   Detection Complete!
echo ================================================================================
echo.
echo Check the updated config files in:
echo   - templates/placeholder_mapping.json
echo   - config/placeholder_colors.json
echo   - config/ai_prompts.json
echo.
pause

