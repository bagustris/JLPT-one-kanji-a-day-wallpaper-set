#!/usr/bin/env python3
"""
JLPT N2 Kanji Image Generator
Processes kanji data from jlptstudy.net and creates wallpaper images in the same format as JLPT-N3 folder.

Input format expected (from https://www.jlptstudy.net/N2/?kanji-list):
```
arm, ability, talentJis208: 47-51
腕
▲ Kanji Dictionary for 腕
ワン
うで
Compounds
右腕 うわん right arm (n)
手腕 しゅわん ability (n)
敏腕 びんわん ability (adj-na, n)
片腕 かたうで one arm, right-hand man (n)
両腕 もろうで both arms (n)
```
"""

from PIL import Image, ImageDraw, ImageFont
import re
import os
import sys

# Image configuration to match existing N3 format
IMAGE_WIDTH = 1260
IMAGE_HEIGHT = 520
BACKGROUND_COLOR = (0, 0, 0, 255)  # Black background with alpha
TEXT_COLOR = (255, 255, 255)  # White text
COMPOUND_BOX_COLOR = (20, 20, 20, 255)  # Slightly lighter black for subtle contrast
COMPOUND_TEXT_COLOR = (255, 255, 255)  # White text for compounds
COMPOUND_READING_COLOR = (255, 165, 0)  # Orange color for hiragana readings in compounds
ACCENT_COLOR = (100, 149, 237)  # Cornflower blue for section headers
KANJI_COLOR = (255, 255, 255)  # White for main kanji
STROKE_ORDER_COLOR = (128, 128, 128)  # Gray for stroke order info

