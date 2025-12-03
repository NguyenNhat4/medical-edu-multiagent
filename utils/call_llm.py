from openai import OpenAI
import os

def call_llm(prompt, system_prompt=None):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    r = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return r.choices[0].message.content
    
if __name__ == "__main__":
    prompt = "What is the meaning of life?"
    print(call_llm(prompt))
