# AWS Bedrock POC Plan — Step-by-Step Practice Tasks

**Purpose**: A hands-on, iterative POC plan for integrating AWS Bedrock into the IBM Migration Copilot.  
Each step has:
1. A **POC task** — isolated, minimal, safe to experiment with
2. A **Real Developer Problem** — a real bug/friction a developer encounters when doing this for the first time
3. A **Next step gate** — only move forward when the POC task passes

**Philosophy**: Learn by doing. Break things safely. Fix real problems. Build up muscle memory before touching production workflow.

**Verified project state**: Phases 1–5 complete. Provider abstraction at `backend/app/providers/` is the primary migration seam.

---

## How to Use This Plan

```
Step N: POC Task → run it → hit the real problem → fix it → gate check → Step N+1
```

- Each step lives in an **isolated sandbox file** (never touch production agents first).
- Each "Real Developer Problem" is a **known friction point** you WILL hit — it's listed so you debug it faster, not skip it.
- Gate checks are simple: "Does this output match expected?" If yes, proceed.

---

## Step 1: First AWS Bedrock API Call (Model Invocation)

### 🎯 POC Task
Make your first raw Bedrock API call using `boto3` — invoke Claude 3 Haiku with a simple prompt and print the response.

**What to build**: A standalone Python script `backend/poc/step1_bedrock_hello.py`

```python
import boto3
import json

bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'          # Change to your region
)

body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 100,
    "messages": [
        {"role": "user", "content": "Say hello and name yourself in one sentence."}
    ]
})

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-haiku-20240307-v1:0',
    body=body
)

result = json.loads(response['body'].read())
print(result['content'][0]['text'])
```

**Expected Output**: Something like `"Hello! I'm Claude, an AI assistant made by Anthropic."`

**Gate Check**: ✅ Script runs, response contains text, no exception.

---

### 🔥 Real Developer Problem #1: Access Denied / Model Not Enabled

**What happens**:
```
botocore.errorfactory.AccessDeniedException: 
An error occurred (AccessDeniedException) when calling the InvokeModel operation: 
You don't have access to the model with the specified model ID.
```

**Why it happens**: AWS Bedrock models must be **manually enabled per region** in the AWS Console. IAM permissions alone are not enough. New accounts have NO models enabled by default.

**Fix**:
1. Go to AWS Console → Bedrock → Model access (left sidebar)
2. Click "Request model access" or "Manage model access"
3. Select "Anthropic Claude 3 Haiku" → Submit
4. Wait 2–5 minutes for activation (sometimes instant)
5. Re-run the script

**Prevention Going Forward**: Always check `bedrock.list_foundation_models()` first to see what's available in your region/account.

---

### 🔥 Real Developer Problem #2: Region Not Supported

**What happens**:
```
botocore.exceptions.EndpointResolutionError: 
Endpoint does not exist for bedrock-runtime in region ap-south-1
```

**Why it happens**: Not all Bedrock models are available in all regions. Claude 3 is primarily in `us-east-1`, `us-west-2`, `eu-west-3`.

**Fix**: Change `region_name` to `us-east-1` or check the [Bedrock model availability matrix](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html).

---

## Step 2: Build BedrockProvider Implementing LLMProvider Interface

### 🎯 POC Task
Create `backend/poc/step2_bedrock_provider.py` — a Bedrock provider that implements the exact same `LLMProvider` abstract interface already used by `OpenAIProvider` and `GeminiProvider`.

**Why this interface matters**: `backend/app/providers/base.py` defines:
- `async generate(prompt, system_prompt, ...) → ProviderResponse`
- `async generate_structured(prompt, schema, ...) → Dict[str, Any]`
- `async health_check() → bool`

The POC must implement all three so it can be dropped into the factory without changing any agent code.

