"""
Standalone Placeholder Detection and Configuration Tool

This script scans your Google Slides presentation and auto-configures new placeholders.
Run it with your presentation ID to detect and configure placeholders.
"""

import json
import os
import sys
import re

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.slides_client import SlidesClient

PLACEHOLDER_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def analyze_presentation(presentation_id):
    """Detect all placeholders in the presentation"""
    # Use SlidesClient for authentication
    client = SlidesClient()
    service = client.service
    presentation = service.presentations().get(presentationId=presentation_id).execute()
    
    placeholders = []
    
    for slide in presentation.get('slides', []):
        slide_id = slide.get('objectId')
        for element in slide.get('pageElements', []):
            element_id = element.get('objectId')
            
            # Extract text from shapes
            if 'shape' in element and element['shape'].get('text'):
                text_content = ''
                for te in element['shape']['text'].get('textElements', []):
                    if 'textRun' in te and te['textRun'].get('content'):
                        text_content += te['textRun']['content']
                    elif 'autoText' in te and te['autoText'].get('content'):
                        text_content += te['autoText']['content']
                
                # Find placeholders
                for match in PLACEHOLDER_PATTERN.findall(text_content or ''):
                    placeholders.append({
                        'name': match,
                        'slide_id': slide_id,
                        'element_id': element_id
                    })
            
            # Extract text from tables
            if 'table' in element:
                table = element['table']
                rows = table.get('tableRows', [])
                for row in rows:
                    cells = row.get('tableCells', [])
                    for cell in cells:
                        cell_text = cell.get('text')
                        if not cell_text:
                            continue
                        text_content = ''
                        for te in cell_text.get('textElements', []):
                            if 'textRun' in te and te['textRun'].get('content'):
                                text_content += te['textRun']['content']
                        
                        for match in PLACEHOLDER_PATTERN.findall(text_content or ''):
                            placeholders.append({
                                'name': match,
                                'slide_id': slide_id,
                                'element_id': element_id
                            })
    
    return {
        'presentation_id': presentation_id,
        'title': presentation.get('title'),
        'placeholders': placeholders
    }


