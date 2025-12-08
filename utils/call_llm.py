from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
def call_llm(prompt, system_prompt=None):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "your-api-key"))
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )
    return response.text
    
if __name__ == "__main__":
    prompt = "What is the meaning of life?"
    print(call_llm(prompt))
