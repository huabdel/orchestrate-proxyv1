# Connecting watsonx Workshop to watsonx Orchestrate
### External Agent Integration Guide via Code Engine Proxy


---

## Overview

This repo contains a Flask proxy deployed on IBM Code Engine that bridges watsonx Workshop and watsonx Orchestrate. It enables Workshop skills to delegate tasks to specialized Orchestrate agents (e.g. sending emails, retrieving Slack messages).

### Architecture

```
User (Workshop chat)

watsonx Workshop skill (External API)
       
Code Engine Proxy (/send)
        starts run + polls for result
watsonx Orchestrate agent
       
Response returned to Workshop
```


---

## Prerequisites

| Requirement | Details |
|---|---|
| IBM Cloud account | With access to Code Engine and Container Registry |
| watsonx Orchestrate instance | With at least one configured agent |
| watsonx Workshop access | Agent Creator space with skill configuration access |
| IBM Cloud API key | For authenticating to Orchestrate's API |
| IBM Container Registry | Namespace created in ICR |

---

## Step 1: Deploy to Code Engine

**Note**
 * To create a new Code Engine proxy: Start at Step 1.
 * To use an existing proxy or the one in this repo: Skip to Step 4

Go to **IBM Cloud -> Code Engine -> your project -> Applications -> Create**

| Field | Value |
|---|---|
| Name | `wxoproxy` (or any name) |
| Source | Source code |
| Code repo URL | URL of this repo |
| SSH secret | None (public repo) |
| Branch | `main` |
| Strategy | `Dockerfile` |
| Dockerfile | `Dockerfile` |
| Timeout | `10m` |
| Registry server | `private.de.icr.io` |
| Registry secret | Your ICR secret |
| Namespace | Your ICR namespace |
| Repository | `orchestrate-proxy` |
| Tag | `latest` |
| Domain mapping | `Public` |
| Port | `8080` |
| Min instances | `1` |

---

## Step 2: Set Environment Variables

Under **Environment variables** in Code Engine, add:

| Variable | Value |
|---|---|
| `INSTANCE_URL` | `https://api.eu-de.watson-orchestrate.cloud.ibm.com/instances/YOUR_INSTANCE_ID` |
| `AGENT_ID` | Your Orchestrate agent ID |
| `ENV_ID` | Your Orchestrate environment ID |
| `IBM_API_KEY` | Your IBM Cloud API key |

To find `AGENT_ID` and `ENV_ID`: go to your Orchestrate instance → open the agent → check the embed code snippet for `agentId` and `agentEnvironmentId`.

---

## Step 3: Verify Deployment

Once deployed, verify the proxy is running:

```
GET https://your-code-engine-url/health
```

Expected response:
```json
{"status": "ok"}
```

---

## Step 4: Configure watsonx Workshop

### 4.1 Create or open your agent skill

- Click **Add Skill**
- Give it a name and description relevant to what the Orchestrate agent does
- Under **Stream from External Agent**, toggle to **Yes**
- Click **Configure API → External API**

### 4.2 Configure headers

Under the **Headers** tab (Custom):

| Header Name | Value |
|---|---|
| `Content-Type` | `application/json` |

No auth header needed — the proxy handles IBM IAM token generation internally.

### 4.3 Configure the API endpoint

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `https://your-code-engine-url/send` |

### 4.4 Configure the request body

```json
{
  "message": "{{user_question}}"
  "history": "{{conversation_history}}" 
}
```

### 4.5 Test the connection

1. In the API test tool, replace `{{user_question}}` with a hardcoded test message
2. Click **Send** — you should get a response from your Orchestrate agent
3. If successful, restore `{{user_question}}` and save

---



