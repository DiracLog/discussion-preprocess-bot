# Discussion Preprocess Bot

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)
![Discord](https://img.shields.io/badge/Discord.py-2.0+-5865F2.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An AI-powered Discord bot that captures, transcribes, analyzes, and stores structured insights from voice conversations.  
It records individual speaker audio streams, converts them into text, performs LLM-based analysis, and persists searchable meeting intelligence.

---

## ⚡ Key Features

- **Multi-Server Support:** Safely handles simultaneous recordings across different Discord servers.
- **High-Fidelity Recording:** Captures individual audio streams for precise transcription.
- **AI-Powered Analysis:**
  - **Transcription:** Faster-Whisper speech-to-text.
  - **Structure Extraction:** Identifies topics, arguments, and discussion items.
  - **Summarization:** Generates structured meeting minutes.
- **Persistent Memory:** Saves logs and vector embeddings for semantic retrieval.
- **Dockerized:** Fully containerized for easy deployment and scalability.
- **Modular Production Architecture:** Clean separation of audio, AI, orchestration, storage, and Discord layers.

---

## 🛠️ Prerequisites

Before you begin, ensure you have:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A **Discord Bot Token** from the [Discord Developer Portal](https://discord.com/developers/applications)
- **FFmpeg** (included automatically inside Docker container)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/DiracLog/discussion-preprocess-bot.git
cd discussion-preprocess-bot
```

### 2. Configure Environment Secrets

Create `.env` in project root:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

### 3. Build and Run

```bash
docker compose up -d --build
```

### 4. Verify Installation

```bash
docker logs -f discussion-bot
```

---

## 🤖 Slash Commands

| Command | Description |
| :--- | :--- |
| **/join** | Join your voice channel and begin capturing audio streams |
| **/cut** | Transcribe current buffered audio segment |
| **/summarize** | Generate full meeting report and store session memory |
| **/ask** | Search semantic discussion memory |
| **/stop** | Disconnect bot and cleanup session |

---

## 📂 Project Structure

```text
audio/
    gpu_setup.py
    sink.py
    transcriber.py

ai/
    ai_manager.py
    engine/
        analyst.py
        inference.py
        parser.py
        prompts.py
        model_loader.py
        chunking.py

core/
    orchestrator.py
    session_manager.py

storage/
    memory.py

bott/
    bot.py
    embeds.py
    commands/
        join.py
        cut.py
        summarize.py
        ask.py
        stop.py

Dockerfile
docker-compose.yml
requirements.txt
```

---

## 🛡️ Troubleshooting

**Bot connects but doesn't record**

Enable in Discord Developer Portal → Bot → Privileged Gateway Intents:

- Server Members Intent
- Message Content Intent

**Audio files missing on host**

Ensure docker-compose volume mapping:

```yaml
volumes:
  - ./recordings:/app/recordings
  - ./processed:/app/processed
```

---

## 📄 License

MIT License — see the LICENSE file for details.
