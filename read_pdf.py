import os
import json
import re
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict, Counter
import logging
import sys

# --- Configuration ---
# Setup logging to display informational messages.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFOutlineExtractor:
    """
    Extracts a structured outline from a PDF file by analyzing font styles and text patterns.
    It identifies headings and their hierarchical levels (H1, H2, H3) even if the
    PDF does not have a built-in table of contents.
    """
    def __init__(self):
        """Initializes the extractor with a set of regex patterns and explicit keywords for identifying headings."""
        self.heading_patterns = [
            # Matches numbered headings like "1. Text", "1.1 Text", "1.1.1 Text"
            r'^\d+(\.\d+)*\s+.*',
            # Matches headings like "Chapter 1", "Section A"
            r'^(Chapter|Section)\s+([A-Z]|\d+)\s+.*',
            # Matches ALL CAPS headings (at least 3 chars long)
            r'^[A-Z\s]{3,}$',
            # Matches Title Case Headings (at least two words)
            r'^([A-Z][a-z]+)(\s[A-Z][a-z]+)+$',
            # Matches Roman numeral headings like "I. Text"
            r'^[IVXLCDM]+\.\s+.+',
        ]
        # Add keywords that are almost always headings
        self.explicit_headings = {
            "acknowledgements", "revision history", "table of contents", 
            "references", "trademarks", "introduction", "overview"
        }

    def _identify_headers_and_footers(self, doc):
        """
        Scans the top and bottom margins of each page to identify common, repeating text
        that is likely a header or footer by checking its vertical position.

        Args:
            doc (fitz.Document): The opened PDF document object.

        Returns:
            set: A set of common header and footer text strings to be ignored.
        """
        header_candidates = defaultdict(int)
        footer_candidates = defaultdict(int)
        
        if not doc.page_count:
            return set()

        # Define margins based on the first page's height
        page_height = doc[0].rect.height
        header_margin = page_height * 0.15  # Top 15%
        footer_margin = page_height * 0.85  # Bottom 15%

        for page in doc:
            blocks = page.get_text("dict").get("blocks", [])
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip()).strip()
                        if not line_text or len(line_text) < 4:
                            continue
                        
                        # Check vertical position using the line's bounding box
                        y1 = line["bbox"][1]
                        if y1 < header_margin:
                            header_candidates[line_text] += 1
                        elif y1 > footer_margin:
                            footer_candidates[line_text] += 1
        
        common_texts = set()
        # A line is a header/footer if it appears on at least half the pages (or 2, whichever is larger)
        threshold = max(doc.page_count // 2, 2) if doc.page_count > 2 else 1

        for text, count in header_candidates.items():
            if count >= threshold:
                common_texts.add(text)
        for text, count in footer_candidates.items():
            if count >= threshold:
                common_texts.add(text)

        if common_texts:
            logger.info(f"Identified potential headers/footers to ignore: {common_texts}")
            
        return common_texts

    def extract_text_lines(self, pdf_path):
        """
        Extracts text from a PDF, aggregated by lines, while filtering out
        identified headers and footers.

        Args:
            pdf_path (str): The file path to the PDF.

        Returns:
            list: A list of dictionaries, where each dictionary represents a line of text
                  with its associated formatting.
        """
        try:
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return []

            doc = fitz.open(pdf_path)
            if not doc.page_count:
                logger.warning(f"PDF has no pages: {pdf_path}")
                doc.close()
                return []

            # First, identify common headers and footers to ignore them during extraction
            headers_and_footers = self._identify_headers_and_footers(doc)

            logger.info(f"Processing {doc.page_count} pages from '{pdf_path}'")
            all_lines = []

            for page_num, page in enumerate(doc):
                blocks = page.get_text("dict").get("blocks", [])
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            if not line.get("spans"):
                                continue

                            line_text = " ".join(span["text"].strip() for span in line["spans"] if span["text"].strip()).strip()
                            if not line_text:
                                continue
                            
                            # --- FILTERING LOGIC ---
                            if line_text in headers_and_footers:
                                continue
                            if re.search(r'\s\.{3,}\s*\d+$', line_text):
                                continue

                            first_span = line["spans"][0]
                            all_lines.append({
                                'text': line_text,
                                'font': first_span["font"],
                                'size': round(first_span["size"], 1),
                                'flags': first_span["flags"],
                                'bbox': line["bbox"],
                                'page': page_num + 1,
                            })
            doc.close()
            logger.info(f"Extracted {len(all_lines)} text lines after filtering.")
            return all_lines
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return []

    def extract_title(self, text_lines):
        """
        Heuristically extracts the document title. It typically looks for the
        largest text on the first page.

        Args:
            text_lines (list): A list of text lines from `extract_text_lines`.

        Returns:
            str: The extracted document title or a default title.
        """
        if not text_lines:
            return "Untitled Document"

        first_page_lines = [line for line in text_lines if line['page'] == 1][:30]
        if not first_page_lines:
            first_page_lines = [line for line in text_lines if line['page'] == 2][:30]
            if not first_page_lines:
                return "Untitled Document"
            
        max_size = max(line['size'] for line in first_page_lines)
        title_candidates = [line['text'] for line in first_page_lines if line['size'] == max_size]
        
        title = ' '.join(title_candidates).strip()
        title = re.sub(r'\s+', ' ', title)
        if len(title) > 150:
            title = title[:147] + "..."
            
        return title if title else "Untitled Document"

    def analyze_font_styles(self, text_lines):
        """
        Analyzes font sizes across the document to identify the most common (body)
        font size and a list of potential heading sizes.

        Args:
            text_lines (list): A list of text lines.

        Returns:
            tuple: A tuple containing (body_size, heading_sizes).
        """
        if not text_lines:
            return 10.0, []
            
        size_frequency = Counter(line['size'] for line in text_lines)
        body_size = size_frequency.most_common(1)[0][0] if size_frequency else 10.0
        heading_sizes = sorted([size for size in size_frequency if size > body_size], reverse=True)
        
        return body_size, heading_sizes

    def is_likely_heading(self, line):
        """
        Determines if a line of text is likely a heading based on patterns and content.

        Args:
            line (dict): A dictionary representing a line of text.

        Returns:
            bool: True if the line is likely a heading, False otherwise.
        """
        text = line['text']
        if len(text) < 3 or len(text) > 200:
            return False
        if re.fullmatch(r'\d+', text):
            return False

        # Check for explicit heading keywords
        if text.lower().strip() in self.explicit_headings:
            return True

        # Check against predefined heading regex patterns
        for pattern in self.heading_patterns:
            if re.match(pattern, text):
                return True
        
        # Check for boldness
        if line['flags'] & 16:
            return True

        return False

    def classify_heading_level(self, line, heading_sizes):
        """
        Assigns a heading level (H1, H2, H3) based on font size and text patterns.

        Args:
            line (dict): The heading line to classify.
            heading_sizes (list): A sorted list of identified heading font sizes.

        Returns:
            str: The heading level (e.g., "H1").
        """
        font_size = line['size']
        text = line['text']
        
        try:
            level_index = heading_sizes.index(font_size)
            if level_index == 0:
                level = "H1"
            elif level_index == 1:
                level = "H2"
            else:
                level = "H3"
        except ValueError:
            level = "H3"

        match = re.match(r'^(\d+(\.\d+)*)', text)
        if match:
            num_parts = match.group(1).split('.')
            if len(num_parts) == 1:
                level = "H1"
            elif len(num_parts) == 2:
                level = "H2"
            else:
                level = "H3"
                
        return level

    def extract_outline(self, pdf_path):
        """
        The main orchestration method to extract the full outline from a PDF.

        Args:
            pdf_path (str): The path to the PDF file.

        Returns:
            dict: A dictionary containing the document's title and a list of headings.
        """
        text_lines = self.extract_text_lines(pdf_path)
        if not text_lines:
            return {"title": "Error: Could Not Process Document", "outline": []}

        title = self.extract_title(text_lines)
        body_size, heading_sizes = self.analyze_font_styles(text_lines)

        if not heading_sizes:
            logger.warning("Could not identify any heading styles. Falling back to basic size check.")
            unique_sizes = sorted(list(set(l['size'] for l in text_lines)), reverse=True)
            if len(unique_sizes) > 1:
                body_size = unique_sizes[-1]
                heading_sizes = [s for s in unique_sizes if s > body_size]

        outline = []
        seen_headings = set()
        
        for line in text_lines:
            if line['size'] <= body_size:
                continue

            if self.is_likely_heading(line):
                heading_text = line['text']
                page_num = line['page']
                
                # Filter out the document title if it's mistaken for a heading on the first page
                if heading_text.strip() == title.strip() and page_num <= 2:
                    logger.info(f"Skipping potential heading as it is the title: '{heading_text}'")
                    continue

                heading_key = (heading_text.lower(), page_num)
                if heading_key in seen_headings:
                    continue
                seen_headings.add(heading_key)
                
                level = self.classify_heading_level(line, heading_sizes)
                
                outline.append({
                    "level": level,
                    "text": heading_text,
                    "page": page_num
                })

        outline.sort(key=lambda x: x['page'])
        
        return {
            "title": title,
            "outline": outline
        }

# --- Main Execution Block ---
if __name__ == "__main__":
    extractor = PDFOutlineExtractor()

    try:
        current_dir = "."
        all_files = os.listdir(current_dir)
        pdf_files = [f for f in all_files if f.lower().endswith(".pdf")]

        if not pdf_files:
            print("❌ No PDF files found in the current directory.")
            sys.exit(1)

        print("📄 Available PDF files:")
        for idx, filename in enumerate(pdf_files, start=1):
            print(f"   {idx}. {filename}")

        choice_input = input("\nEnter the number of the PDF to process: ")
        choice = int(choice_input)
        if not 1 <= choice <= len(pdf_files):
            print("❌ Invalid choice. Exiting.")
            sys.exit(1)
            
        selected_pdf = pdf_files[choice - 1]

    except (ValueError, IndexError):
        print("❌ Invalid input. Please enter a valid number. Exiting.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    print(f"\n🔍 Processing '{selected_pdf}'...")
    result = extractor.extract_outline(selected_pdf)

    output_dir = "output_json"
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = f"{os.path.splitext(selected_pdf)[0]}.json"
    output_file_path = os.path.join(output_dir, output_filename)

    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"✅ Outline successfully saved to: {output_file_path}")
    except Exception as e:
        print(f"❌ Failed to save the output file: {e}")
