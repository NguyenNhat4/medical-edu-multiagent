import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from pocketflow import Node

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    RapidOcrOptions,
    smolvlm_picture_description
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import PictureItem, TableItem

class DocParserNode(Node):
    """
    Node for parsing medical research documents using docling.
    Follows the PocketFlow Node pattern with prep, exec, and post methods.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.info("DocParserNode initialized!")

    def prep(self, shared):
        """
        Read document path and output directory from shared store.

        Returns:
            Tuple of (document_path, output_dir, parse_options)
        """
        document_path = shared.get("document_path")
        output_dir = shared.get("parsed_content_dir", "parsed_content")

        # Get optional parsing configuration
        parse_options = {
            "image_resolution_scale": shared.get("image_resolution_scale", 2.0),
            "do_ocr": shared.get("do_ocr", True),
            "do_tables": shared.get("do_tables", True),
            "do_formulas": shared.get("do_formulas", True),
            "do_picture_desc": shared.get("do_picture_desc", False)
        }

        return (document_path, output_dir, parse_options)

    def exec(self, prep_res):
        """
        Parse the document and extract structured content and images.

        Args:
            prep_res: Tuple containing (document_path, output_dir, parse_options)

        Returns:
            Tuple containing (parsed_document, list_of_image_paths)
        """
        document_path, output_dir, parse_options = prep_res

        # Create output directory if it doesn't exist
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions(
            generate_page_images=True,
            generate_picture_images=True,
            images_scale=parse_options["image_resolution_scale"],
            do_ocr=parse_options["do_ocr"],
            do_table_structure=parse_options["do_tables"],
            do_formula_enrichment=parse_options["do_formulas"],
            do_picture_description=parse_options["do_picture_desc"]
        )

        # Set table structure mode
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Initialize document converter
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )

        # Convert document
        conversion_res = converter.convert(document_path)

        # Get document filename
        doc_filename = conversion_res.input.file.stem

        # Save page images
        for page_no, page in conversion_res.document.pages.items():
            page_image_filename = output_dir_path / f"{doc_filename}-{page_no}.png"
            with page_image_filename.open("wb") as fp:
                page.image.pil_image.save(fp, format="PNG")

        # Save images of figures and tables
        table_counter = 0
        picture_counter = 0
        image_paths = []

        for element, _level in conversion_res.document.iterate_items():
            if isinstance(element, TableItem):
                table_counter += 1
                element_image_filename = output_dir_path / f"{doc_filename}-table-{table_counter}.png"
                with element_image_filename.open("wb") as fp:
                    element.get_image(conversion_res.document).save(fp, "PNG")

            if isinstance(element, PictureItem):
                picture_path = f"{doc_filename}-picture-{picture_counter}.png"
                element_image_filename = output_dir_path / picture_path
                with element_image_filename.open("wb") as fp:
                    element.get_image(conversion_res.document).save(fp, "PNG")

                # Add path to the list of images
                image_paths.append(str(element_image_filename))
                picture_counter += 1

        # Extract images for summarization
        images = []
        for picture in conversion_res.document.pictures:
            ref = picture.get_ref().cref
            image = picture.image
            if image:
                images.append(str(image.uri))

        return (conversion_res.document, images)

    def post(self, shared, prep_res, exec_res):
        """
        Write parsed document and images to shared store.

        Args:
            shared: Shared data store
            prep_res: Result from prep (not used here)
            exec_res: Result from exec - tuple of (parsed_document, images)

        Returns:
            Action string (default)
        """
        parsed_document, images = exec_res

        # Store results in shared
        shared["parsed_document"] = parsed_document
        shared["images"] = images

        self.logger.info(f"Parsed document and extracted {len(images)} images")

        return "default"