class KanjiImageGenerator:
    def __init__(self):
        self.font_large = None
        self.font_medium = None
        self.font_small = None
        self._load_fonts()
    
    def _load_fonts(self):
        """Load suitable fonts for Japanese characters."""
        font_paths = [
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Ubuntu/Debian
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Alternative path
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Fallback
            '/System/Library/Fonts/Hiragino Sans GB.ttc',  # macOS
            '/Windows/Fonts/msgothic.ttc',  # Windows
        ]
        
        # Try to load fonts in different sizes - reduced for wallpaper use
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.font_large = ImageFont.truetype(font_path, 220)  # Smaller main kanji
                    self.font_medium = ImageFont.truetype(font_path, 32)  # Smaller meaning/readings
                    self.font_small = ImageFont.truetype(font_path, 24)   # Smaller compounds
                    self.font_jis = ImageFont.truetype(font_path, 16)     # Smaller JIS text
                    print(f"Successfully loaded font: {font_path}")
                    return
                except Exception as e:
                    print(f"Failed to load font {font_path}: {e}")
                    continue
        
        # Fallback to default font
        print("Warning: Using default font. Japanese characters may not display correctly.")
        try:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_jis = ImageFont.load_default()
        except Exception:
            print("Error: Could not load any font")

    def parse_kanji_entry(self, text_block):
        """
        Parse a kanji entry from the jlptstudy.net format.
        
        Args:
            text_block (str): Text block for one kanji
            
        Returns:
            dict: Parsed kanji data
        """
        lines = [line.strip() for line in text_block.strip().split('\n') if line.strip()]
        
        if len(lines) < 2:
            return None
            
        # First line contains meaning and JIS info
        first_line = lines[0]
        
        # Extract JIS code using regex
        jis_match = re.search(r'Jis208:\s*(\d+-\d+)', first_line)
        jis_code = f"Jis208: {jis_match.group(1)}" if jis_match else ""
        
        # Extract meaning (remove JIS part)
        meaning = re.sub(r'Jis208:.*$', '', first_line).strip()
        
        # Second line should be the kanji character
        kanji = lines[1] if len(lines) > 1 else ""
        
        # Extract readings - separate hiragana and katakana
        hiragana_readings = []
        katakana_readings = []
        compounds = []
        
        collecting_compounds = False
        for line in lines[2:]:
            if '▲ Kanji Dictionary' in line:
                continue
            elif line == 'Compounds':
                collecting_compounds = True
                continue
            elif collecting_compounds:
                # Parse compound: "右腕 うわん right arm (n)"
                compound_match = re.match(r'([^ ]+)\s+([^ ]+)\s+(.+)', line)
                if compound_match:
                    compounds.append({
                        'kanji': compound_match.group(1),
                        'reading': compound_match.group(2),
                        'meaning': compound_match.group(3)
                    })
            elif not collecting_compounds and line:
                # Distinguish between hiragana and katakana readings
                if re.match(r'^[\u3040-\u309F\s・.,]+$', line):  # Pure hiragana line
                    hiragana_readings.append(line)
                elif re.match(r'^[\u30A0-\u30FF\s・,]+$', line):  # Pure katakana line
                    katakana_readings.append(line)
                else:
                    # Mixed line - separate hiragana and katakana characters
                    hiragana_chars = []
                    katakana_chars = []
                    
                    # Split by comma and process each part
                    parts = [p.strip() for p in line.split(',')]
                    for part in parts:
                        if re.match(r'^[\u3040-\u309F\s・.]+$', part):  # Hiragana part
                            hiragana_chars.append(part)
                        elif re.match(r'^[\u30A0-\u30FF\s・]+$', part):  # Katakana part
                            katakana_chars.append(part)
                    
                    if hiragana_chars:
                        hiragana_readings.extend(hiragana_chars)
                    if katakana_chars:
                        katakana_readings.extend(katakana_chars)
        
        return {
            'kanji': kanji,
            'meaning': meaning,
            'jis_code': jis_code,
            'hiragana_readings': hiragana_readings,
            'katakana_readings': katakana_readings,
            'compounds': compounds
        }

    def create_kanji_image(self, kanji_data, output_path):
        """
        Create a kanji wallpaper image with the specified layout.
        
        Args:
            kanji_data (dict): Parsed kanji data
            output_path (str): Path to save the image
        """
        if not kanji_data or not kanji_data.get('kanji'):
            print(f"Warning: Invalid kanji data for {output_path}")
            return False
            
        # Create image
        image = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)
        
        kanji = kanji_data['kanji']
        
        # --- Text Positioning ---
        x_margin = 50
        y_margin = 30
        vertical_spacing = 15  # Additional vertical space between elements
        
        # Left alignment for all text elements
        left_x = x_margin
        
        # Draw the main Kanji character (large, left side) 
        kanji_y = y_margin + 10
        draw.text((left_x, kanji_y), kanji, font=self.font_large, fill=KANJI_COLOR)

        # Calculate position for right column (next to kanji with some spacing)
        right_x = left_x + 300  # Position right column next to kanji
        right_y = y_margin
        
        # Draw JIS code at top-right corner - aligned with top
        if kanji_data.get('jis_code'):
            jis_text = kanji_data['jis_code']
            bbox = draw.textbbox((0, 0), jis_text, font=self.font_jis)
            jis_width = bbox[2] - bbox[0]
            jis_x = IMAGE_WIDTH - x_margin - jis_width
            draw.text((jis_x, right_y), jis_text, font=self.font_jis, fill=TEXT_COLOR)

        # Draw meaning - left-aligned in right column (no label)
        draw.text((right_x, right_y), kanji_data['meaning'], font=self.font_medium, fill=TEXT_COLOR)
        right_y += 45 + vertical_spacing

        # Draw hiragana readings - left-aligned with additional spacing (no label)
        if kanji_data.get('hiragana_readings'):
            hiragana_text = ' / '.join(kanji_data['hiragana_readings'])
            draw.text((right_x, right_y), hiragana_text, font=self.font_medium, fill=TEXT_COLOR)
            right_y += 40 + vertical_spacing

        # Draw katakana readings - left-aligned with additional spacing (no label)
        if kanji_data.get('katakana_readings'):
            katakana_text = ' / '.join(kanji_data['katakana_readings'])
            draw.text((right_x, right_y), katakana_text, font=self.font_medium, fill=TEXT_COLOR)
            right_y += 40 + vertical_spacing

        # --- Compounds Box ---
        # Remove compounds label, start box directly
        box_padding = 15
        line_spacing = 30  # Fixed spacing between compound lines
        box_x0 = right_x - box_padding  # Left-aligned with other text
        box_y0 = right_y + vertical_spacing

        # Calculate available box width more conservatively to prevent overflow
        available_width = IMAGE_WIDTH - right_x - x_margin - 20  # Extra margin for safety
        max_box_width = available_width - (box_padding * 2)
        
        # Process compounds and handle text wrapping with colored components
        wrapped_compound_lines = []
        for compound in kanji_data['compounds']:
            # Store compound parts separately for colored rendering
            compound_parts = {
                'kanji': compound['kanji'],
                'reading': compound['reading'], 
                'meaning': compound['meaning']
            }
            
            # Create full text for width calculation
            full_text = f"{compound['kanji']} {compound['reading']} {compound['meaning']}"
            bbox = draw.textbbox((0, 0), full_text, font=self.font_small)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_box_width:
                # Text fits in one line - store as compound parts
                wrapped_compound_lines.append(compound_parts)
            else:
                # Split into multiple lines more aggressively to prevent overflow
                words = full_text.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_bbox = draw.textbbox((0, 0), test_line, font=self.font_small)
                    test_width = test_bbox[2] - test_bbox[0]
                    
                    if test_width <= max_box_width * 0.85:  # More conservative limit
                        current_line = test_line
                    else:
                        # Line is full, save it and start new line
                        if current_line:
                            wrapped_compound_lines.append({'kanji': '', 'reading': '', 'meaning': current_line})
                        current_line = word
                
                # Add the last line
                if current_line:
                    wrapped_compound_lines.append({'kanji': '', 'reading': '', 'meaning': current_line})

        # Calculate box height based on actual wrapped lines + ensure bottom is visible
        if wrapped_compound_lines:
            # Reserve space at bottom of image to ensure box is fully visible
            max_available_height = IMAGE_HEIGHT - box_y0 - 30  # 30px from bottom edge
            ideal_content_height = len(wrapped_compound_lines) * line_spacing
            actual_content_height = min(ideal_content_height, max_available_height - (box_padding * 2))
            
            box_height = actual_content_height + (box_padding * 2)
            box_y1 = box_y0 + box_height
        else:
            box_y1 = box_y0 + (box_padding * 2) + 30  # Minimum height for empty box

        # Define the box dimensions
        box_x1 = IMAGE_WIDTH - x_margin

        # Draw the filled rectangle with visible borders
        draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=COMPOUND_BOX_COLOR, outline=TEXT_COLOR, width=2)

        # Now draw the wrapped compound text with colored components
        if wrapped_compound_lines:
            compound_y = box_y0 + box_padding
            for line_parts in wrapped_compound_lines:
                current_x = right_x
                
                # Handle different line types
                if line_parts['kanji'] and line_parts['reading'] and line_parts['meaning']:
                    # Full compound line with all parts
                    # Draw kanji part (white)
                    draw.text((current_x, compound_y), line_parts['kanji'], font=self.font_small, fill=COMPOUND_TEXT_COLOR)
                    kanji_bbox = draw.textbbox((0, 0), line_parts['kanji'], font=self.font_small)
                    current_x += kanji_bbox[2] - kanji_bbox[0] + 8  # Add spacing
                    
                    # Draw reading part (orange)
                    draw.text((current_x, compound_y), line_parts['reading'], font=self.font_small, fill=COMPOUND_READING_COLOR)
                    reading_bbox = draw.textbbox((0, 0), line_parts['reading'], font=self.font_small)
                    current_x += reading_bbox[2] - reading_bbox[0] + 12  # Add more spacing before meaning
                    
                    # Draw meaning part (white)
                    draw.text((current_x, compound_y), line_parts['meaning'], font=self.font_small, fill=COMPOUND_TEXT_COLOR)
                    
                elif line_parts['meaning']:
                    # Continuation line with just meaning (or overflow text)
                    draw.text((current_x, compound_y), line_parts['meaning'], font=self.font_small, fill=COMPOUND_TEXT_COLOR)
                
                compound_y += line_spacing
                
                # Safety check: don't draw text outside the box
                if compound_y > box_y1 - box_padding:
                    break

        # Save the image
        try:
            image.save(output_path, 'PNG')
            print(f"✓ Created: {output_path}")
            return True
        except Exception as e:
            print(f"✗ Error saving {output_path}: {e}")
            return False

