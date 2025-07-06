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
from datetime import datetime

# Set up logging so you can see info and error messages in your console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file (for secrets like API keys)
load_dotenv()

# Get your secret tokens and keys from environment variables
HASHNODE_TOKEN = os.getenv("HASHNODE_TOKEN")
PUBLICATION_ID = os.getenv("HASHNODE_PUBLICATION_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create the FastAPI app instance
app = FastAPI()

# Set up the OpenAI client with your API key
client = OpenAI(api_key=OPENAI_API_KEY)

# Define the expected structure of the webhook payload using Pydantic
class WebhookPayload(BaseModel):
    ref: str
    head_commit: dict
    commits: list
    repository: dict

# Utility function to format a timestamp string to just "HH:MM"
def format_time_only(timestamp: str) -> str:
    try:
        # Convert ISO timestamp to datetime object
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception as e:
        logger.warning("⚠️ Failed to format time: %s", e)
        return timestamp

# === Util: Create AI summary ===

# This function asks OpenAI to generate a short summary for a commit
def generate_summary(commit_message: str, repo: str, commit_type: str, author: str, timestamp: str) -> str:
    try:
        # Send a prompt to OpenAI's GPT-4 to generate a devlog-style summary
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

        # Return the generated summary text
        content = response.choices[0].message.content
        return content.strip() if content else f"{commit_type}: {commit_message}"

    except Exception as e:
        logger.error("OpenAI API failed: %s", e)
        # If OpenAI fails, just return the commit type and message
        return f"{commit_type}: {commit_message}"

# === Util: Post to Hashnode ===

# This function posts a draft article to Hashnode using their API
def post_to_hashnode(title: str, content: str) -> bool:
    url = "https://gql.hashnode.com"

    headers = {
        "Content-Type": "application/json",
        "Authorization": HASHNODE_TOKEN
    }

    # GraphQL mutation to create a draft post
    query = """
    mutation CreateDraft($input: CreateDraftInput!) {
      createDraft(input: $input) {
        __typename
      }
    }
    """

    # Variables for the GraphQL mutation
    variables = {
        "input": {
            "title": title,
            "contentMarkdown": content,
            "publicationId": PUBLICATION_ID
        }
    }

    try:
        # Send the POST request to Hashnode
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
        data = response.json()

        # Check for errors in the response
        if "errors" in data:
            logger.error("❌ Hashnode API error:\n%s", json.dumps(data["errors"], indent=2))
            return False

        typename = data["data"]["createDraft"]["__typename"]
        logger.info("✅ Draft created (%s): %s", typename, title)
        return True

    except Exception as e:
        logger.exception("❌ Exception posting to Hashnode: %s", str(e))
        return False

# This function processes each commit in the webhook payload
async def process_commits(payload: dict):
    # Get the repository name from the payload
    repo_name = payload["repository"]["full_name"]
    logger.info("🔔 Webhook received from repo: %s", repo_name)

    # Local helper to format timestamp (could use the global one instead)
    def format_time_only(timestamp_str):
        try:
            dt = datetime.fromisoformat(timestamp_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return timestamp_str

    # Loop through each commit in the payload
    for commit in payload.get("commits", []):
        message = commit.get("message", "")
        # Decide if this is a merge or a regular commit
        commit_type = "Merged" if message.lower().startswith("merge") else "Committed"
        # Create a title for the Hashnode post (first line of commit message, max 80 chars)
        title = f"{repo_name} – {commit_type}: {message.splitlines()[0][:80]}"
        
        # Generate an AI summary for the commit
        summary = generate_summary(
            commit_message=message,
            repo=repo_name,
            commit_type=commit_type,
            author=commit.get("author", {}).get("name", "Unknown"),
            timestamp=format_time_only(commit.get("timestamp", "Unknown"))
        )
  
        # Post the summary to Hashnode as a draft
        posted = post_to_hashnode(title, summary)
        status = "✅ Posted to Hashnode" if posted else "❌ Failed to post"
        logger.info("%s: %s", status, title)

# Root endpoint to check if the server is running
@app.get("/")
def root():
    return {"message": "IF YOU ARE SEEING THIS, YOU ARE ON THE RIGHT PATH"}

# === FastAPI Webhook Endpoint ===

# This endpoint receives webhook POST requests (e.g., from GitHub)
@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    # Parse the incoming JSON payload
    payload = await request.json()
    # Process commits in the background (so the webhook returns quickly)
    background_tasks.add_task(process_commits, payload)
    return {"status": "accepted"}

# Health check endpoint to keep the server awake (useful for free hosting)
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

'''
# (Optional) Test endpoint to manually post a test article to Hashnode
@app.get("/test-post")
def test_post():
    title = "Test Post from Webhook App"
    content = "This is a test post to confirm Hashnode integration is working."
    success = post_to_hashnode(title, content)
    return {"success": success}
'''