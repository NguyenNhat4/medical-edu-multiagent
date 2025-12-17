import logging
import os
from pocketflow import Node
from utils.tool_registry import call_tool


class DocumentGeneratorNode(Node):
    """
    Node for generating final document from content sections.

    Creates a professional Word document (.docx) with:
    - Table of contents
    - Hierarchical section numbering (1., 1.1., etc.)
    - Consistent formatting (Times New Roman, proper heading sizes)
    - Markdown content support
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read generated sections and topic from shared store.

        Args:
            shared: Shared data store

        Returns:
            Tuple of (sections, topic)
        """
        sections = shared.get("doc_sections", [])
        topic = shared.get("requirements", {}).get("topic", "document")

        self.logger.info(f"Preparing to generate document for: {topic}")
        self.logger.info(f"  Sections to include: {len(sections)}")

        return sections, topic

    def exec(self, inputs):
        """
        Generate Word document from sections.

        Args:
            inputs: Tuple of (sections, topic)

        Returns:
            Absolute path to generated document
        """
        sections, topic = inputs

        # Create output directory
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename
        filename = f"{output_dir}/{topic.replace(' ', '_')}.docx"
        filename = os.path.abspath(filename)

        self.logger.info(f"Generating document: {filename}")

        # 1. Create Document
        call_tool("create_document", {"file_path": filename})

        # 2. Set Styles (Times New Roman, Heading 1=15, Normal=13)
        call_tool("set_document_styles", {
            "font_name": "Times New Roman",
            "heading1_size": 15,
            "normal_size": 13
        })

        # 3. Add Table of Contents
        call_tool("add_table_of_contents", {})
        call_tool("add_page_break", {})

        # 4. Add Content with Hierarchical Numbering
        for i, sec in enumerate(sections, 1):
            # Main section numbering: "1. Title"
            title = sec.get('title', f'Section {i}')
            numbered_title = f"{i}. {title}"
            call_tool("add_heading", {"text": numbered_title, "level": 1})

            # Add subsections
            for j, block in enumerate(sec.get('body', []), 1):
                if block.get('heading'):
                    # Sub section numbering: "1.1. SubTitle"
                    sub_title = f"{i}.{j}. {block['heading']}"
                    call_tool("add_heading", {"text": sub_title, "level": 2})

                if block.get('content'):
                    call_tool("add_markdown_content", {"markdown_text": block['content']})

            self.logger.info(f"  ✓ Added section {i}: {title}")

        # 5. Save Document
        call_tool("save_document", {})

        self.logger.info(f"Document generation complete: {filename}")
        return filename

    def post(self, shared, prep_res, filename):
        """
        Store output file path in shared store.

        Args:
            shared: Shared data store
            prep_res: Prepared inputs
            filename: Generated file path

        Returns:
            Action string
        """
        shared["output_file"] = filename
        self.logger.info(f"Document generated successfully at: {filename}")
        return "default"


def main():
    """
    Test function for DocumentGeneratorNode.

    Note: Requires MCP document tools to be available.
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Testing DocumentGeneratorNode")
    print("="*60 + "\n")

    # Mock document sections
    shared = {
        "requirements": {
            "topic": "Diabetes Management Test"
        },
        "doc_sections": [
            {
                "title": "Introduction to Diabetes",
                "body": [
                    {
                        "heading": "Overview",
                        "content": "Diabetes mellitus is a chronic metabolic disorder characterized by elevated blood glucose levels.\n\nIt affects millions worldwide."
                    },
                    {
                        "heading": "Types of Diabetes",
                        "content": "There are three main types:\n- Type 1 Diabetes\n- Type 2 Diabetes\n- Gestational Diabetes"
                    }
                ]
            },
            {
                "title": "Diagnosis",
                "body": [
                    {
                        "heading": "Diagnostic Criteria",
                        "content": "Diagnosis is based on blood glucose measurements:\n- Fasting glucose ≥126 mg/dL\n- HbA1c ≥6.5%"
                    }
                ]
            }
        ]
    }

    print("Mock Sections:")
    for idx, section in enumerate(shared["doc_sections"], 1):
        print(f"{idx}. {section['title']}")
        print(f"   Subsections: {len(section['body'])}\n")

    print("Attempting to generate document...")
    print("\nNote: This requires:")
    print("  - MCP document tools configured")
    print("  - Document server running")
    print("\nIf tools are not available, this test will fail.")
    print("\nSkipping actual document generation in test mode.")


if __name__ == "__main__":
    main()
