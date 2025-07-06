from fastapi import FastAPI, Request, BackgroundTasks
import subprocess, os, json
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime
import logging
import openai
from openai import OpenAI
import requests
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

HASHNODE_TOKEN = os.getenv("HASHNODE_TOKEN")
PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

client = OpenAI(api_key=OPENAI_API_KEY)


class WebhookPayload(BaseModel):
    ref: str
    head_commit: dict
    commits: list
    repository: dict

# === Util: Create AI summary ===

def generate_summary(commit_message: str, repo: str, commit_type: str, author: str, timestamp: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "user",
                    "content": f"""
You're writing a short, developer-style blog journal entry based on a Git commit.

Write it in a clean and informative tone, suitable for a changelog or Hashnode devlog.

Include what changed and why it might matter — even if it's a small refactor or cleanup.

Here is the context:

🔧 Repository: {repo}  
📂 Type: {commit_type}  
🧑‍💻 Author: {author}  
🕒 Timestamp: {timestamp}  

📝 Commit Message: {commit_message}
"""
                }
            ],
            max_tokens=300,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("OpenAI API failed: %s", e)
        return f"{commit_type}: {commit_message}"

    



# === Util: Post to Hashnode ===
def post_to_hashnode(title: str, content: str) -> bool:
    url = "https://gql.hashnode.com"

    headers = {
        "Content-Type": "application/json",
        "Authorization": HASHNODE_TOKEN
    }

    query = """
    mutation CreateDraft($input: CreateDraftInput!) {
      createDraft(input: $input) {
        __typename
      }
    }
    """

    variables = {
        "input": {
            "title": title,
            "contentMarkdown": content,
            "publicationId": PUBLICATION_ID
        }
    }

    try:
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
        data = response.json()

        if "errors" in data:
            logger.error("❌ Hashnode API error:\n%s", json.dumps(data["errors"], indent=2))
            return False

        typename = data["data"]["createDraft"]["__typename"]
        logger.info("✅ Draft created (%s): %s", typename, title)
        return True

    except Exception as e:
        logger.exception("❌ Exception posting to Hashnode: %s", str(e))
        return False

async def process_commits(payload: dict):
    repo_name = payload["repository"]["full_name"]
    logger.info("🔔 Webhook received from repo: %s", repo_name)

    for commit in payload.get("commits", []):
        message = commit.get("message", "")
        commit_type = "Merged" if message.lower().startswith("merge") else "Committed"
        title = f"{repo_name} – {commit_type}: {message.splitlines()[0][:80]}"

        summary = generate_summary(
            commit_message=message,
            repo=repo_name,
            commit_type=commit_type,
            author=commit.get("author", {}).get("name", "Unknown"),
            timestamp=commit.get("timestamp", "Unknown")
        )

        posted = post_to_hashnode(title, summary)
        status = "✅ Posted to Hashnode" if posted else "❌ Failed to post"
        logger.info("%s: %s", status, title)






@app.get("/")
def root():
    return {"message": "IF YOU ARE SEEING THIS, YOU ARE ON THE RIGHT PATH"}


# === FastAPI Webhook Endpoint ===

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_commits, payload)
    return {"status": "accepted"}




# This is to keep the server awake - so that railway will not shut it down(hosted in thr free tier)
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test-post")
def test_post():
    title = "Test Post from Webhook App"
    content = "This is a test post to confirm Hashnode integration is working."
    success = post_to_hashnode(title, content)
    return {"success": success}