**What to build**:
```python
# backend/poc/step2_bedrock_provider.py
import boto3, json
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

# Copy base.py interface for self-contained POC
class BedrockProviderPOC:
    def __init__(self, region="us-east-1", model_id="anthropic.claude-3-haiku-20240307-v1:0"):
        self.client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            body["system"] = system_prompt

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

    async def generate_structured(self, prompt: str, schema: dict) -> dict:
        structured_prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema: {json.dumps(schema)}"
        text = await self.generate(structured_prompt)
        # CRITICAL: strip markdown before parsing (same as GeminiProvider)
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    async def health_check(self) -> bool:
        try:
            await self.generate("Reply with OK")
            return True
        except Exception:
            return False

# Test
import asyncio

async def main():
    provider = BedrockProviderPOC()

    # Test 1: basic generation
    text = await provider.generate("What is cloud migration in one sentence?")
    print("TEXT:", text[:100])

    # Test 2: structured output
    result = await provider.generate_structured(
        "List 2 cloud providers",
        {"providers": [{"name": "string", "specialty": "string"}]}
    )
    print("STRUCTURED:", result)

    # Test 3: health check
    healthy = await provider.health_check()
    print("HEALTHY:", healthy)

asyncio.run(main())
```

**Expected Output**:
```
TEXT: Cloud migration is the process of moving applications...
STRUCTURED: {'providers': [{'name': 'AWS', 'specialty': '...'}, ...]}
HEALTHY: True
```

**Gate Check**: ✅ All 3 tests pass without exceptions.

---

### 🔥 Real Developer Problem #3: boto3 is Not Async

**What happens**: You use `await self.client.invoke_model(...)` and get:
```
TypeError: object Response can't be used in 'await' expression
```

**Why it happens**: `boto3` is **synchronous**. It has no native `async` support. `asyncio` cannot await boto3 calls.

**Fix — Two Options**:

**Option A (Simple — for POC)**: Use `asyncio.get_event_loop().run_in_executor()` to run boto3 in a thread pool:
```python
import asyncio
from functools import partial

loop = asyncio.get_event_loop()
response = await loop.run_in_executor(
    None,
    partial(self.client.invoke_model, modelId=self.model_id, body=json.dumps(body))
)
```

**Option B (Production — recommended)**: Use `aioboto3` package (async boto3 wrapper):
```python
import aioboto3

session = aioboto3.Session()
async with session.client('bedrock-runtime', region_name='us-east-1') as bedrock:
    response = await bedrock.invoke_model(...)
```
Install: `pip install aioboto3`

**What to use**: Option A for the POC (no new dependency). Option B for production `BedrockProvider`.

---

### 🔥 Real Developer Problem #4: Structured Output JSON Parse Failure

**What happens**:
```
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Why it happens**: Claude 3 (like Gemini) often wraps its JSON response in markdown code blocks:
```
Here is the JSON response:
```json
{"providers": [...]}
```
```

**Fix**: Always apply the markdown-stripping pattern (same as `GeminiProvider`). This is already in the POC code above. Never assume clean JSON from any LLM.

---

## Step 3: Bedrock Embeddings with Titan Embed

### 🎯 POC Task
Generate embeddings using Amazon Titan Embed Text v2. Compare the vector dimensions with the current Qdrant setup (768 for Gemini, 1536 for OpenAI).

**What to build**: `backend/poc/step3_bedrock_embeddings.py`

```python
import boto3, json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def embed_text(text: str) -> list:
    body = json.dumps({"inputText": text})
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=body
    )
    result = json.loads(response['body'].read())
    return result['embedding']

# Test
embedding = embed_text("What is cloud migration?")
print(f"Dimension: {len(embedding)}")   # Expected: 1024
print(f"First 5 values: {embedding[:5]}")
print(f"Type: {type(embedding[0])}")   # Should be float
```

**Expected Output**:
```
Dimension: 1024
First 5 values: [0.023..., -0.041..., ...]
Type: <class 'float'>
```

**Gate Check**: ✅ Embedding is a list of 1024 floats. No exception.

---

### 🔥 Real Developer Problem #5: Qdrant Collection Dimension Mismatch

**What happens**: You switch to Titan Embed (1024 dims) but your existing Qdrant collection was created for OpenAI (1536) or Gemini (768). New documents fail to insert:
```
qdrant_client.http.exceptions.UnexpectedResponse: 
Unexpected Response: 400 - Vector dimension error. Expected dim: 1536, got: 1024
```

**Why it happens**: Qdrant collections lock their vector dimension at creation time. Adding vectors of a different size is rejected.

**Fix**: The existing `QdrantStore.add_documents()` already handles this at line ~60:
```python
# Auto-detects dimension mismatch and recreates collection
if existing_dim != new_dim:
    await self.delete_collection(collection_name)
    await self.create_collection(collection_name, vector_size=new_dim)
