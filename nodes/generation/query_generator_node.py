import logging
from pocketflow import BatchNode
from utils.call_llm import call_llm


class QueryGeneratorNode(BatchNode):
    """
    Node for generating targeted queries from blueprint items.

    For each section in the blueprint:
    1. Analyzes the title and description
    2. Generates a specific query to retrieve relevant content from RAG
    3. Returns query optimized for medical/educational context
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read blueprint from shared store.

        Args:
            shared: Shared data store

        Returns:
            List of blueprint items
        """
        blueprint = shared.get("blueprint", [])
        self.logger.info(f"Generating queries for {len(blueprint)} blueprint items")
        return blueprint

    def exec(self, item):
        """
        Generate a targeted query for one blueprint item.

        Args:
            item: Blueprint dict with 'title' and 'description'

        Returns:
            Dict with original item plus generated query
        """
        title = item.get('title', '')
        description = item.get('description', '')

        prompt = f"""
Generate a specific, targeted search query to retrieve relevant medical/educational content for this section.

Section Title: {title}
Description: {description}

Requirements:
- Focus on key medical concepts and terminology
- Include specific topics mentioned in the description
- Make it specific enough to find relevant sources
- Return ONLY the query string, no quotes or extra text

Query:"""

        try:
            query = call_llm(prompt).strip().strip('"')
            self.logger.info(f"Generated query for '{title}': {query}")

            return {
                "title": title,
                "description": description,
                "query": query
            }
        except Exception as e:
            self.logger.error(f"Error generating query for '{title}': {e}")
            # Fallback to title + description
            return {
                "title": title,
                "description": description,
                "query": f"{title} {description}"
            }

    def post(self, shared, prep_res, exec_res_list):
        """
        Store generated queries in shared store.

        Args:
            shared: Shared data store
            prep_res: Blueprint items
            exec_res_list: List of items with generated queries

        Returns:
            Action string
        """
        shared["blueprint_with_queries"] = exec_res_list

        self.logger.info(f"Generated {len(exec_res_list)} queries")
        return "default"


def main():
    """
    Test function for QueryGeneratorNode.
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Testing QueryGeneratorNode")
    print("="*60 + "\n")

    # Mock blueprint
    shared = {
        "blueprint": [
            {
                "title": "Introduction to Diabetes",
                "description": "Overview of diabetes types, prevalence, and basic pathophysiology"
            },
            {
                "title": "Diagnosis and Testing",
                "description": "Diagnostic criteria, laboratory tests, and screening guidelines"
            },
            {
                "title": "Treatment Protocols",
                "description": "Evidence-based treatment approaches for Type 1 and Type 2 diabetes"
            }
        ]
    }

    query_gen = QueryGeneratorNode()
    action = query_gen.run(shared)

    print(f"\nAction: {action}")
    print(f"\nGenerated Queries:\n")

    for idx, item in enumerate(shared.get("blueprint_with_queries", []), 1):
        print(f"{idx}. {item['title']}")
        print(f"   Query: {item['query']}")
        print()


if __name__ == "__main__":
    main()
