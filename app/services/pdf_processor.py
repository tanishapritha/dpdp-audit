import pdfplumber
from typing import List, Dict

class PDFProcessor:
    @staticmethod
    def extract_text_with_pages(file_path: str) -> List[Dict]:
        """
        Extracts text from PDF and returns a list of dictionaries with page number and text.
        """
        pages_content = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages_content.append({
                        "page": i + 1,
                        "text": text
                    })
        return pages_content

    @staticmethod
    def segment_into_clauses(pages_content: List[Dict]) -> List[Dict]:
        """
        Segments page text into clauses. 
        Uses a newline-based segmentation by default.
        """
        clauses = []
        for page_data in pages_content:
            page_num = page_data["page"]
            text = page_data["text"]
            
            # Segmentation by lines/paragraphs
            lines = text.split('\n')
            current_clause = ""
            clause_id = 1
            
            for line in lines:
                line = line.strip()
                if not line:
                    if current_clause:
                        clauses.append({
                            "page": page_num,
                            "clause_id": f"{page_num}.{clause_id}",
                            "text": current_clause
                        })
                        current_clause = ""
                        clause_id += 1
                    continue
                
                # If the line looks like a header or new clause, split
                # This is a heuristic.
                if current_clause and (line[0].isdigit() or len(line) < 40):
                     clauses.append({
                        "page": page_num,
                        "clause_id": f"{page_num}.{clause_id}",
                        "text": current_clause
                    })
                     current_clause = line
                     clause_id += 1
                else:
                    if current_clause:
                        current_clause += " " + line
                    else:
                        current_clause = line
            
            if current_clause:
                clauses.append({
                    "page": page_num,
                    "clause_id": f"{page_num}.{clause_id}",
                    "text": current_clause
                })
                
        return clauses
