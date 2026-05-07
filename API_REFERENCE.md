# Egloo Backend API Reference — Pingo 🐧

Welcome to the Egloo Backend API documentation. Egloo is a comprehensive "Second Brain" application designed to help you stay organized and intelligent. Your personal assistant, **Pingo**, works behind the scenes to process your data and answer your questions.

---

## 🌟 Overview

Egloo connects your disparate data sources into a single, searchable intelligence layer.

*   **Pingo 🐧**: Your intelligent assistant who knows everything about your data.
*   **Connected Sources**: Seamlessly integrate **Gmail**, **Slack**, and **Google Drive**.
*   **RAG Pipeline**: Advanced Retrieval-Augmented Generation that grounds AI answers in your actual data.
*   **Digests**: Automated daily summaries that extract key insights and action items.
*   **Topics**: Intelligent clustering of your data into meaningful themes.
*   **Saved Bookmarks**: Quick access to important query results and digests.
*   **LLM Fallback Chain**: Robust AI orchestration (Gemini → Groq → OpenRouter).

---

## 🚀 Quick Integration Flow

Follow these steps to get a user up and running:

1.  **Register**: Create a new account via `/auth/register`.
2.  **Login**: Authenticate via `/auth/login` and receive your JWT tokens.
3.  **Store JWT**: Save the `access_token` and `refresh_token` securely.
4.  **Authorize**: Attach `Authorization: Bearer <access_token>` to all subsequent headers.
5.  **Connect Source**: Navigate the user to `/sources/connect/gmail` to start OAuth.
6.  **Ingest**: Trigger a data sync via `/ingest/trigger-all`.
7.  **Query**: Ask Pingo questions using `/query/ask`.
8.  **Save**: Bookmark useful answers with `/saved`.
9.  **Read Digest**: Fetch the daily summary via `/digest/today`.

---

## 🔐 Authentication

Egloo uses JWT-based authentication.

*   **Access Token**: Short-lived (30 min) token for API authorization.
*   **Refresh Token**: Long-lived (7 days) token used to generate new access tokens.
*   **Header Format**: `Authorization: Bearer <access_token>`
*   **401 Flow**: If a request returns `401 Unauthorized`, attempt to call `/auth/refresh`. If that fails, redirect to login.
*   **Logout**: Blacklists the current token in Redis to prevent reuse.

---

## 🛠 API Modules

### 👤 Auth
Authentication and user management.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Create a new user account. | No |
| `POST` | `/api/v1/auth/login` | Exchange credentials for JWT tokens. | No |
| `POST` | `/api/v1/auth/refresh` | Use a refresh token to get a new access token. | No |
| `POST` | `/api/v1/auth/logout` | Revoke current tokens. | Yes |
| `GET` | `/api/v1/auth/me` | Get current user profile. | Yes |

---

### 🔌 Sources
Manage third-party integrations (Gmail, Slack, Drive).

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/sources` | List user's connected sources (Status of all available). | Yes |
| `GET` | `/api/v1/sources/available` | List all supported platforms (Global list). | No |
| `GET` | `/api/v1/sources/connect/{type}` | Get OAuth URL for Gmail or Slack. | Yes |
| `GET` | `/api/v1/sources/callback/{type}` | OAuth callback handler. | No |
| `DELETE` | `/api/v1/sources/{type}` | Disconnect a source. | Yes |
| `GET` | `/api/v1/sources/{type}/status` | Check connection health of a source. | Yes |

---

### 📥 Ingest
Trigger and monitor data ingestion pipelines.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/ingest/trigger/{id}` | Start ingestion for a specific source. | Yes |
| `POST` | `/api/v1/ingest/trigger-all` | Start ingestion for all connected sources. | Yes |
| `POST` | `/api/v1/ingest/trigger-direct/{id}` | Run ingestion synchronously (debug/small sources). | Yes |
| `GET` | `/api/v1/ingest/job/{id}` | Check status and progress of an ingestion job. | Yes |
| `GET` | `/api/v1/ingest/jobs` | List recent ingestion jobs. | Yes |

---

