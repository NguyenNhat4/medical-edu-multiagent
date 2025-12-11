from pocketflow import Node, BatchNode, AsyncParallelBatchNode
from utils.call_llm import call_llm
from utils.tool_registry import get_tools, call_tool
from utils.yaml_utils import parse_yaml_robustly
import yaml
import os
import asyncio

class GetToolsNode(Node):
    def prep(self, shared):
        """Initialize and get tools"""
        print("🔍 Getting available tools...")
        return None

    def exec(self, _):
        """Retrieve tools from the MCP server"""
        # Using the new tool registry
        tools = get_tools()
        return tools

    def post(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        tools = exec_res
        shared["tools"] = tools
        
        # Format tool information for later use
        tool_info = []
        for i, tool in enumerate(tools, 1):
            properties = tool.inputSchema.get('properties', {})
            required = tool.inputSchema.get('required', [])
            
            params = []
            for param_name, param_info in properties.items():
                param_type = param_info.get('type', 'unknown')
                req_status = "(Required)" if param_name in required else "(Optional)"
                params.append(f"    - {param_name} ({param_type}): {req_status}")
            
            tool_info.append(f"[{i}] {tool.name}\n  Description: {tool.description}\n  Parameters:\n" + "\n".join(params))
        
        shared["tool_info"] = "\n".join(tool_info)
        return "decide"

class DecideToolNode(Node):
    def prep(self, shared):
        """Prepare the prompt for LLM to process the question"""
        tool_info = shared.get("tool_info", "No tools available")
        question = shared.get("question", "")
        
        prompt = f"""
### CONTEXT
You are an assistant that can use tools via Model Context Protocol (MCP).

### ACTION SPACE
{tool_info}

### TASK
Answer this question: "{question}"

## NEXT ACTION
Analyze the question, extract any numbers or parameters, and decide which tool to use.
Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning about what the question is asking and what numbers to extract>
tool: <name of the tool to use>
reason: <why you chose this tool>
parameters:
    <parameter_name>: <parameter_value>
    <parameter_name>: <parameter_value>
```
IMPORTANT: 
1. Extract numbers from the question properly
2. Use proper indentation (4 spaces) for multi-line fields
3. Use the | character for multi-line text fields
"""
        return prompt

    def exec(self, prompt):
        """Call LLM to process the question and decide which tool to use"""
        print("🤔 Analyzing question and deciding which tool to use...")
        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        """Extract decision from YAML and save to shared context"""
        try:
            decision = parse_yaml_robustly(exec_res)
            
            if not decision:
                raise ValueError("Failed to parse YAML decision")

            shared["tool_name"] = decision["tool"]
            shared["parameters"] = decision["parameters"]
            shared["thinking"] = decision.get("thinking", "")
            
            print(f"💡 Selected tool: {decision['tool']}")
            print(f"🔢 Extracted parameters: {decision['parameters']}")
            
            return "execute"
        except Exception as e:
            print(f"❌ Error parsing LLM response: {e}")
            print("Raw response:", exec_res)
            return None

class ExecuteToolNode(Node):
    def prep(self, shared):
        """Prepare tool execution parameters"""
        return shared["tool_name"], shared["parameters"]

    def exec(self, inputs):
        """Execute the chosen tool"""
        tool_name, parameters = inputs
        print(f"🔧 Executing tool '{tool_name}' with parameters: {parameters}")
        # Using the new tool registry
        result = call_tool(tool_name, parameters)
        return result

    def post(self, shared, prep_res, exec_res):
        print(f"\n✅ Final Answer: {exec_res}")
        return "done"

class InterviewerNode(Node):
    def prep(self, shared):
        # We need both history and current known requirements
        return shared.get("chat_history", []), shared.get("requirements", {})

    def exec(self, inputs):
        history, reqs = inputs

        history_text = ""
        for msg in history:
            role = "User" if msg['role'] == "user" else "Agent"
            history_text += f"{role}: {msg['content']}\n"

        # Format current requirements as YAML for context
        reqs_text = yaml.dump(reqs, default_flow_style=False, allow_unicode=True) if reqs else "Chưa có thông tin."

        prompt = f"""
Bạn là Trợ lý Y khoa (Medical Agent).
Nhiệm vụ: Thu thập thông tin từ người dùng để xây dựng bài giảng.
Cần 3 thông tin quan trọng:
1. Chủ đề (Topic)
2. Đối tượng (Audience)
3. Mục tiêu (Objectives)

Trạng thái hiện tại (Thông tin đã biết):
{reqs_text}

Lịch sử hội thoại:
{history_text}

HÃY SUY NGHĨ:
- Nếu thiếu thông tin nào -> Hỏi thông tin đó.
- Nếu người dùng thay đổi ý định -> Cập nhật thông tin mới.
- Nếu đã đủ 3 thông tin -> Xác nhận (done).

OUTPUT FORMAT (YAML):
Vui lòng trả về YAML trong block code. Luôn luôn quote (ngoặc kép) các giá trị string để tránh lỗi parse.

```yaml
status: "ask"  # hoặc "done"
message: "Câu hỏi tiếp theo hoặc xác nhận..."
requirements:
  topic: "..."      # Giữ nguyên hoặc cập nhật
  audience: "..."   # Giữ nguyên hoặc cập nhật
  objectives: "..." # Giữ nguyên hoặc cập nhật
```
"""
        try:
            response = call_llm(prompt)
            result = parse_yaml_robustly(response)
            if not result:
                raise ValueError("Failed to parse YAML")
            return result
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            print(f"Raw Response: {response}")
            return {"status": "ask", "message": "Có lỗi xử lý, vui lòng nhắc lại."}

    def post(self, shared, prep_res, exec_res):
        if not isinstance(exec_res, dict):
             exec_res = {"status": "ask", "message": "Lỗi định dạng phản hồi."}

        shared["interview_result"] = exec_res
        if exec_res.get("status") == "done":
            shared["requirements"] = exec_res.get("requirements")
        return "default"

class PlannerNode(Node):
    def prep(self, shared):
        return {
            "reqs": shared.get("requirements", {}),
            "current_blueprint": shared.get("blueprint", []),
            "feedback": shared.get("planner_feedback", "")
        }

    def exec(self, inputs):
        reqs = inputs.get("reqs", {})
        current_blueprint = inputs.get("current_blueprint", [])
        feedback = inputs.get("feedback", "")

        if not reqs:
            return {"blueprint": []}

        if feedback:
            prompt = f"""
Bạn là chuyên gia soạn bài giảng y khoa.
Nhiệm vụ: Cập nhật dàn ý bài giảng dựa trên yêu cầu chỉnh sửa của người dùng.
Bạn có thể thêm, bớt hoặc sửa đổi các slide nếu cần thiết.

Thông tin bài giảng:
Topic: {reqs.get('topic')}
Audience: {reqs.get('audience')}
Objectives: {reqs.get('objectives')}

Dàn ý hiện tại:
{yaml.dump(current_blueprint, allow_unicode=True)}

Yêu cầu chỉnh sửa: "{feedback}"

Output YAML list mới (Cập nhật hoàn chỉnh):
Important: Quote strings.

```yaml
blueprint:
  - title: "..."
    description: "..."
```
"""
        else:
            prompt = f"""
Lập dàn ý bài giảng (Blueprint) cho:
Topic: {reqs.get('topic')}
Audience: {reqs.get('audience')}
Objectives: {reqs.get('objectives')}

Output YAML list. Important: Quote strings.
```yaml
blueprint:
  - title: "..."
    description: "..."
  - title: "..."
    description: "..."
```
"""
        try:
            response = call_llm(prompt)
            result = parse_yaml_robustly(response)
            if not result:
                raise ValueError("Failed to parse YAML")
            return result
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            print(f"Raw Response: {response}")
            return {"blueprint": []}

    def post(self, shared, prep_res, exec_res):
        if isinstance(exec_res, dict):
            shared["blueprint"] = exec_res.get("blueprint", [])
        else:
            shared["blueprint"] = []
        return "default"

class ResearcherNode(BatchNode):
    def prep(self, shared):
        self.rag_agent = shared.get("rag_agent")
        self.web_search_agent = shared.get("web_search_agent")
        return shared.get("blueprint", [])

    def exec(self, item):
        if not item: return "No item"

        # 1. Generate Query
        prompt = f"""
Generate a specific, high-quality search query to find detailed medical information for the following section of a document.
Section Title: {item.get('title')}
Description: {item.get('description')}

Return ONLY the query string, no quotes.
"""
        try:
            query = call_llm(prompt).strip().strip('"')
            print(f"🔎 Researching: {query}")

            # 2. Search
            if self.web_search_agent:
                results = self.web_search_agent.search_raw(query)
            else:
                results = [] # Fallback

            # 3. Ingest
            chunks = []
            for res in results:
                content = res.get('content')
                if content:
                    # Format chunk with metadata
                    chunk_text = f"Source: {res.get('title', 'Web')}\nURL: {res.get('url', '')}\nContent: {content}"
                    chunks.append(chunk_text)

            if chunks and self.rag_agent:
                self.rag_agent.ingest_text_chunks(chunks, metadata_path=f"Query: {query}")
                return f"Ingested {len(chunks)} results."
        except Exception as e:
            print(f"Researcher Error: {e}")
            return "Error in research."

        return "No results."

    def post(self, shared, prep_res, exec_res_list):
        shared["research_log"] = exec_res_list
        return "default"

class ContentWriterNode(AsyncParallelBatchNode):
    async def prep_async(self, shared):
        self.rag_agent = shared.get("rag_agent")
        return shared.get("blueprint", [])

    async def exec_async(self, item):
        title = item.get('title')
        description = item.get('description')

        context = ""
        if self.rag_agent:
            # Retrieve relevant chunks
            query = f"{title} {description}"
            # Run sync retrieval in thread
            try:
                docs = await asyncio.to_thread(self.rag_agent.vector_store.retrieve_relevant_chunks, query)
                context = "\n\n".join([d.get('content', '') for d in docs])
                print(f"📚 Retrieved {len(docs)} chunks for '{title}'")
            except Exception as e:
                print(f"Retrieval error: {e}")

        prompt = f"""
Vai trò: Medical Content Writer.
Nhiệm vụ: Viết nội dung chi tiết cho một phần trong tài liệu bài giảng, dựa trên thông tin được cung cấp.
Section Title: "{title}"
Description: "{description}"
Context Info:
{context}

Yêu cầu:
- Nội dung chuyên sâu, chính xác.
- Trình bày mạch lạc.
- Định dạng output YAML phải chính xác.

Output YAML. Use block scalar (|) for content.
```yaml
section:
  title: "{title}"
  body:
    - heading: "Overview"
      content: |
        ...
    - heading: "Details"
      content: |
        ...
```
"""
        try:
            response = await asyncio.to_thread(call_llm, prompt)
            result = parse_yaml_robustly(response)
            if isinstance(result, dict) and "section" in result:
                return result["section"]
            else:
                return {"title": title, "body": [{"content": "Error in generation"}]}
        except Exception as e:
            print(f"Content Generation Error: {e}")
            return {"title": title, "body": [{"content": "Error in generation"}]}

    async def post_async(self, shared, prep_res, exec_res_list):
        shared["doc_sections"] = exec_res_list
        return "default"

class DocGeneratorNode(Node):
    def prep(self, shared):
        return shared.get("doc_sections", []), shared.get("requirements", {}).get("topic", "document")

    def exec(self, inputs):
        sections, topic = inputs
        # Create output directory
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{output_dir}/{topic.replace(' ', '_')}.docx"
        filename = os.path.abspath(filename)

        print(f"📄 Generating document: {filename}")

        # 1. Create Doc
        call_tool("create_document", {"file_path": filename})

        # 2. Set Styles (Times New Roman, Heading 1=15, Normal=13)
        call_tool("set_document_styles", {
            "font_name": "Times New Roman",
            "heading1_size": 15,
            "normal_size": 13
        })

        # 3. Add TOC
        call_tool("add_table_of_contents", {})
        call_tool("add_page_break", {})

        # 4. Add Content with Hierarchy Numbering (e.g., 1. Title, 1.1. Subheading)
        for i, sec in enumerate(sections, 1):
            # Main section numbering: "1. Title"
            title = f"{i}. {sec['title']}"
            call_tool("add_heading", {"text": title, "level": 1})

            for j, block in enumerate(sec.get('body', []), 1):
                if block.get('heading'):
                    # Sub section numbering: "1.1. SubTitle"
                    sub_title = f"{i}.{j}. {block['heading']}"
                    call_tool("add_heading", {"text": sub_title, "level": 2})
                if block.get('content'):
                    call_tool("add_markdown_content", {"markdown_text": block['content']})

        # 5. Save
        call_tool("save_document", {})

        return filename

    def post(self, shared, prep_res, filename):
        shared["output_file"] = filename
        print(f"✅ Document generated at: {filename}")
        return "default"

class PPTGeneratorNode(Node):
    # Left here for backward compatibility or future use
    def prep(self, shared):
        # ... (Old logic, might not work with new data structure)
        return None
    def exec(self, _):
        return None
    def post(self, shared, prep_res, exec_res):
        return "default"
