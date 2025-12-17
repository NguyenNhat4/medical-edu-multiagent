# Flow-Based Streamlit App Guide

## 🎯 Three App Versions Explained

### 1. **app.py** - Individual Node Execution
❌ **Not recommended** - Nodes called individually, no flow structure
```python
# Nodes called one by one
researcher = ResearcherNode()
researcher.run_async(shared)

writer = ContentWriterNode()
writer.run_async(shared)
```

### 2. **app_with_flow.py** - Hybrid Approach
⚠️ **Mixed** - Has flow option but still uses individual nodes
```python
if use_flow:
    flow = create_simple_content_flow()
    flow.run_async(shared)
else:
    # Individual nodes...
```

### 3. **app_flow_based.py** - Pure Flow Architecture ✅
✅ **RECOMMENDED** - Nodes connected into flows, proper architecture
```python
# Nodes connected in flows
researcher >> query_generator >> content_writer >> doc_generator
flow = AsyncFlow(start=researcher)
flow.run_async(shared)
```

## 🏗️ Flow-Based Architecture

### Key Principle: **Nodes Only Exist Within Flows**

```python
# ❌ WRONG: Calling nodes individually
node1 = SomeNode()
node1.run(shared)
node2 = AnotherNode()
node2.run(shared)

# ✅ RIGHT: Nodes connected in flows
node1 = SomeNode()
node2 = AnotherNode()
node1 >> node2
flow = Flow(start=node1)
flow.run(shared)
```

## 📊 Flow Definitions in app_flow_based.py

### Flow 1: Interview Flow
```python
def create_interview_flow():
    """Interview → Plan (with loop)"""

    interviewer = InterviewerNode()
    planner = PlannerNode()

    # Connect with actions
    interviewer - "ask" >> interviewer  # Loop if more info needed
    interviewer - "done" >> planner     # Proceed when done

    return Flow(start=interviewer)
```

**Usage in app**:
```python
# Stage 1: Interview
interview_flow = create_interview_flow()
interview_flow.run(st.session_state.shared)
```

### Flow 2: Content Generation Flow
```python
def create_content_generation_flow():
    """Research → Query Gen → Write → Document"""

    researcher = ResearcherNode()
    query_generator = QueryGeneratorNode()
    content_writer = ContentWriterNode()
    doc_generator = DocumentGeneratorNode()

    # Connect in sequence
    researcher >> query_generator >> content_writer >> doc_generator

    return AsyncFlow(start=researcher)  # Async because researcher/writer are async
```

**Usage in app**:
```python
# Stage 3: Execution
content_flow = create_content_generation_flow()
asyncio.run(content_flow.run_async(st.session_state.shared))
```

### Flow 3: Research-Only Flow
```python
def create_research_flow():
    """Research → Query Gen (no content generation)"""

    researcher = ResearcherNode()
    query_generator = QueryGeneratorNode()

    researcher >> query_generator

    return AsyncFlow(start=researcher)
```

**Usage**:
```python
# For building knowledge base only
research_flow = create_research_flow()
asyncio.run(research_flow.run_async(shared))
```

## 🔄 App Flow Structure

```
┌─────────────────────────────────────────────┐
│  STAGE 1: Interview                         │
│  ┌───────────────────────────────────────┐  │
│  │ create_interview_flow()               │  │
│  │   Interview ──ask──> Interview (loop) │  │
│  │           └──done──> Planner          │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STAGE 2: Plan                              │
│  ┌───────────────────────────────────────┐  │
│  │ Single Node (no flow needed)          │  │
│  │   PlannerNode.run()                   │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STAGE 3: Execution                         │
│  ┌───────────────────────────────────────┐  │
│  │ create_content_generation_flow()      │  │
│  │   Researcher ──>                      │  │
│  │   QueryGen   ──>                      │  │
│  │   Writer     ──>                      │  │
│  │   DocGen                              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STAGE 4: Done                              │
│    Display results & download               │
└─────────────────────────────────────────────┘
```

## 💡 Why Flow-Based is Better

### Comparison

| Aspect | Individual Nodes (app.py) | Flow-Based (app_flow_based.py) |
|--------|---------------------------|----------------------------------|
| **Architecture** | ❌ Coupled | ✅ Clean separation |
| **Reusability** | ❌ Hard to reuse | ✅ Flows can be reused |
| **Testing** | ❌ Must test entire app | ✅ Test flows independently |
| **Maintenance** | ❌ Change in multiple places | ✅ Change flow definition once |
| **Error Handling** | ❌ Manual for each node | ✅ Flow handles it |
| **Orchestration** | ❌ Manual in UI code | ✅ Declarative in flow |
| **Best Practice** | ❌ No | ✅ Yes |

### Example: Adding a New Step

**Individual Nodes (app.py)**:
```python
# Must update UI code
researcher = ResearcherNode()
asyncio.run(researcher.run_async(shared))
progress_bar.progress(30)

# NEW: Add aggregator (must modify app.py)
aggregator = ContentAggregatorNode()
aggregator.run(shared)
progress_bar.progress(45)

writer = ContentWriterNode()
asyncio.run(writer.run_async(shared))
progress_bar.progress(60)
```

**Flow-Based (app_flow_based.py)**:
```python
# Update flow definition only
def create_content_generation_flow():
    researcher = ResearcherNode()
    aggregator = ContentAggregatorNode()  # NEW: Just add here
    query_generator = QueryGeneratorNode()
    content_writer = ContentWriterNode()
    doc_generator = DocumentGeneratorNode()

    # NEW: Connect it
    researcher >> aggregator >> query_generator >> content_writer >> doc_generator

    return AsyncFlow(start=researcher)

# App code unchanged!
content_flow = create_content_generation_flow()
asyncio.run(content_flow.run_async(shared))
```

