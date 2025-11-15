"""
Enhanced Interactive Mode for PPT Automation
Provides a user-friendly step-by-step interface for creating presentations
"""
from utils.logger import get_logger
from config import LOG_LEVEL, LOG_FILE, TEMPLATE_PRESENTATION_ID


class InteractiveMode:
    def __init__(self):
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.template_id = None
        self.company_name = None
        self.company_website = None
        self.project_name = None
        self.project_description = None
        self.output_title = None
        self.use_ai = True
        self.auto_detect = False
        
    def run(self) -> int:
        """Main interactive mode entry point"""
        try:
            self._display_welcome()
            self._get_template_id()
            self._select_presentation_type()
            self._get_basic_info()
            self._confirm_and_generate()
            return 0
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return 1
        except Exception as e:
            self.logger.error(f"Interactive mode error: {e}")
            print(f"\nError: {e}")
            return 1

    def run_with_params(self,
                        template_id: str,
                        company_name: str,
                        project_name: str,
                        project_description: str,
                        output_title: str | None = None,
                        company_website: str | None = None,
                        use_ai: bool = True,
                        auto_detect: bool = False,
                        sheets_id: str | None = None,
                        sheets_range: str | None = None,
                        primary_color: str | None = None,
                        secondary_color: str | None = None,
                        accent_color: str | None = None):
        """Non-interactive: run generation directly with provided parameters.

        Returns the result dict from automation (success, presentation_id, url, etc.) or raises on error.
        """
        from core import PPTAutomation
        self.template_id = template_id or TEMPLATE_PRESENTATION_ID
        if not self.template_id:
            raise ValueError("Template ID is required")
        self.company_name = company_name
        self.company_website = company_website
        self.project_name = project_name
        self.project_description = project_description
        self.output_title = output_title or f"{company_name} - {project_name}"
        self.use_ai = use_ai
        self.auto_detect = auto_detect

        automation = PPTAutomation(use_ai=self.use_ai)
        if self.auto_detect:
            result = automation.generate_presentation_auto(
                context=self.company_name,
                template_id=self.template_id,
                output_title=self.output_title,
                profile='company' if self.company_name else None,
                project_name=self.project_name,
                project_description=self.project_description,
                company_name=self.company_name,
                proposal_type=None,
                company_website=self.company_website,
                sheets_id=sheets_id,
                sheets_range=sheets_range,
                primary_color=primary_color,
                secondary_color=secondary_color,
                accent_color=accent_color,
            )
        else:
            result = automation.generate_presentation(
                context=self.company_name,
                template_id=self.template_id,
                output_title=self.output_title,
                image_overrides=None,
                profile='company' if self.company_name else None,
                project_name=self.project_name,
                project_description=self.project_description,
                company_name=self.company_name,
                proposal_type=None,
                company_website=self.company_website,
                sheets_id=sheets_id,
                sheets_range=sheets_range,
                primary_color=primary_color,
                secondary_color=secondary_color,
                accent_color=accent_color,
            )
        return result
    
    def _display_welcome(self):
        """Display welcome message and instructions"""
        print("=" * 60)
        print("🎨 PPT AUTOMATION - INTERACTIVE MODE")
        print("=" * 60)
        print("Create professional presentations with AI-powered content!")
        print("This interactive mode will guide you through the process step by step.")
        print()
    
    def _get_template_id(self):
        """Get template presentation ID from user"""
        print("📋 STEP 1: Template Selection")
        print("-" * 30)
        
        # Check if template ID is set in environment
        if TEMPLATE_PRESENTATION_ID:
            print(f"Using default template: {TEMPLATE_PRESENTATION_ID}")
            self.template_id = TEMPLATE_PRESENTATION_ID
            return
        
        # Get template ID from user
        while not self.template_id:
            template_id = input("Enter your Google Slides template ID: ").strip()
            if template_id:
                self.template_id = template_id
                print(f"✅ Template ID set: {template_id}")
            else:
                print("❌ Template ID is required. Please try again.")
        print()
    
    def _select_presentation_type(self):
        """Setup company presentation mode"""
        print("🏢 Company Presentation Mode")
        print("This mode will analyze your company and create a themed presentation.")
        print()
        
        self.company_name = self._get_input("Enter company name", required=True)
        self.company_website = self._get_input("Enter company website URL (optional, for logo extraction)", required=False)
        if self.company_website:
            print(f"✅ Logo will be extracted from: {self.company_website}")
        else:
            print("ℹ️  Logo will be generated using AI")
        print()
        self.project_name = self._get_input("Enter project name", required=True)
        self.project_description = self._get_input("Enter project description", required=True)
        self.use_ai = True
        self.auto_detect = False
    
    
    def _get_basic_info(self):
        """Set default presentation title"""
        # Set output title automatically
        self.output_title = f"{self.company_name} - {self.project_name}"
    
    
    
    def _confirm_and_generate(self):
        """Confirm settings and generate presentation"""
        print("✅ STEP 3: Confirmation")
        print("-" * 30)
        print("Please review your settings:")
        print()
        print(f"Template ID: {self.template_id}")
        print(f"Company: {self.company_name}")
        if self.company_website:
            print(f"Company Website: {self.company_website}")
        print(f"Project: {self.project_name}")
        print(f"Description: {self.project_description}")
        print(f"Output Title: {self.output_title}")
        print(f"AI Generation: {'Yes' if self.use_ai else 'No'}")
        print()
        
        if not self._get_yes_no("Generate presentation with these settings?", default=True):
            print("Operation cancelled.")
            return
        
        print("\n🚀 Generating presentation...")
        print("This may take a few minutes. Please wait...")
        print()
        
        # Import and run the automation
        try:
            from core import PPTAutomation
            
            automation = PPTAutomation(use_ai=self.use_ai)
            
            if self.auto_detect:
                result = automation.generate_presentation_auto(
                    context=self.company_name,
                    template_id=self.template_id,
                    output_title=self.output_title,
                    profile='company' if self.company_name else None,
                    project_name=self.project_name,
                    project_description=self.project_description,
                    company_name=self.company_name,
                    proposal_type=None,
                    company_website=self.company_website,
                )
            else:
                result = automation.generate_presentation(
                    context=self.company_name,
                    template_id=self.template_id,
                    output_title=self.output_title,
                    image_overrides=None,
                    profile='company' if self.company_name else None,
                    project_name=self.project_name,
                    project_description=self.project_description,
                    company_name=self.company_name,
                    proposal_type=None,
                )
            
            if result and result.get('success'):
                print("🎉 SUCCESS!")
                print("=" * 30)
                print(f"✅ Presentation generated successfully!")
                print(f"🔗 URL: {result.get('presentation_url')}")
                print(f"📊 Placeholders replaced: {result.get('placeholders_replaced', 'Unknown')}")
                print()
                print("You can now view and edit your presentation in Google Slides.")
            else:
                print("❌ FAILED!")
                print("Presentation generation failed. Check the logs for details.")
                return 1
                
        except Exception as e:
            print(f"❌ Error during generation: {e}")
            self.logger.error(f"Generation error: {e}")
            return 1
    
    def _get_input(self, prompt: str, required: bool = False, default: str = None) -> str:
        """Get input from user with validation"""
        while True:
            if default:
                full_prompt = f"{prompt} [{default}]: "
            else:
                full_prompt = f"{prompt}: "
            
            value = input(full_prompt).strip()
            
            if not value and default:
                return default
            elif not value and required:
                print("❌ This field is required. Please try again.")
                continue
            elif not value and not required:
                return ""
            else:
                return value
    
    def _get_yes_no(self, prompt: str, default: bool = None) -> bool:
        """Get yes/no input from user"""
        while True:
            if default is True:
                full_prompt = f"{prompt} [Y/n]: "
            elif default is False:
                full_prompt = f"{prompt} [y/N]: "
            else:
                full_prompt = f"{prompt} [y/n]: "
            
            response = input(full_prompt).strip().lower()
            
            if not response and default is not None:
                return default
            elif response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("❌ Please enter 'y' for yes or 'n' for no.")


def main():
    """Main entry point for interactive mode"""
    interactive = InteractiveMode()
    return interactive.run()


if __name__ == "__main__":
    exit(main())
