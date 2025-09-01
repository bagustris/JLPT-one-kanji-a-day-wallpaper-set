#!/usr/bin/env python3
"""
JLPT N2 Kanji Image Generator
Processes kanji data from CSV file and creates wallpaper images in the same format as JLPT-N3 folder.

Input format expected (CSV file with header):
```
kanji,meaning,readings,compounds
腕,"arm, ability, talent",ワン; うで,"右腕 (うわん) = right arm; 手腕 (しゅわん) = ability; ..."
```
"""

from PIL import Image, ImageDraw, ImageFont
import csv
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
COMPOUND_READING_COLOR = (
    255,
    165,
    0,
)  # Orange color for hiragana readings in compounds
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
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Ubuntu/Debian
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Alternative path
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Fallback
            "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS
            "/Windows/Fonts/msgothic.ttc",  # Windows
        ]

        # Try to load fonts in different sizes - reduced for wallpaper use
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.font_large = ImageFont.truetype(
                        font_path, 220
                    )  # Smaller main kanji
                    self.font_medium = ImageFont.truetype(
                        font_path, 32
                    )  # Smaller meaning/readings
                    self.font_small = ImageFont.truetype(
                        font_path, 24
                    )  # Smaller compounds
                    self.font_jis = ImageFont.truetype(
                        font_path, 16
                    )  # Smaller JIS text
                    print(f"Successfully loaded font: {font_path}")
                    return
                except Exception as e:
                    print(f"Failed to load font {font_path}: {e}")
                    continue

        # Fallback to default font
        print(
            "Warning: Using default font. Japanese characters may not display correctly."
        )
        try:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_jis = ImageFont.load_default()
        except Exception:
            print("Error: Could not load any font")

    def parse_csv_entry(self, row):
        """
        Parse a kanji entry from CSV format.

        Args:
            row (dict): CSV row with keys: kanji, meaning, readings, compounds

        Returns:
            dict: Parsed kanji data
        """
        kanji = row["kanji"].strip()
        meaning = row["meaning"].strip()
        readings_str = row["readings"].strip()
        compounds_str = row["compounds"].strip()

        # Parse readings - separate hiragana and katakana
        hiragana_readings = []
        katakana_readings = []

        if readings_str:
            # Split by semicolon and comma
            reading_parts = []
            for part in readings_str.split(";"):
                reading_parts.extend([p.strip() for p in part.split(",") if p.strip()])

            for reading in reading_parts:
                reading = reading.strip()
                if reading:
                    # Check if it's hiragana or katakana
                    if re.match(r"^[\u3040-\u309F\s・.,ー]+$", reading):  # Hiragana
                        hiragana_readings.append(reading)
                    elif re.match(r"^[\u30A0-\u30FF\s・,ー]+$", reading):  # Katakana
                        katakana_readings.append(reading)
                    else:
                        # Mixed or other - try to separate
                        hiragana_part = re.findall(r"[\u3040-\u309F・.,ー]+", reading)
                        katakana_part = re.findall(r"[\u30A0-\u30FF・,ー]+", reading)
                        if hiragana_part:
                            hiragana_readings.extend(hiragana_part)
                        if katakana_part:
                            katakana_readings.extend(katakana_part)

        # Parse compounds - format: "右腕 (うわん) = right arm; 手腕 (しゅわん) = ability; ..."
        compounds = []
        if compounds_str:
            # Split by semicolon first
            compound_parts = [
                part.strip() for part in compounds_str.split(";") if part.strip()
            ]

            for compound_part in compound_parts:
                # Match pattern: "kanji (reading) = meaning"
                match = re.match(
                    r"([^\s(]+)\s*\(([^)]+)\)\s*=\s*(.+)", compound_part.strip()
                )
                if match:
                    compounds.append(
                        {
                            "kanji": match.group(1).strip(),
                            "reading": match.group(2).strip(),
                            "meaning": match.group(3).strip(),
                        }
                    )

        return {
            "kanji": kanji,
            "meaning": meaning,
            "jis_code": "",  # Not available in CSV format
            "hiragana_readings": hiragana_readings,
            "katakana_readings": katakana_readings,
            "compounds": compounds,
        }

    def _split_meaning_text(self, meaning, max_width, wrapped_lines, draw):
        """
        Split meaning text into multiple lines that fit within max_width.
        Uses intelligent word-based splitting to preserve natural flow.
        """
        words = meaning.split()
        current_line_words = []

        for word in words:
            # Test if adding this word would exceed the width
            if current_line_words:
                test_text = " ".join(current_line_words + [word])
            else:
                test_text = word

            bbox = draw.textbbox((0, 0), test_text, font=self.font_small)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line_words.append(word)
            else:
                # Current line is full, save it and start new line with this word
                if current_line_words:
                    wrapped_lines.append(
                        {
                            "kanji": "",
                            "reading": "",
                            "meaning": " ".join(current_line_words),
                        }
                    )
                    current_line_words = []

                # Check if the single word fits on its own line
                bbox = draw.textbbox((0, 0), word, font=self.font_small)
                word_width = bbox[2] - bbox[0]

                if word_width <= max_width:
                    current_line_words = [word]
                else:
                    # Word is too long, split it character by character
                    self._split_long_word(word, max_width, wrapped_lines, draw)

        # Add any remaining words
        if current_line_words:
            wrapped_lines.append(
                {"kanji": "", "reading": "", "meaning": " ".join(current_line_words)}
            )

    def _split_long_word(self, long_word, max_width, wrapped_lines, draw):
        """
        Split a very long word character by character to fit within max_width.

        Args:
            long_word (str): The word that's too long to fit
            max_width (int): Maximum width in pixels
            wrapped_lines (list): List to append the wrapped lines to
            draw: PIL ImageDraw object for text measurement
        """
        current_chars = ""

        for char in long_word:
            test_chars = current_chars + char
            test_bbox = draw.textbbox((0, 0), test_chars, font=self.font_small)
            test_width = test_bbox[2] - test_bbox[0]

            if test_width <= max_width * 0.95:
                current_chars = test_chars
            else:
                # Add current characters as a line
                if current_chars:
                    wrapped_lines.append(
                        {"kanji": "", "reading": "", "meaning": current_chars}
                    )
                current_chars = char

        # Add remaining characters
        if current_chars:
            wrapped_lines.append({"kanji": "", "reading": "", "meaning": current_chars})

    def create_kanji_image(self, kanji_data, output_path):
        """
        Create a kanji wallpaper image with the specified layout.

        Args:
            kanji_data (dict): Parsed kanji data
            output_path (str): Path to save the image
        """
        if not kanji_data or not kanji_data.get("kanji"):
            print(f"Warning: Invalid kanji data for {output_path}")
            return False

        # Create image
        image = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)

        kanji = kanji_data["kanji"]

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

        # Draw JIS code at top-right corner - aligned with top (skip if not available)
        if kanji_data.get("jis_code") and kanji_data["jis_code"].strip():
            jis_text = kanji_data["jis_code"]
            bbox = draw.textbbox((0, 0), jis_text, font=self.font_jis)
            jis_width = bbox[2] - bbox[0]
            jis_x = IMAGE_WIDTH - x_margin - jis_width
            draw.text((jis_x, right_y), jis_text, font=self.font_jis, fill=TEXT_COLOR)

        # Draw meaning - left-aligned in right column (no label)
        draw.text(
            (right_x, right_y),
            kanji_data["meaning"],
            font=self.font_medium,
            fill=TEXT_COLOR,
        )
        right_y += 45 + vertical_spacing

        # Draw hiragana readings - left-aligned with additional spacing (no label)
        if kanji_data.get("hiragana_readings"):
            hiragana_text = ", ".join(kanji_data["hiragana_readings"])
            draw.text(
                (right_x, right_y),
                hiragana_text,
                font=self.font_medium,
                fill=TEXT_COLOR,
            )
            right_y += 40 + vertical_spacing

        # Draw katakana readings - left-aligned with additional spacing (no label)
        if kanji_data.get("katakana_readings"):
            katakana_text = ", ".join(kanji_data["katakana_readings"])
            draw.text(
                (right_x, right_y),
                katakana_text,
                font=self.font_medium,
                fill=TEXT_COLOR,
            )
            right_y += 40 + vertical_spacing

        # --- Compounds Box ---
        # Remove compounds label, start box directly
        box_padding = 15
        line_spacing = 30  # Fixed spacing between compound lines
        box_x0 = right_x - box_padding  # Left-aligned with other text
        box_y0 = right_y + vertical_spacing

        # Calculate available box width more conservatively to prevent overflow
        available_width = (
            IMAGE_WIDTH - right_x - x_margin - 20
        )  # Extra margin for safety
        max_box_width = available_width - (box_padding * 2)

        # Process compounds and handle text wrapping with colored components
        wrapped_compound_lines = []
        for compound in kanji_data["compounds"]:
            # Store compound parts separately for colored rendering
            compound_parts = {
                "kanji": compound["kanji"],
                "reading": compound["reading"],
                "meaning": compound["meaning"],
            }

            # Calculate actual width needed including spacing between components
            kanji_bbox = draw.textbbox((0, 0), compound["kanji"], font=self.font_small)
            reading_bbox = draw.textbbox(
                (0, 0), compound["reading"], font=self.font_small
            )
            meaning_bbox = draw.textbbox(
                (0, 0), compound["meaning"], font=self.font_small
            )

            kanji_width = kanji_bbox[2] - kanji_bbox[0]
            reading_width = reading_bbox[2] - reading_bbox[0]
            meaning_width = meaning_bbox[2] - meaning_bbox[0]

            # Account for spacing: 8px after kanji + 12px after reading
            total_width = kanji_width + 8 + reading_width + 12 + meaning_width

            if total_width <= max_box_width:
                # All parts fit on one line
                wrapped_compound_lines.append(compound_parts)
            else:
                # Instead of immediately splitting, try to keep the compound together
                # by wrapping the meaning text intelligently

                # Check if we can fit kanji + reading + partial meaning on first line
                kr_width = (
                    kanji_width + 8 + reading_width + 12
                )  # Include spacing after reading
                remaining_width = max_box_width - kr_width

                if (
                    kr_width < max_box_width and remaining_width > 20
                ):  # Need some minimum space for meaning
                    # Try to fit some meaning words on the first line
                    meaning_words = compound["meaning"].split()
                    first_line_words = []
                    remaining_words = meaning_words[:]

                    # Build up first line with as many words as fit
                    for word in meaning_words:
                        test_meaning = " ".join(first_line_words + [word])
                        meaning_bbox = draw.textbbox(
                            (0, 0), test_meaning, font=self.font_small
                        )
                        test_width = meaning_bbox[2] - meaning_bbox[0]

                        if test_width <= remaining_width:
                            first_line_words.append(word)
                            remaining_words.remove(word)
                        else:
                            break

                    if first_line_words:
                        # Add first line with kanji, reading, and partial meaning
                        wrapped_compound_lines.append(
                            {
                                "kanji": compound["kanji"],
                                "reading": compound["reading"],
                                "meaning": " ".join(first_line_words),
                            }
                        )

                        # Add remaining meaning words on subsequent lines
                        if remaining_words:
                            remaining_meaning = " ".join(remaining_words)
                            self._split_meaning_text(
                                remaining_meaning,
                                max_box_width,
                                wrapped_compound_lines,
                                draw,
                            )
                    else:
                        # No meaning words fit, put kanji + reading on first line, meaning on next
                        wrapped_compound_lines.append(
                            {
                                "kanji": compound["kanji"],
                                "reading": compound["reading"],
                                "meaning": "",
                            }
                        )
                        self._split_meaning_text(
                            compound["meaning"],
                            max_box_width,
                            wrapped_compound_lines,
                            draw,
                        )
                else:
                    # Kanji + reading don't leave enough space, split to separate lines
                    wrapped_compound_lines.append(
                        {
                            "kanji": compound["kanji"],
                            "reading": compound["reading"],
                            "meaning": "",
                        }
                    )
                    self._split_meaning_text(
                        compound["meaning"], max_box_width, wrapped_compound_lines, draw
                    )

        # Calculate box height based on actual wrapped lines + ensure bottom is visible
        if wrapped_compound_lines:
            # Reserve space at bottom of image to ensure box is fully visible
            max_available_height = IMAGE_HEIGHT - box_y0 - 30  # 30px from bottom edge
            ideal_content_height = len(wrapped_compound_lines) * line_spacing
            actual_content_height = min(
                ideal_content_height, max_available_height - (box_padding * 2)
            )

            box_height = actual_content_height + (box_padding * 2)
            box_y1 = box_y0 + box_height
        else:
            box_y1 = box_y0 + (box_padding * 2) + 30  # Minimum height for empty box

        # Define the box dimensions
        box_x1 = IMAGE_WIDTH - x_margin

        # Draw the filled rectangle with visible borders
        draw.rectangle(
            [box_x0, box_y0, box_x1, box_y1],
            fill=COMPOUND_BOX_COLOR,
            outline=TEXT_COLOR,
            width=2,
        )

        # Now draw the wrapped compound text with colored components
        if wrapped_compound_lines:
            compound_y = box_y0 + box_padding
            for line_parts in wrapped_compound_lines:
                current_x = right_x

                # Draw kanji part if present (white)
                if line_parts["kanji"]:
                    draw.text(
                        (current_x, compound_y),
                        line_parts["kanji"],
                        font=self.font_small,
                        fill=COMPOUND_TEXT_COLOR,
                    )
                    kanji_bbox = draw.textbbox(
                        (0, 0), line_parts["kanji"], font=self.font_small
                    )
                    current_x += kanji_bbox[2] - kanji_bbox[0] + 8  # Add spacing

                # Draw reading part if present (orange)
                if line_parts["reading"]:
                    draw.text(
                        (current_x, compound_y),
                        line_parts["reading"],
                        font=self.font_small,
                        fill=COMPOUND_READING_COLOR,
                    )
                    reading_bbox = draw.textbbox(
                        (0, 0), line_parts["reading"], font=self.font_small
                    )
                    current_x += (
                        reading_bbox[2] - reading_bbox[0] + 12
                    )  # Add more spacing before meaning

                # Draw meaning part if present (white)
                if line_parts["meaning"]:
                    draw.text(
                        (current_x, compound_y),
                        line_parts["meaning"],
                        font=self.font_small,
                        fill=COMPOUND_TEXT_COLOR,
                    )

                compound_y += line_spacing

                # Safety check: don't draw text outside the box
                if compound_y > box_y1 - box_padding:
                    break

        # Save the image
        try:
            image.save(output_path, "PNG")
            print(f"✓ Created: {output_path}")
            return True
        except Exception as e:
            print(f"✗ Error saving {output_path}: {e}")
            return False


