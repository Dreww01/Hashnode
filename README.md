# 📰 Auto Post Git Commits to Hashnode Journals with FastAPI

This project is a developer-focused automation tool that listens for GitHub webhooks and posts meaningful summaries of your commit history directly to your **Hashnode Journal** as drafts.

Built with **FastAPI**, **OpenAI GPT-4**, and the **Hashnode GraphQL API**, it turns commit messages into clean blog entries without ever leaving your terminal.

---

## 🚀 Features

* Receives GitHub webhooks for push events
* Filters commits (including merges)
* Generates clean summaries using GPT-4
* Posts as draft entries in your Hashnode Journal
* Deployable on platforms like Railway or Render
* Easily extendable for multiple repositories (coming soon)
* Async processing to prevent webhook timeout errors

---

## 🔧 Project Setup

### 1. **Clone the repo**

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### 2. **Install dependencies**

```bash
pip install -r requirements.txt
```

### 3. **Create a `.env` file**

Create a `.env` file in your project root with:

```env
HASHNODE_TOKEN=your_hashnode_personal_access_token
PUBLICATION_ID=your_hashnode_publication_id
OPENAI_API_KEY=your_openai_api_key
```

---

## 🔑 Getting Your API Keys

### 🟦 OpenAI (for GPT summaries)

1. Go to [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
2. Click "Create new secret key"
3. Copy and paste into your `.env` as `OPENAI_API_KEY`

### 🟦 Hashnode

#### Step 1: Get Your Hashnode Token

1. Go to [https://hashnode.com/settings/developer](https://hashnode.com/settings/developer)
2. Click **Generate New Token**
3. Copy it and add to `.env` as `HASHNODE_TOKEN`

#### Step 2: Get Your Publication ID

1. Run this GraphQL query:

```graphql
query {
  me {
    publications(first: 1) {
      edges {
        node {
          id
          title
        }
      }
    }
  }
}
```

You can test this with `curl`:

```bash
curl -X POST https://gql.hashnode.com \
  -H "Content-Type: application/json" \
  -H "Authorization: YOUR_HASHNODE_TOKEN" \
  -d '{"query": "{ me { publications(first: 1) { edges { node { id title } } } } }"}'
```

Find your publication `id` in the response and paste it into `.env` as `PUBLICATION_ID`.

---

## 🛠 How It Works

1. GitHub pushes a commit → webhook sends data to `/webhook`
2. FastAPI receives payload and filters commits
3. Each commit is summarized using GPT-4
4. Each summary is posted as a draft to your Hashnode Journal

---

## 🧪 Run Locally on Your Network

### 1. Start the FastAPI app

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

This makes your app accessible on your **local network** using your computer's IP.

### 2. Find your IP address

* On Windows: `ipconfig`
* On macOS/Linux: `ifconfig`

Use the IP with the port `8000` in your webhook URL:

```
http://192.168.x.x:8000/webhook
```

---

## 📦 Deploying to Railway (Example)

1. Push your project to GitHub
2. Go to [https://railway.app](https://railway.app)
3. Create a new project → Deploy from GitHub
4. Add your `.env` variables under "Variables"
5. Set the start command: `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## ⚙️ GitHub Webhook Setup

1. Go to your GitHub repo → Settings → Webhooks
2. Click "Add webhook"
3. Payload URL: `https://your-deployment-url.com/webhook`
4. Content type: `application/json`
5. Events: **Just the push event**
6. Save

GitHub will now POST to your FastAPI app on each push.

---

## 🧠 Example Summary Output

```
Title:
my-username/my-repo – Committed: Refactor generate_summary function for clarity

Summary:
This update improves the clarity of the `generate_summary` function by breaking up long lines and adding inline documentation. It helps future contributors understand how summaries are generated.
```

![image](https://github.com/user-attachments/assets/f1062da9-bf51-47a0-959b-17272eb9cab0)

---

## 📌 Planned Features (Future)

* [ ] ✅ Support multiple repositories → journals
* [ ] ✅ Custom tags per commit type (e.g., #fix, #feature, #docs)
* [ ] ✅ Full post publishing (not just drafts)
* [ ] ✅ Weekly commit roundups
* [ ] ✅ Frontend dashboard to manage journals
* [ ] ✅ Discord/Telegram notification integration
* [ ] ✅ Logging to file/database
* [ ] ✅ Retry logic for failed posts
* [ ] ✅ GitHub Actions integration for tighter automation

---

## 🙌 Credits

* [FastAPI](https://fastapi.tiangolo.com)
* [Hashnode GraphQL API](https://hashnode.com/graphql)
* [OpenAI Python SDK](https://github.com/openai/openai-python)

---

## 📬 License

MIT