### 🔍 Query
The core RAG search and AI assistant interface.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/query/ask` | Ask Pingo a question about your data. | Yes |
| `POST` | `/api/v1/query/ask/stream` | Stream Pingo's response (Server-Sent Events). | Yes |
| `GET` | `/api/v1/query/history` | List previous questions and answers. | Yes |
| `DELETE` | `/api/v1/query/history` | Clear query history. | Yes |
| `GET` | `/api/v1/query/suggest` | Get AI-suggested follow-up questions. | Yes |
| `POST` | `/api/v1/query/save` | Shortcut to save a query result. | Yes |

---

### 🤖 LLM
Manage and monitor AI providers.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/llm/health` | Check which LLM providers are online. | Yes |
| `GET` | `/api/v1/llm/usage` | View token usage statistics. | Yes |
| `POST` | `/api/v1/llm/test` | Test a prompt against the LLM chain. | Yes |

---

### 📑 Digest
Automated daily summaries.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/digest/today` | Fetch today's generated digest. | Yes |
| `POST` | `/api/v1/digest/generate` | Manually trigger digest generation (Sync). | Yes |
| `POST` | `/api/v1/digest/generate/async` | Trigger digest generation in background. | Yes |
| `GET` | `/api/v1/digest/history` | List past digests. | Yes |
| `GET` | `/api/v1/digest/{id}` | Get a specific digest by ID. | Yes |
| `DELETE` | `/api/v1/digest/{id}` | Delete a digest. | Yes |
| `POST` | `/api/v1/digest/{id}/save` | Bookmark a digest. | Yes |

---

### 🏷 Topics
Intelligent thematic clustering.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/topics` | List current topic clusters. | Yes |
| `POST` | `/api/v1/topics/refresh` | Force re-clustering of data. | Yes |
| `POST` | `/api/v1/topics/refresh/async` | Trigger re-clustering in background. | Yes |
| `GET` | `/api/v1/topics/{id}` | Get details for a specific topic. | Yes |
| `DELETE` | `/api/v1/topics/{id}` | Remove a topic. | Yes |

---

### 🔖 Saved
Unified bookmarking for all content types.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/saved` | Create a new saved item. | Yes |
| `GET` | `/api/v1/saved` | List all saved items (Digests, Queries). | Yes |
| `GET` | `/api/v1/saved/counts` | Get count of saved items by type. | Yes |
| `GET` | `/api/v1/saved/{id}` | Get a specific saved item. | Yes |
| `DELETE` | `/api/v1/saved/{id}` | Remove a saved item. | Yes |
| `DELETE` | `/api/v1/saved/all` | Clear all bookmarks. | Yes |

---

### 🐧 Root & Health
Infrastructure endpoints.

| Method | Route | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API version and assistant info. | No |
| `GET` | `/health` | Deep health check (DB, Redis, AI). | No |

---

## 📦 Data Models (Schemas)

### AskRequest
```json
{
  "question": "What were the key takeaways from the meeting yesterday?",
  "use_cache": true,
  "stream": false
}
```

### AskResponse
```json
{
  "answer": "Pingo found that the meeting focused on project timelines...",
  "sources": [
    { "type": "gmail", "subject": "Meeting Minutes", "score": 0.95 }
  ],
  "model_used": "gemini-1.5-flash",
  "cached": false
}
```

### TokenResponse
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

---

## 📱 Frontend Best Practices

1.  **Secure Storage**: Never store JWT tokens in `localStorage`. Use **EncryptedSharedPrefs** (Android) or **Secure Enclave** (iOS).
2.  **Auth Interceptor**: Implement an HTTP interceptor to catch `401` errors and automatically fire the `/auth/refresh` request.
3.  **Job Polling**: Ingestion jobs are asynchronous. When triggering an ingest, use the `job_id` to poll `/ingest/job/{id}` every 2-3 seconds until the status is `success`.
4.  **Optimistic UI**: When a user clicks "Save", update the UI immediately before the server response arrives.
5.  **Streaming UI**: Use the `/query/ask/stream` endpoint for a more "alive" feel. Handle Server-Sent Events (SSE) to render tokens as they arrive.
6.  **Token Rotation**: Always use the refresh token to get a new access token before it expires to prevent session interruptions.

---

**Egloo Backend — Powered by Pingo 🐧**