def parse_kanji_csv_file(file_path):
    """
    Parse the CSV file containing kanji data.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        list: List of parsed kanji data dictionaries
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return []

    parsed_kanji = []
    generator = KanjiImageGenerator()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 since header is row 1
                try:
                    kanji_data = generator.parse_csv_entry(row)
                    if kanji_data and kanji_data.get("kanji"):
                        parsed_kanji.append(kanji_data)
                    else:
                        print(f"Warning: Invalid kanji data at row {row_num}")
                except Exception as e:
                    print(f"Error parsing row {row_num}: {e}")
                    continue

    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

    return parsed_kanji


def main():
    """Main function to generate N2 kanji images from CSV file."""

    if len(sys.argv) != 2:
        print("Usage: python3 generate_n2_kanji_images.py <kanji_csv_file>")
        print("\nExpected CSV format:")
        print("kanji,meaning,readings,compounds")
        print(
            '腕,"arm, ability, talent",ワン; うで,"右腕 (うわん) = right arm; 手腕 (しゅわん) = ability; ..."'
        )
        print("\nThe script will create images in the JLPT-N2 folder.")
        return

    input_file = sys.argv[1]

    print("Parsing kanji CSV data...")
    kanji_list = parse_kanji_csv_file(input_file)

    if not kanji_list:
        print("No valid kanji data found in the CSV file.")
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
            print(
                f"Failed to create image for kanji: {kanji_data.get('kanji', 'unknown')}"
            )

    print(f"\n=== Generation Complete ===")
    print(f"✓ Successfully created: {successful} images")
    print(f"✗ Failed: {failed} images")
    print(f"📁 Output directory: {output_dir}")


if __name__ == "__main__":
    main()