```

**BUT** — this silently deletes all existing vectors. For a real migration, you must:
1. Create a NEW collection: `migration_docs_bedrock`
2. Re-ingest all documents with Titan embeddings
3. Only switch the active collection name after full re-ingestion

**Prevention**: Always check `collection_info()` before switching embedding providers.

---

## Step 4: Add BedrockProvider to the Provider Factory (Real Integration)

### 🎯 POC Task
Integrate `BedrockProvider` into the real `backend/app/providers/` system — add it as a third provider option alongside OpenAI and Gemini, activated via `.env` config.

**Files to change** (surgical, minimal):

**1. Create `backend/app/providers/bedrock_provider.py`**
- Implement `LLMProvider` interface from `base.py`
- Use `run_in_executor` for boto3 async compatibility
- Apply markdown stripping in `generate_structured`
- Support `aws_access_key_id`, `aws_secret_access_key`, `region_name`, `model_id`

**2. Update `backend/app/config.py`** — add settings:
```python
bedrock_region: str = "us-east-1"
bedrock_model: str = "anthropic.claude-3-haiku-20240307-v1:0"
aws_access_key_id: Optional[str] = None
aws_secret_access_key: Optional[str] = None
aws_session_token: Optional[str] = None
```

**3. Update `backend/app/providers/factory.py`** — add `"bedrock"` to `_create_provider()`:
```python
elif provider_name == "bedrock":
    from app.providers.bedrock_provider import BedrockProvider
    return BedrockProvider(
        region=settings.bedrock_region,
        model_id=settings.bedrock_model,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
```

**4. Update `backend/.env`** to test:
```env
PRIMARY_PROVIDER=bedrock
FALLBACK_PROVIDER=openai
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

**Gate Check**: ✅ `GET /health/providers` returns `bedrock: healthy`. ✅ `POST /api/orchestration/execute` runs the full workflow (extraction, questionnaire, intake draft) using Bedrock Claude as the LLM.

---

### 🔥 Real Developer Problem #6: Bedrock Response Schema Differs from OpenAI

**What happens**: The extraction agent calls `generate_structured()` and gets a `ValidationError`:
```
pydantic.error_wrappers.ValidationError: 
1 validation error for ExtractionResult
  field: facts
  value is not a valid list (type=type_error.list)
```

**Why it happens**: Claude 3 via Bedrock may interpret JSON schema instructions differently from GPT-4. GPT-4 uses strict JSON mode (`response_format={"type": "json_object"}`), but Bedrock Claude relies on prompt engineering. The output structure can vary.

**Fix**:
1. Make the JSON schema instruction in the prompt more explicit:
   ```python
   f"Return ONLY a JSON object. No explanation. No markdown. Schema: {json.dumps(schema)}\n\nRespond:"
   ```
2. Add a post-parse validator in `generate_structured()` that checks required top-level keys.
3. Log the raw response before parsing (add `logger.debug(f"Raw LLM response: {text[:200]}")`) — this is critical for debugging.

---

### 🔥 Real Developer Problem #7: LangSmith Traces Show Bedrock Calls as "Untraced"

**What happens**: Bedrock calls via `boto3` do NOT appear in LangSmith traces the way OpenAI/Gemini calls do — because LangSmith hooks into LangChain's callback system, and raw `boto3` bypasses it.

**Why it happens**: `OpenAIProvider` and `GeminiProvider` use LangChain SDK clients (`langchain-openai`, `langchain-google-genai`) which automatically hook into LangSmith. Direct `boto3` does not.

**Fix — Two Options**:

**Option A**: Use `langchain_aws.ChatBedrock` instead of raw `boto3`:
```python
from langchain_aws import ChatBedrock

llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name="us-east-1",
    model_kwargs={"max_tokens": 2048}
)
response = llm.invoke(prompt)
```
This gives automatic LangSmith tracing.

**Option B**: Manually wrap boto3 calls in `LangSmithTracer.trace_llm_call()` (already implemented in `backend/app/tracing/langsmith.py`).

**Recommendation**: Use `langchain_aws.ChatBedrock` — it's the cleanest approach and aligns with the Bedrock learning plan.  
Add to requirements: `langchain-aws>=0.1.0`

---

## Step 5: Bedrock Knowledge Base (Replace Qdrant for RAG)

### 🎯 POC Task
Create a Bedrock Knowledge Base, ingest 2–3 sample migration documents, and query it using the RetrieveAndGenerate API. Compare results against the current Qdrant vector search.

**What to build**: `backend/poc/step5_bedrock_knowledge_base.py`

```python
import boto3

# Step A: Create Knowledge Base (one-time setup via console/CLI)
# Knowledge Base ID will be given after creation
KB_ID = "your-knowledge-base-id"

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

def query_knowledge_base(query: str, kb_id: str) -> dict:
    response = bedrock_agent_runtime.retrieve_and_generate(
        input={"text": query},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {"numberOfResults": 5}
                }
            }
        }
    )
    return {
        "answer": response["output"]["text"],
        "citations": response.get("citations", [])
    }

result = query_knowledge_base("What are the key dependencies of this application?", KB_ID)
print("Answer:", result["answer"])
print("Citations:", len(result["citations"]))
```

**Gate Check**: ✅ Query returns a relevant answer. ✅ Citations include the source document.

---

### 🔥 Real Developer Problem #8: Knowledge Base Ingestion is Asynchronous

**What happens**: You ingest documents and immediately query. The results are empty or stale:
```
Answer: I don't have information about the dependencies...
```
Even though you just uploaded the documents.

**Why it happens**: Knowledge Base ingestion is **asynchronous** — documents go through a pipeline (chunking → embedding → indexing) that takes minutes. Querying before ingestion completes returns nothing.

**Fix**:
1. Trigger ingestion:
   ```python
   bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
   sync_job = bedrock_agent.start_ingestion_job(
       knowledgeBaseId=KB_ID,
       dataSourceId=DATA_SOURCE_ID
   )
   job_id = sync_job['ingestionJob']['ingestionJobId']
   ```
2. Poll for completion:
   ```python
   import time
   while True:
       status = bedrock_agent.get_ingestion_job(
           knowledgeBaseId=KB_ID,
           dataSourceId=DATA_SOURCE_ID,
           ingestionJobId=job_id
       )['ingestionJob']['status']
       if status == 'COMPLETE':
           break
       time.sleep(10)
       print(f"Ingestion status: {status}")
   ```
3. Only query after `status == 'COMPLETE'`.

---

### 🔥 Real Developer Problem #9: S3 is Required for Knowledge Base Data Sources

**What happens**: You try to point the Knowledge Base at your local files or a direct URL. The console only accepts S3 buckets as data sources.

**Why it happens**: Bedrock Knowledge Bases ONLY support S3 (and optionally Confluence, SharePoint, Salesforce) as data sources. There's no "upload directly" option via API.

**Fix**:
1. Create an S3 bucket: `migration-copilot-docs-poc`
2. Upload documents: `aws s3 cp ./test_docs/ s3://migration-copilot-docs-poc/ --recursive`
3. Point Knowledge Base data source to the S3 bucket URI
4. Set bucket policy to allow Bedrock service role to read

**This is a fundamental architecture difference** from Qdrant (which stores vectors you send directly). Bedrock Knowledge Bases pull from managed data sources.

---

## Step 6: Wire Bedrock Knowledge Base into Context Retrieval Agent

### 🎯 POC Task
Modify `backend/app/agents/context_retrieval_agent.py` to add a third retrieval path: **Bedrock Knowledge Base** — alongside the existing MCP and Qdrant paths.

**Current retrieval hierarchy** (from the code):
```
1. MCP (Confluence via IBM Context Studio)  ← Primary
2. Qdrant (local vector store)              ← Fallback
```

**New hierarchy after this step**:
```
1. MCP (Confluence via IBM Context Studio)  ← Primary
2. Bedrock Knowledge Base                   ← New fallback
3. Qdrant (local vector store)              ← Last resort
```

**What to build**: A `BedrockKBRetriever` class in `backend/app/mcp/bedrock_kb_retriever.py` that wraps the Knowledge Base query and returns a `ContextPack` in the same format as `MCPConnector.retrieve()`.

**Gate Check**: ✅ Full workflow runs using Bedrock KB for context retrieval. ✅ `context_source` in state is `"bedrock_kb"`. ✅ Extracted facts match expectations.

---

### 🔥 Real Developer Problem #10: Citation Formatting Incompatible with Existing ContextPack Schema

**What happens**: Bedrock KB returns citations in this format:
```python
{
    "retrievedReferences": [{
        "content": {"text": "..."},
        "location": {"s3Location": {"uri": "s3://bucket/file.pdf"}},
        "metadata": {"x-amz-bedrock-kb-source-uri": "..."}
    }]
}
```

But `ContextPack` expects `Document` objects with `source`, `type`, `title`, `content`, `metadata` fields.

**Why it happens**: Bedrock KB returns AWS-native format; the `MCPConnector._normalize_resources()` was written for Confluence JSON-RPC format.

**Fix**: Write a `_normalize_bedrock_references()` method (similar to `_normalize_resources()`) that maps:
- `retrievedReference.content.text` → `Document.content`
- `retrievedReference.location.s3Location.uri` → `Document.metadata.source_url`
- `retrievedReference.metadata['x-amz-bedrock-kb-source-uri']` → `Document.id`
- `DocumentSource.QDRANT` → use a new `DocumentSource.BEDROCK_KB` enum value

---

## Step 7: Full Workflow End-to-End Test with Bedrock

### 🎯 POC Task
Run the **complete end-to-end workflow** using:
- **LLM**: Bedrock Claude 3 Haiku (extraction, questionnaire, intake draft)
- **Embeddings**: Amazon Titan Embed v2 (via new BedrockEmbedder)
- **Context Retrieval**: Bedrock Knowledge Base
- **State**: Redis (unchanged)
- **Orchestration**: LangGraph (unchanged)

The existing `POST /api/orchestration/start` + `POST /api/orchestration/execute` workflow should run without modifications to orchestration code.

**Test Command**:
```bash
# 1. Start backend with BEDROCK as primary
PRIMARY_PROVIDER=bedrock uvicorn app.main:app --reload

# 2. In another terminal, trigger workflow
curl -X POST http://localhost:8000/api/orchestration/start \
  -H "Content-Type: application/json" \
  -d '{"project_id": "bedrock-poc-test"}'

curl -X POST http://localhost:8000/api/orchestration/execute \
  -H "Content-Type: application/json" \
  -d '{"project_id": "bedrock-poc-test"}'
```

**Gate Check**: ✅ Workflow completes to `HUMAN_REVIEW` phase (same as with OpenAI/Gemini). ✅ `extracted_facts` has >10 facts. ✅ `missing_questions` has at least 1 question. ✅ `intake_draft` has all 8 required sections. ✅ LangSmith shows Bedrock traces (if using `langchain_aws.ChatBedrock`).

---

### 🔥 Real Developer Problem #11: Bedrock Throttling (ThrottlingException) at Scale

**What happens**: When extraction runs against a large document (32 facts, many LLM calls), you hit:
```
botocore.errorfactory.ThrottlingException: 
Too many requests, please wait before trying again.
```

**Why it happens**: Bedrock has per-account, per-model **throughput limits** (Transactions Per Minute). The extraction agent makes multiple LLM calls in quick succession, exhausting the limit.

**Fix**:
1. Add exponential backoff in `BedrockProvider`:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
   from botocore.exceptions import ClientError

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10),
       retry=retry_if_exception_type(ClientError)
   )
   async def _invoke_model(self, body):
       ...
   ```
2. For production: Request a quota increase via AWS console (Bedrock → Quota → Request increase)
3. Consider **Provisioned Throughput** for predictable workloads

**Note**: `tenacity` is already in `requirements.txt` — use it.

---

## Step 8: Observability — CloudWatch vs LangSmith

### 🎯 POC Task
Set up CloudWatch logging for Bedrock model invocations and compare the observability experience with LangSmith.

**What to build**: `backend/poc/step8_bedrock_logging.py`

Enable Bedrock model invocation logging via AWS Console:
1. Bedrock → Settings → Model invocation logging
2. Enable "Log to CloudWatch"
3. Set destination: `/aws/bedrock/model-invocations`
4. Set IAM role with `logs:CreateLogGroup`, `logs:CreateLogDelivery`

Then query logs:
```python
import boto3

