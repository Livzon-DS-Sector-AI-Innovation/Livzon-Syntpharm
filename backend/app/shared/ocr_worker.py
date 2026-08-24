#!/usr/bin/env python3
"""Standalone OCR worker - processes entire PDF in isolated subprocess.

Usage:
    python -m app.shared.ocr_worker <file_path> <engine> <output_file>

Args:
    file_path: Path to the PDF file
    engine: "pp_structurev3" (only supported for now)
    output_file: Path to write JSON result
"""

import json
import sys
from pathlib import Path


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""

    def default(self, obj: object) -> object:
        import numpy as np

        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def main() -> None:
    """Execute OCR inference for entire PDF and output result as JSON to file."""
    if len(sys.argv) != 4:
        error_result = {
            "success": False,
            "error": "Usage: python -m app.shared.ocr_worker <file_path> <engine> <output_file>",
        }
        print(json.dumps(error_result))
        sys.exit(1)

    file_path = Path(sys.argv[1])
    output_file = Path(sys.argv[3])

    try:
        # Lazy load models
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info(f"[Worker] Loading models for {file_path.name}...")

        from pdf2image import convert_from_path

        from app.shared.ocr_service import OCRService, count_pdf_pages

        # Get total page count
        total_pages = count_pdf_pages(file_path)

        logger.info(f"[Worker] Total pages: {total_pages}")

        # Load models (once per subprocess)
        service = OCRService()
        logger.info("[Worker] Models loaded successfully")

        # Process all pages
        page_results = []

        for page_num in range(1, total_pages + 1):
            logger.info(f"[Worker] Processing page {page_num}/{total_pages}...")

            # Convert page to image
            images = convert_from_path(
                str(file_path),
                dpi=200,
                first_page=page_num,
                last_page=page_num,
            )

            if not images:
                raise RuntimeError(f"Failed to convert page {page_num} to image")

            img_array = images[0]

            # Single inference call - get both markdown and structure
            structure_result = service.extract_structure(img_array)
            markdown = structure_result.get("markdown", "")

            page_results.append(
                {
                    "page_number": page_num,
                    "markdown": markdown,
                    "structure": structure_result,
                }
            )

        # Build final result
        result = {
            "success": True,
            "total_pages": total_pages,
            "pages": page_results,
        }

        # Write result to output file with numpy-safe serialization
        output_file.write_text(json.dumps(result, cls=NumpyEncoder))
        logger.info("[Worker] Completed successfully")
        sys.exit(0)

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        output_file.write_text(json.dumps(error_result, cls=NumpyEncoder))
        sys.exit(1)


if __name__ == "__main__":
    main()
