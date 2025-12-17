import logging
import asyncio
from pocketflow import AsyncParallelBatchNode
from utils.call_llm import call_llm
from utils.yaml_utils import parse_yaml_robustly


class ContentWriterNode(AsyncParallelBatchNode):
    """
    Node for generating educational content using RAG retrieval.

    For each blueprint item with query:
    1. Retrieves relevant chunks from vector store
    2. Uses retrieved context to generate detailed content
    3. Formats content as structured sections
    4. Returns complete section with sources

    Uses AsyncParallelBatchNode to generate multiple sections concurrently.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    async def prep_async(self, shared):
        """
        Read blueprint with queries and RAG agent from shared store.

        Args:
            shared: Shared data store

        Returns:
            List of blueprint items with queries
        """
        self.rag_agent = shared.get("rag_agent")
        blueprint_with_queries = shared.get("blueprint_with_queries", [])

        # Fallback to regular blueprint if queries not generated
        if not blueprint_with_queries:
            blueprint = shared.get("blueprint", [])
            blueprint_with_queries = [
                {**item, "query": f"{item.get('title', '')} {item.get('description', '')}"}
                for item in blueprint
            ]

        self.logger.info(f"Preparing to write content for {len(blueprint_with_queries)} sections")
        return blueprint_with_queries

    async def exec_async(self, item):
        """
        Generate content for one blueprint section.

        Args:
            item: Dict with 'title', 'description', 'query', and optional 'context'

        Returns:
            Dict with section title and body
        """
        title = item.get('title', 'Unknown Section')
        description = item.get('description', '')
        # query = item.get('query', f"{title} {description}") # Not needed if context provided

        # Context is now passed in the item (from previous steps in the chain)
        context = item.get('context', '')

        self.logger.info(f"Writing content for: {title}")

        # Generate content using LLM
        prompt = f"""
Vai trò: Medical Content Writer for Educational Materials.

Nhiệm vụ: Viết nội dung chi tiết, chuyên sâu cho một phần trong tài liệu giáo dục y khoa.

Section Title: "{title}"
Description: "{description}"

Thông tin tham khảo (từ nguồn y khoa đáng tin cậy):
{context if context else "No specific references available. Use general medical knowledge."}

Yêu cầu:
- Nội dung chuyên sâu, chính xác về mặt y khoa
- Phù hợp với đối tượng học viên y khoa
- Trình bày mạch lạc, có cấu trúc rõ ràng
- Chia thành các tiểu mục (headings) logic
- Mỗi tiểu mục có nội dung chi tiết

Output YAML format. Use block scalar (|) for multi-line content.

```yaml
section:
  title: "{title}"
  body:
    - heading: "Overview"
      content: |
        Detailed content here...
        Multiple paragraphs...
    - heading: "Key Points"
      content: |
        More detailed content...
```
"""

        try:
            response = await asyncio.to_thread(call_llm, prompt)
            result = parse_yaml_robustly(response)

            if isinstance(result, dict) and "section" in result:
                section = result["section"]
                self.logger.info(f"✓ Generated content for '{title}' with {len(section.get('body', []))} subsections")
                return section
            else:
                self.logger.warning(f"Failed to parse YAML for '{title}', using fallback")
                return {
                    "title": title,
                    "body": [{
                        "heading": "Content",
                        "content": "Error generating content. Please review and regenerate."
                    }]
                }
        except Exception as e:
            self.logger.error(f"Content generation error for '{title}': {e}")
            return {
                "title": title,
                "body": [{
                    "heading": "Error",
                    "content": f"Error in generation: {str(e)}"
                }]
            }

    async def post_async(self, shared, prep_res, exec_res_list):
        """
        Store generated sections in shared store.

        Args:
            shared: Shared data store
            prep_res: Blueprint items with queries
            exec_res_list: List of generated sections

        Returns:
            Action string
        """
        shared["doc_sections"] = exec_res_list

        # Log summary
        self.logger.info(f"\nContent Generation Summary:")
        self.logger.info(f"  Total sections: {len(exec_res_list)}")
        for section in exec_res_list:
            subsections = len(section.get('body', []))
            self.logger.info(f"  ✓ {section.get('title', 'Unknown')}: {subsections} subsections")

        return "default"


def main():
    """
    Test function for ContentWriterNode.

    Note: Full testing requires RAG agent instance.
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("ContentWriterNode Structure Test")
    print("="*60 + "\n")

    # Mock blueprint with queries
    blueprint_with_queries = [
        {
            "title": "Introduction to Diabetes",
            "description": "Overview of diabetes types and pathophysiology",
            "query": "diabetes types pathophysiology overview medical education"
        },
        {
            "title": "Diagnosis and Testing",
            "description": "Diagnostic criteria and laboratory tests",
            "query": "diabetes diagnosis laboratory tests screening criteria"
        }
    ]

    print("Test Blueprint:")
    for idx, item in enumerate(blueprint_with_queries, 1):
        print(f"{idx}. {item['title']}")
        print(f"   Query: {item['query']}\n")

    print("\nNote: Full testing requires:")
    print("  - RAG agent instance with populated vector store")
    print("  - Async runtime environment")
    print("\nUse integration tests with complete flow for full testing.")


if __name__ == "__main__":
    main()
