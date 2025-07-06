from fastapi import FastAPI, Request
import subprocess, os, json, openai, requests
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

HASHNODE_TOKEN = os.getenv("HASHNODE_TOKEN")
PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

class WebhookPayload(BaseModel):
    ref: str
    head_commit: dict
    commits: list
    repository: dict

# === Util: Create AI summary ===
def generate_summary(text: str):
    if not OPENAI_API_KEY:
        logger.warning("No OpenAI API key found — returning raw commit message.")
        return text

    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": f"Write a short, professional developer blog post summarizing this GitHub merge commit:\n\n{text}"
            }],
            max_tokens=200,
            temperature=0.7,
        )
        print(generate_summary("Merge branch 'feature/authentication' into main"))

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("OpenAI API failed: %s", str(e))
        return text
    



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






@app.get("/")
def root():
    return {"message": "IF YOU ARE SEEING THIS, YOU ARE ON THE RIGHT PATH"}


# === FastAPI Webhook Endpoint ===

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()
    repo_name = payload.get("repository", {}).get("full_name", "unknown")
    logger.info("🔔 Webhook received from repo: %s", repo_name)

    for commit in payload.get("commits", []):
        message = commit.get("message", "")
        commit_type = "Merged" if message.lower().startswith("merge") else "Committed"

        # Basic metadata
        author = commit.get("author", {}).get("name", "Unknown")
        timestamp = commit.get("timestamp", "Unknown time")
        short_message = message.splitlines()[0][:60]

        # Title format
        title = f"{repo_name} – {commit_type}: {short_message}"

        # Summary via ChatGPT with context
        contextual_prompt = (
            f"Write a professional, developer-style blog summary from this Git commit.\n\n"
            f"Repository: {repo_name}\n"
            f"Type: {commit_type}\n"
            f"Author: {author}\n"
            f"Timestamp: {timestamp}\n\n"
            f"Commit Message:\n{message}"
        )

        summary = generate_summary(contextual_prompt)

        # Add commit metadata at the end of the blog post
        summary += f"\n\n---\n🧑‍💻 Author: **{author}**  \n🕒 Timestamp: **{timestamp}**"

        # Post to Hashnode
        posted = post_to_hashnode(title, summary)
        if posted:
            logger.info("✅ Posted to Hashnode: %s", title)
        else:
            logger.error("❌ Failed to post: %s", title)

    return {"status": "processed"}



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
