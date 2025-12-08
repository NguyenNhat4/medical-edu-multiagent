from openai import OpenAI
import os

def call_llm(prompt, system_prompt=None):
    api_key = os.environ.get("OPENAI_API_KEY")

    # Mocking for testing environment or missing key
    if not api_key or api_key.startswith("sk-...") or api_key == "your-api-key":

        if "Requirement Gathering" in prompt or "Thu thập đầy đủ thông tin" in prompt:
            # Check for empty history
            if "Lịch sử hội thoại:\n[]" in prompt:
                return """```yaml
status: ask
question: "Chào bạn, bạn muốn tạo bài giảng về chủ đề gì?"
requirements: null
```"""

            # Check for specific artifacts in the prompt (Assuming history is populated)
            # We assume valid user input if not empty history for this mock
            if "slide" in prompt.lower() or "lecture" in prompt.lower():
                 return """```yaml
status: done
requirements:
  topic: "Medical Mock Topic"
  audience: "Students"
  artifacts: ["lecture", "slide"]
question: null
```"""
            else:
                 # Fallback if history has generic text
                 return """```yaml
status: ask
question: "Tôi cần thêm thông tin chi tiết."
requirements: null
```"""

        if "Plan" in prompt or "Dàn ý" in prompt:
            return """```yaml
outline: |
  # Lecture Title
  ## Part 1: Intro
  ## Part 2: Body
  ## Part 3: Conclusion
subtasks:
  - title: "Plan Task 1"
    description: "Desc 1"
```"""

        if "Tạo tài liệu" in prompt or "Content" in prompt:
            return """```yaml
content: |
  # Mock Content
  This is the generated content for the requested artifact.
```"""

        return "Mock Response"

    client = OpenAI(api_key=api_key)
    # ... rest ...
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return r.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return f"Error: {e}"
