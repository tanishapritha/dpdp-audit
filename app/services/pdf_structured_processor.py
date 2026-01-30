import fitz  # PyMuPDF
import re
from typing import List, Dict, Any

class LayoutAwarePDFProcessor:
    """
    Advanced PDF parser that understands document layout and hierarchy.
    Converts PDF into structured markdown-like segments.
    """
    
    @staticmethod
    def extract_structured_text(file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text while identifying headers and maintaining section context.
        """
        doc = fitz.open(file_path)
        structured_content = []
        current_section = "General"
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("blocks")
            # Sort blocks by vertical position then horizontal
            blocks.sort(key=lambda x: (x[1], x[0]))
            
            for block in blocks:
                text = block[4].strip()
                if not text:
                    continue
                
                # Heuristic for headers: short lines with specific patterns
                # or lines that look like "Section X" or "X.Y Header"
                is_header = False
                if len(text) < 100:
                    if re.match(r'^(Section|Article|Clause)\s+\d+', text, re.I) or \
                       re.match(r'^\d+(\.\d+)*\s+[A-Z]', text):
                        is_header = True
                        current_section = text
                
                structured_content.append({
                    "page": page_num + 1,
                    "text": text,
                    "section": current_section,
                    "is_header": is_header,
                    "type": "header" if is_header else "paragraph",
                    "bbox": block[:4] # (x0, y0, x1, y1)
                })
        
        doc.close()
        return structured_content

    @staticmethod
    def create_semantic_chunks(structured_content: List[Dict[str, Any]], max_chars: int = 1500) -> List[Dict[str, Any]]:
        """
        Groups paragraphs into semantic chunks while preserving section context.
        """
        chunks = []
        current_chunk_text = ""
        current_pages = set()
        current_sections = set()
        
        current_bboxes = []
        
        for item in structured_content:
            text = item["text"]
            bbox = item["bbox"]
            page = item["page"]
            
            # If adding this would exceed max_chars, save the current chunk
            if len(current_chunk_text) + len(text) > max_chars and current_chunk_text:
                chunks.append({
                    "text": current_chunk_text.strip(),
                    "pages": list(current_pages),
                    "section_context": " > ".join(list(current_sections)[-2:]), # Last 2 sections for context
                    "metadata": {
                        "type": "semantic_group",
                        "bboxes": current_bboxes
                    }
                })
                current_chunk_text = ""
                current_pages = set()
                current_bboxes = []
                # We keep the last section for the next chunk
                last_section = list(current_sections)[-1] if current_sections else "General"
                current_sections = {last_section}

            current_chunk_text += "\n" + text
            current_pages.add(page)
            current_sections.add(item["section"])
            current_bboxes.append({"page": page, "bbox": bbox})
            
        # Add final chunk
        if current_chunk_text:
            chunks.append({
                "text": current_chunk_text.strip(),
                "pages": list(current_pages),
                "section_context": " > ".join(list(current_sections)[-2:]),
                "metadata": {
                    "type": "semantic_group",
                    "bboxes": current_bboxes
                }
            })
            
        return chunks
