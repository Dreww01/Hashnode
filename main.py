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
def post_to_hashnode(title, content):
    url = "https://gql.hashnode.com"
    headers = {
        "Authorization": HASHNODE_TOKEN,
        "Content-Type": "application/json"
    }

    query = """
    mutation CreateStory($input: CreateStoryInput!) {
      createStory(input: $input) {
        post {
          title
          slug
        }
      }
    }
    """

    variables = {
        "input": {
            "title": title,
            "contentMarkdown": content,
            "publicationId": PUBLICATION_ID,
            "tags": [{"_id": "56744721958ef13879b9549b", "name": "Git"}],
            "isPartOfPublication": True
        }
    }

    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    return response.status_code == 200

@app.get("/")
def root():
    return {"message": "IF YOU ARE SEEING THIS, YOU ARE ON THE RIGHT PATH"}


# === FastAPI Webhook Endpoint ===
@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()  # ✅ parse raw body safely
    print("🔔 Webhook received:", payload)

    for commit in payload.get("commits", []):
        message = commit.get("message", "")
        if message.lower().startswith("merge"):
            title = message.split("\n")[0][:60]
            summary = generate_summary(message)
            posted = post_to_hashnode(title, summary)
            logger.info("✅ Posted:", title) if posted else print("❌ Failed:", title)

    return {"status": "processed"}


# This is to keep the server awake - so that railway will not shut it down(hosted in thr free tier)
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
