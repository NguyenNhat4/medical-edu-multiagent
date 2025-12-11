from google import genai
import os
from dotenv import load_dotenv
import PIL.Image

load_dotenv()

def call_llm(prompt, system_prompt=None, image_paths=None):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "your-api-key"))
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    # Gemini API uses system_instruction parameter for system prompts
    config = {"system_instruction": system_prompt} if system_prompt else {}

    contents = [prompt]
    if image_paths:
        for path in image_paths:
            try:
                img = PIL.Image.open(path)
                contents.append(img)
            except Exception as e:
                print(f"Error loading image {path}: {e}")

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config
    )
    return response.text
    
if __name__ == "__main__":
    prompt = "What is the meaning of life?"
    print(call_llm(prompt))
