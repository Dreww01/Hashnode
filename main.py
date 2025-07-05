from fastapi import FastAPI, Request
import subprocess, os, json, openai, requests
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime


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
        return text
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Write a developer blog summary from this merge commit:\n\n{text}"
        }],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

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

# === FastAPI Webhook Endpoint ===
@app.post("/webhook")
async def handle_webhook(payload: WebhookPayload):
    for commit in payload.commits:
        message = commit["message"]
        if message.lower().startswith("merge"):
            title = message.split("\n")[0][:60]
            summary = generate_summary(message)
            posted = post_to_hashnode(title, summary)
            print("✅ Posted:", title) if posted else print("❌ Failed:", title)
    return {"status": "processed"}


# This is to keep the server awake - so that railway will not shut it down(hosted in thr free tier)
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()