def load_existing_configs():
    """Load existing placeholder configurations"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    configs = {
        'placeholder_mapping': {},
        'placeholder_colors': {},
        'ai_prompts': {}
    }
    
    try:
        with open(os.path.join(base_dir, 'templates/placeholder_mapping.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            configs['placeholder_mapping'] = data.get('placeholder_mappings', {})
    except Exception as e:
        print(f"Could not load placeholder_mapping.json: {e}")
    
    try:
        with open(os.path.join(base_dir, 'config/placeholder_colors.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            configs['placeholder_colors'] = data.get('placeholder_configurations', {})
    except Exception as e:
        print(f"Could not load placeholder_colors.json: {e}")
    
    try:
        with open(os.path.join(base_dir, 'config/ai_prompts.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
            configs['ai_prompts'] = {
                **data.get('text_prompts', {}),
                **data.get('image_prompts', {})
            }
    except Exception as e:
        print(f"Could not load ai_prompts.json: {e}")
    
    return configs


def infer_placeholder_type(name):
    """Infer the type of placeholder based on its name"""
    name_lower = name.lower()
    
    if 'image' in name_lower or 'chart' in name_lower:
        return 'IMAGE'
    elif 'color' in name_lower:
        return 'COLOR'
    elif 'logo' in name_lower and name_lower != 'companylogo':
        return 'EMOJI'
    elif 'heading' in name_lower or 'head' in name_lower:
        return 'TITLE'
    elif 'para' in name_lower:
        return 'PARAGRAPH'
    elif 'title' in name_lower or 'name' in name_lower:
        return 'TITLE'
    elif 'subtitle' in name_lower:
        return 'SUBTITLE'
    elif 'bullet' in name_lower or 'property' in name_lower:
        return 'BULLET'
    elif 'footer' in name_lower:
        return 'FOOTER'
    else:
        return 'TEXT'


def generate_default_configs(name, ptype):
    """Generate default configurations for a new placeholder"""
    
    mapping = {
        'type': ptype,
        'description': f"{ptype.lower()} placeholder for {name}",
        'content_requirements': {
            'min_words': 8 if ptype == 'PARAGRAPH' else 2,
            'max_words': 80 if ptype == 'PARAGRAPH' else 6,
            'style': 'professional'
        },
        'auto_fill': {
            'use_project_name': ptype in ['TITLE', 'TEXT', 'PARAGRAPH'],
            'use_company_name': ptype in ['TITLE', 'TEXT', 'PARAGRAPH'],
            'suffix': '',
            'prefix': ''
        }
    }
    
    color_config = {
        'color_source': 'theme_based',
        'theme_color': 'text_color' if 'para' in name.lower() else 'primary_color',
        'custom_color': '#1f2937' if 'para' in name.lower() else '#2563eb',
        'fallback_color': '#1f2937' if 'para' in name.lower() else '#2563eb',
        'bold': ptype == 'TITLE',
        'italic': False,
        'description': f"{ptype.lower()} placeholder styling"
    }
    
    if ptype == 'IMAGE':
        prompt = "Professional image for '{project_name}' by {company_name}. Project Description: {project_description}. CRITICAL DIMENSION REQUIREMENT: Generate image in EXACT dimensions {placeholder_width}x{placeholder_height} {placeholder_unit}."
    elif ptype == 'TITLE' or ptype == 'EMOJI':
        prompt = f"Generate content for {name} related to {{project_name}} by {{company_name}}."
    elif ptype == 'PARAGRAPH':
        prompt = f"Write a paragraph about {{project_name}} for {{company_name}}. Project Description: {{project_description}}. Use professional language."
    else:
        prompt = f"Generate appropriate content for {name} related to {{project_name}} by {{company_name}}."
    
    return mapping, color_config, prompt


def main():
    print("\n" + "="*80)
    print("  Placeholder Detection and Configuration Tool")
    print("="*80 + "\n")
    
    # Get presentation ID and flags from command line or user input
    import sys
    auto_configure = False
    if len(sys.argv) > 1:
        presentation_id = sys.argv[1].strip()
        print(f"[*] Using presentation ID from command line: {presentation_id}\n")
        # Check for auto-configure flag
        if len(sys.argv) > 2 and sys.argv[2].lower() in ['-y', '--yes', '--auto']:
            auto_configure = True
            print("[*] Auto-configure mode enabled\n")
    else:
        presentation_id = input("Enter your Google Slides Presentation ID: ").strip()
    
    if not presentation_id:
        print("Error: No presentation ID provided.")
        return
    
    # Extract ID from full URL if user pasted it
    if '/' in presentation_id:
        parts = presentation_id.split('/')
        for part in parts:
            if len(part) > 20:  # Google Slides IDs are typically long
                presentation_id = part
                break
    
    print(f"\n[*] Analyzing presentation: {presentation_id}")
    print("Please wait...\n")
    
    try:
        # Analyze the presentation
        report = analyze_presentation(presentation_id)
        detected_placeholders = report.get('placeholders', [])
        
        if not detected_placeholders:
            print("[X] No placeholders found in this presentation.")
            print("\nMake sure your placeholders are in the format: {{placeholder_name}}")
            return
        
        print(f"[OK] Found {len(detected_placeholders)} placeholders in your presentation\n")
        
        # Load existing configurations
        existing_configs = load_existing_configs()
        
        # Get list of configured placeholder names
        configured_names = set()
        configured_names.update(existing_configs['placeholder_mapping'].keys())
        configured_names.update(existing_configs['placeholder_colors'].keys())
        configured_names.update(existing_configs['ai_prompts'].keys())
        
        # Separate into configured and new placeholders
        configured = []
        new_placeholders = []
        
        for ph in detected_placeholders:
            name = ph.get('name')
            ptype = infer_placeholder_type(name)
            
            if name in configured_names:
                configured.append({'name': name, 'type': ptype})
            else:
                new_placeholders.append({'name': name, 'type': ptype})
        
        # Display results
        print(f"[*] Summary:")
        print(f"   Total placeholders detected: {len(detected_placeholders)}")
        print(f"   Already configured: {len(configured)}")
        print(f"   New placeholders: {len(new_placeholders)}\n")
        
        if configured:
            print("[OK] Already configured placeholders:")
            for ph in configured:
                print(f"   - {ph['name']} ({ph['type']})")
            print()
        
        if new_placeholders:
            print("[NEW] New placeholders found:")
            for ph in new_placeholders:
                print(f"   - {ph['name']} ({ph['type']})")
            print()
            
            # Ask user if they want to auto-configure the new placeholders
            if auto_configure:
                response = 'y'
                print("[*] Auto-configuring all new placeholders...\n")
            else:
                try:
                    response = input("Would you like to auto-configure these new placeholders? (y/n): ").strip().lower()
                except EOFError:
                    print("\n[INFO] Running in non-interactive mode. Use -y flag to auto-configure.")
                    return
            
            if response == 'y':
                print("\n[*] Auto-configuring new placeholders...\n")
                
                # Load existing config files
                base_dir = os.path.dirname(os.path.abspath(__file__))
                mapping_path = os.path.join(base_dir, 'templates/placeholder_mapping.json')
                colors_path = os.path.join(base_dir, 'config/placeholder_colors.json')
                prompts_path = os.path.join(base_dir, 'config/ai_prompts.json')
                
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                
                with open(colors_path, 'r', encoding='utf-8') as f:
                    colors_data = json.load(f)
                
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    prompts_data = json.load(f)
                
                # Add new placeholders
                for ph in new_placeholders:
                    name = ph['name']
                    ptype = ph['type']
                    
                    mapping, color_config, prompt = generate_default_configs(name, ptype)
                    
                    # Add to placeholder_mapping.json
                    mapping_data['placeholder_mappings'][name] = mapping
                    
                    # Add to placeholder_colors.json
                    colors_data['placeholder_configurations'][name] = color_config
                    
                    # Add to ai_prompts.json
                    if ptype == 'IMAGE':
                        prompts_data['image_prompts'][name] = prompt
                    else:
                        prompts_data['text_prompts'][name] = prompt
                    
                    print(f"   [OK] Configured: {name} ({ptype})")
                
                # Save updated configs
                with open(mapping_path, 'w', encoding='utf-8') as f:
                    json.dump(mapping_data, f, indent=2, ensure_ascii=False)
                
                with open(colors_path, 'w', encoding='utf-8') as f:
                    json.dump(colors_data, f, indent=4, ensure_ascii=False)
                
                with open(prompts_path, 'w', encoding='utf-8') as f:
                    json.dump(prompts_data, f, indent=2, ensure_ascii=False)
                
                print(f"\n[SUCCESS] Successfully configured {len(new_placeholders)} new placeholders!")
                print("\nNext steps:")
                print("   1. Review the updated config files")
                print("   2. Customize prompts and styling as needed")
                print("   3. Run your presentation generation script")
                print(f"   4. All placeholders will be automatically filled!\n")
        
        # Show presentation details
        print(f"\n[*] Presentation Details:")
        print(f"   Title: {report.get('title', 'N/A')}")
        print(f"   Placeholders per slide:")
        slide_counts = {}
        for ph in detected_placeholders:
            slide_id = ph.get('slide_id')
            slide_counts[slide_id] = slide_counts.get(slide_id, 0) + 1
        
        for i, (slide_id, count) in enumerate(slide_counts.items(), 1):
            print(f"   Slide {i}: {count} placeholders")
        
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