## 🎨 Key Features of app_flow_based.py

### 1. **Clean Flow Definitions**
All flows defined at the top:
```python
def create_interview_flow():
    """Clear, reusable, testable"""
    interviewer = InterviewerNode()
    planner = PlannerNode()

    interviewer - "ask" >> interviewer
    interviewer - "done" >> planner

    return Flow(start=interviewer)
```

### 2. **Separation of Concerns**
- **UI Layer**: Streamlit UI code
- **Flow Layer**: Business logic (flows)
- **Node Layer**: Individual tasks (nodes)

### 3. **Proper Async Handling**
```python
# Flows handle sync/async automatically
content_flow = create_content_generation_flow()

# Just run it
asyncio.run(content_flow.run_async(shared))
```

### 4. **Enhanced Progress Display**
```python
# Show research details
research_log = shared.get("research_log", [])
with st.expander(f"Research Details ({len(research_log)} items)"):
    for log in research_log:
        st.write(f"• {log}")

# Show generated queries
queries = shared.get("blueprint_with_queries", [])
with st.expander(f"Generated Queries ({len(queries)} items)"):
    for item in queries:
        st.write(f"**{item['title']}**")
        st.code(item['query'])
```

### 5. **Better Statistics**
```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📄 Sections", len(doc_sections))
with col2:
    st.metric("📝 Subsections", total_subsections)
with col3:
    st.metric("🔍 Sources", len(research_log))
with col4:
    st.metric("📦 File Size", f"{file_size:.1f} KB")
```

## 🚀 Running the App

### Start Flow-Based App
```bash
streamlit run app_flow_based.py
```

### Expected Behavior

1. **Stage 1: Interview**
   - Uses `create_interview_flow()`
   - Interview loops until requirements complete
   - Auto-proceeds to planner when done

2. **Stage 2: Plan**
   - Uses single PlannerNode (no flow needed)
   - User can edit blueprint
   - AI refinement available

3. **Stage 3: Execution**
   - Uses `create_content_generation_flow()`
   - Complete automated pipeline
   - Shows research log and queries

4. **Stage 4: Done**
   - Download document
   - View statistics
   - Preview content
   - Start new or go back

## 📋 Shared Store Structure

```python
shared = {
    # Interview
    "chat_history": [],
    "requirements": {"topic": "...", "audience": "...", "objectives": "..."},
    "interview_result": {"status": "done", "message": "..."},

    # Planning
    "blueprint": [
        {"title": "...", "description": "..."},
        ...
    ],
    "planner_feedback": "...",

    # Research
    "research_log": [
        "✓ Researched 'Introduction': 5 sources",
        ...
    ],

    # Query Generation
    "blueprint_with_queries": [
        {"title": "...", "description": "...", "query": "..."},
        ...
    ],

    # Content Writing
    "doc_sections": [
        {
            "title": "...",
            "body": [
                {"heading": "...", "content": "..."},
                ...
            ]
        },
        ...
    ],

    # Document Generation
    "output_file": "output/Diabetes_Management.docx",

    # Dependencies
    "rag_agent": rag_agent_instance,
    "web_search_agent": search_agent_instance
}
```

## 🧪 Testing Flows Independently

Each flow can be tested without the UI:

```python
# Test interview flow
from app_flow_based import create_interview_flow

shared = {
    "chat_history": [],
    "requirements": {}
}

flow = create_interview_flow()
flow.run(shared)

print(shared["interview_result"])
```

```python
# Test content generation flow
from app_flow_based import create_content_generation_flow
import asyncio

shared = {
    "blueprint": [...],
    "rag_agent": rag_agent,
    "web_search_agent": search_agent
}

flow = create_content_generation_flow()
asyncio.run(flow.run_async(shared))

print(f"Generated {len(shared['doc_sections'])} sections")
```

## 🎓 Best Practices Demonstrated

### 1. **Flow Composition**
```python
# Each flow does one thing well
create_interview_flow()          # Just interview & plan
create_content_generation_flow() # Just generate content
create_research_flow()           # Just research
```

### 2. **Node Connection Patterns**
```python
# Sequential
node1 >> node2 >> node3

# Conditional (with actions)
node1 - "success" >> node2
node1 - "failure" >> error_node

# Loop
node1 - "continue" >> node1
node1 - "done" >> node2
```

### 3. **Async Flow Usage**
```python
# Create async flow
flow = AsyncFlow(start=async_node)

# Run in Streamlit
try:
    loop = asyncio.get_running_loop()
    loop.run_until_complete(flow.run_async(shared))
except RuntimeError:
    asyncio.run(flow.run_async(shared))
```

### 4. **Error Handling**
```python
try:
    flow.run_async(shared)
    st.success("Done!")
except Exception as e:
    st.error(f"Error: {e}")
    with st.expander("Details"):
        st.code(traceback.format_exc())
```

## ✅ Summary

| Feature | app_flow_based.py |
|---------|-------------------|
| **Architecture** | ✅ Pure flow-based |
| **Nodes** | ✅ Only in flows |
| **Reusable** | ✅ Flows can be reused |
| **Testable** | ✅ Test flows independently |
| **Maintainable** | ✅ Change flows, not UI |
| **Clean** | ✅ Clear separation |
| **Best Practice** | ✅ Yes |

**app_flow_based.py is the recommended approach for production use!** 🎉
