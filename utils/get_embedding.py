from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

def get_embedding(content):
    """
    Get embedding for a string or a list of strings using Google Gemini.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = "models/text-embedding-004"

    is_single = isinstance(content, str)
    contents = [content] if is_single else content

    try:
        # Note: Gemini API might have limits on batch size.
        # For production, implement chunking for large lists.
        result = client.models.embed_content(
            model=model,
            contents=contents,
        )
        embeddings = [e.values for e in result.embeddings]
        return embeddings[0] if is_single else embeddings
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [] if is_single else [[] for _ in contents]

if __name__ == "__main__":
    text = "Hello world"
    emb = get_embedding(text)
    print(f"Embedding length: {len(emb)}")

    texts = ["Hello", "World"]
    embs = get_embedding(texts)
    print(f"Embeddings count: {len(embs)}")
    print(f"First embedding length: {len(embs[0])}")