logs = boto3.client('logs', region_name='us-east-1')
response = logs.filter_log_events(
    logGroupName='/aws/bedrock/model-invocations',
    filterPattern='"claude-3-haiku"',
    limit=10
)
for event in response['events']:
    print(event['message'][:200])
```

**Gate Check**: ✅ CloudWatch shows model invocation logs. ✅ Input/output tokens visible.

---

### 🔥 Real Developer Problem #12: Model Invocation Logging Requires Separate IAM Role

**What happens**: You enable logging but CloudWatch receives no logs:
```
# CloudWatch log group exists but is empty
```

**Why it happens**: Bedrock model invocation logging requires a **separate IAM service role** with specific permissions — it's NOT the same as your user/application IAM role. AWS must be explicitly authorized to write logs on behalf of Bedrock.

**Fix**:
1. Create IAM role: `BedrockModelInvocationLoggingRole`
2. Trust policy must include: `"Service": "bedrock.amazonaws.com"`
3. Permission policy must include:
   ```json
   {
     "Effect": "Allow",
     "Action": ["logs:CreateLogGroup", "logs:CreateLogDelivery", "logs:PutLogEvents"],
     "Resource": "arn:aws:logs:*:*:log-group:/aws/bedrock/*"
   }
   ```
4. Re-configure logging with this role ARN

---

## Summary: POC Step Progression

| Step | Topic | POC Output | Key Problem Learned |
|------|-------|------------|-------------------|
| **1** | First API Call | `bedrock_hello.py` runs | Model access must be explicitly enabled |
| **2** | BedrockProvider Interface | POC provider passes 3 tests | boto3 is sync; markdown stripping needed |
| **3** | Titan Embeddings | 1024-dim vectors generated | Qdrant collection dimension mismatch |
| **4** | Factory Integration | Full workflow uses Bedrock LLM | Response schema differences; LangSmith tracing gap |
| **5** | Knowledge Base RAG | KB query returns cited answer | Ingestion is async; S3 required as data source |
| **6** | Context Retrieval Wiring | Context agent uses Bedrock KB | Citation format incompatible with ContextPack |
| **7** | Full E2E Workflow | All phases complete with Bedrock | Throttling under extraction load |
| **8** | Observability | CloudWatch logs visible | IAM logging role setup required |

---

## Gate Rules — When to Move to Next Step

```
Step 1 Gate: boto3.invoke_model() returns text. No auth errors.
Step 2 Gate: generate(), generate_structured(), health_check() all pass.
Step 3 Gate: Titan embedding is 1024 floats. Qdrant accepts insertion.
Step 4 Gate: GET /health/providers shows bedrock: healthy. Workflow completes.
Step 5 Gate: KB query returns cited answer from ingested documents.
Step 6 Gate: Full workflow uses Bedrock KB for context_source.
Step 7 Gate: Intake draft has all 8 sections. State version reaches ~11.
Step 8 Gate: CloudWatch shows invocation logs with token counts.
```

---

## Files to Create (in Order)

```
backend/
├── poc/                              ← New directory for POC scripts (gitignore-able)
│   ├── step1_bedrock_hello.py
│   ├── step2_bedrock_provider.py
│   ├── step3_bedrock_embeddings.py
│   ├── step5_bedrock_knowledge_base.py
│   └── step8_bedrock_logging.py
└── app/
    ├── providers/
    │   └── bedrock_provider.py       ← Step 4 (production integration)
    ├── embeddings/
    │   └── bedrock_embedder.py       ← Step 3/4
    └── mcp/
        └── bedrock_kb_retriever.py   ← Step 6
```

---

## Environment Variables Required

```env
# AWS Credentials (for boto3)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token  # If using temp credentials / IAM role

# Bedrock Configuration
BEDROCK_REGION=us-east-1
BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_KNOWLEDGE_BASE_ID=your-kb-id  # After Step 5 setup

# Provider Selection
PRIMARY_PROVIDER=bedrock
FALLBACK_PROVIDER=openai   # Keep OpenAI as fallback during transition
```

---

## Python Packages to Add

```text
# Add to backend/requirements.txt for production Steps 4+
boto3>=1.34.0
aioboto3>=12.0.0          # Async boto3 wrapper
langchain-aws>=0.1.0      # For LangSmith-integrated LLM usage
botocore>=1.34.0
```

---

**Plan Written By**: Bob (AI Planning Agent)  
**Based On**: `docs/AWS_BEDROCK_LEARNING_PLAN.md` + full codebase analysis  
**Status**: Ready for implementation, one step at a time  
**Next Action**: Start Step 1 — switch to Agent mode and create `backend/poc/step1_bedrock_hello.py`
