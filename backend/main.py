"""
PPT Automation - Main Entry Point
Generate professional presentations with AI-powered content and theming
"""
import argparse
from config import LOG_LEVEL, LOG_FILE
from utils.logger import get_logger
from core import PPTAutomation
from config import TEMPLATE_PRESENTATION_ID


def main():
    parser = argparse.ArgumentParser(
        description="Generate professional presentations with AI-powered content and theming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for required fields)
  python main.py --interactive --template-id YOUR_TEMPLATE_ID
  
  # Company mode with specific company and project
  python main.py --company "Reliance Foundation" --project-name "Digital Transformation" --template-id YOUR_TEMPLATE_ID
  
  # Custom project with specific details
  python main.py --company "Tech Corp" --project-name "AI Platform" --proposal-type "Technical Proposal" --template-id YOUR_TEMPLATE_ID
        """
    )
    
    # Required arguments
    parser.add_argument('--template-id', '-t', type=str, help='Template presentation ID')
    
    # Content arguments
    parser.add_argument('--company', type=str, help='Company name (enables company profile mode)')
    parser.add_argument('--company-website', type=str, help='Company website URL (for logo extraction)')
    parser.add_argument('--project-name', type=str, help='Project name for {{projectName}}')
    parser.add_argument('--proposal-type', type=str, help='Proposal type for {{proposalName}}')
    
    # Mode arguments
    parser.add_argument('--interactive', action='store_true', help='Interactive mode - prompts for company name')
    parser.add_argument('--fallback', action='store_true', help='Use fallback content (no AI)')
    parser.add_argument('--auto-detect', action='store_true', help='Auto-detect placeholders and fill text/images')
    
    # Google Sheets arguments
    parser.add_argument('--sheets-id', '--sheets-url', type=str, dest='sheets_id', help='Google Sheet ID or full URL for placeholder values')
    parser.add_argument('--sheets-range', type=str, default='Sheet1', help='Sheet name or A1 range (default: Sheet1 - whole sheet)')
    
    # Image arguments
    parser.add_argument('--image', action='append', default=[], help='Image mapping: IMAGE_KEY=URL')
    
    # Output arguments
    parser.add_argument('--title', '--output-title', type=str, dest='output_title', help='Output presentation title')

    # Logging arguments
    parser.add_argument('--log-level', type=str, default=LOG_LEVEL, help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    parser.add_argument('--log-file', type=str, default=LOG_FILE, help='Log file path')
    
    args = parser.parse_args()

    # Initialize logger
    logger = get_logger("app", args.log_level, args.log_file)

    # Validate template ID
    template_id = args.template_id or TEMPLATE_PRESENTATION_ID
    if not template_id:
        logger.error("No template ID provided. Use --template-id or set TEMPLATE_PRESENTATION_ID in .env")
        return 1

    # Interactive mode
    if args.interactive:
        try:
            from interactive_mode import InteractiveMode
            interactive = InteractiveMode()
            return interactive.run()
        except KeyboardInterrupt:
            logger.info("Cancelled by user")
            return 1
        except Exception as e:
            logger.error(f"Interactive mode error: {e}")
            return 1
    
    # Non-interactive mode - validate required arguments
    if not args.company:
        logger.error("Company name is required for non-interactive mode. Use --company or --interactive")
        return 1
    
    if not args.project_name:
        logger.error("Project name is required for non-interactive mode. Use --project-name or --interactive")
        return 1
    
    company_name = args.company
    project_name = args.project_name

    # Determine mode and context
    profile = 'company' if company_name else None
    context_value = company_name or 'General Presentation'
    
    # Set defaults for non-interactive mode
    if not args.proposal_type:
        args.proposal_type = 'Project Proposal'
    if not args.output_title:
        args.output_title = f"{company_name} - {project_name}"

    # Parse image overrides
    image_overrides = {}
    for entry in args.image:
        if '=' in entry:
            key, url = entry.split('=', 1)
            image_overrides[key.strip()] = url.strip()

    # Initialize and run automation
    try:
        automation = PPTAutomation(use_ai=not args.fallback)
        if args.auto_detect:
            result = automation.generate_presentation_auto(
                context_value,
                template_id=template_id,
                output_title=args.output_title,
                profile=profile,
                project_name=args.project_name,
                company_name=company_name,
                proposal_type=args.proposal_type,
                company_website=args.company_website,
                sheets_id=args.sheets_id,
                sheets_range=args.sheets_range,
            )
        else:
            result = automation.generate_presentation(
                context_value,
                template_id=template_id,
                output_title=args.output_title,
                image_overrides=image_overrides or None,
                profile=profile,
                project_name=args.project_name,
                company_name=company_name,
                proposal_type=args.proposal_type,
            )

        if not result:
            logger.error("Presentation generation failed")
            return 1

        logger.info(f"Success! Presentation ready at: {result['presentation_url']}")
        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