def parse_kanji_list_file(file_path):
    """
    Parse the entire kanji list file.
    
    Args:
        file_path (str): Path to the text file containing kanji data
        
    Returns:
        list: List of parsed kanji data dictionaries
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split the content into individual kanji blocks
    # Each kanji block starts with a meaning line followed by the kanji character
    kanji_blocks = []
    current_block = []
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            if current_block:
                kanji_blocks.append('\n'.join(current_block))
                current_block = []
        else:
            current_block.append(line)
    
    # Don't forget the last block
    if current_block:
        kanji_blocks.append('\n'.join(current_block))
    
    # Parse each kanji block
    generator = KanjiImageGenerator()
    parsed_kanji = []
    
    for block in kanji_blocks:
        kanji_data = generator.parse_kanji_entry(block)
        if kanji_data and kanji_data.get('kanji'):
            parsed_kanji.append(kanji_data)
    
    return parsed_kanji

def main():
    """Main function to generate N2 kanji images."""
    
    if len(sys.argv) != 2:
        print("Usage: python3 generate_n2_kanji_images.py <kanji_data_file>")
        print("\nTo use this script:")
        print("1. Go to https://www.jlptstudy.net/N2/?kanji-list")
        print("2. Copy all the kanji data from the page")
        print("3. Save it to a text file (e.g., 'n2_kanji_data.txt')")
        print("4. Run: python3 generate_n2_kanji_images.py n2_kanji_data.txt")
        print("\nThe script will create images in the JLPT-N2 folder.")
        return
    
    input_file = sys.argv[1]
    
    print("Parsing kanji data...")
    kanji_list = parse_kanji_list_file(input_file)
    
    if not kanji_list:
        print("No valid kanji data found in the input file.")
        return
    
    print(f"Found {len(kanji_list)} kanji entries.")
    
    # Create output directory
    output_dir = "/home/bagus/github/JLPT-one-kanji-a-day-wallpaper-set/JLPT-N2"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate images
    generator = KanjiImageGenerator()
    successful = 0
    failed = 0
    
    for i, kanji_data in enumerate(kanji_list):
        # Generate filename with zero-padding (5 digits like in N3)
        file_number = i + 1
        filename = f"JLPT_N2_{file_number:05d}.png"
        output_path = os.path.join(output_dir, filename)
        
        if generator.create_kanji_image(kanji_data, output_path):
            successful += 1
        else:
            failed += 1
            print(f"Failed to create image for kanji: {kanji_data.get('kanji', 'unknown')}")
    
    print(f"\n=== Generation Complete ===")
    print(f"✓ Successfully created: {successful} images")
    print(f"✗ Failed: {failed} images")
    print(f"📁 Output directory: {output_dir}")

if __name__ == "__main__":
    main()
