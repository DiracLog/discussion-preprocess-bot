# Discussion Preprocess Bot

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)
![Discord](https://img.shields.io/badge/Discord.py-2.0+-5865F2.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

An AI-powered Discord bot designed to capture, transcribe, and analyze voice conversations. It joins voice channels, records individual audio streams, and uses advanced processing to generate structured meeting minutes, sentiment analysis, and topic summaries.

## ⚡ Key Features

- **Multi-Server Support:** Safely handles simultaneous recordings across different Discord servers.
- **High-Fidelity Recording:** Captures individual audio streams for precise transcription.
- **AI-Powered Analysis:**
  - **Transcription:** Converts speech to text.
  - **Structure Extraction:** Identifies topics, key arguments, and decisions.
  - **Sentiment Analysis:** Detects the mood (Positive 🟢 / Negative 🔴) of the discussion.
- **Persistent Memory:** Saves logs and vector embeddings for long-term retrieval.
- **Dockerized:** Fully containerized for easy deployment and scalability.

## 🛠️ Prerequisites

Before you begin, ensure you have the following:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- A **Discord Bot Token**. (Get one from the [Discord Developer Portal](https://discord.com/developers/applications)).
- **FFmpeg** (Included automatically in the Docker container).

## 🚀 Quick Start

### 1. Clone the Repository

    git clone [https://github.com/DiracLog/discussion-preprocess-bot.git]
    cd discussion-preprocess-bot

### 2. Configure Environment Secrets
Create a file named `.env` in the root directory. **Do not commit this file.**

    # .env content
    DISCORD_TOKEN=your_discord_bot_token_here

### 3. Build and Run
Use Docker Compose to build the image and start the container in the background.

    docker-compose up -d --build

### 4. Verify Installation
Check the logs to ensure the bot has logged in successfully.

    docker logs -f discussion-bot

---

## 🤖 Commands

| Command | Description |
| :--- | :--- |
| **`!join`** | Summons the bot to your current voice channel and begins recording audio streams. |
| **`!cut`** | Stops the current recording buffer, transcribes the audio, and saves it to the session log. Use this periodically during long meetings. |
| **`!summarize`** | Analyzes the entire session history. It generates a structured report with topics, arguments, and sentiment scores, then saves everything to the database. |
| **`!stop`** | Disconnects the bot from the voice channel and cleans up temporary resources. |

---

## 📂 Project Structure

    ├── recordings/        # Saved WAV files
    ├── processed/         # Processed/Archived audio files
    ├── temp_pcm/          # Temporary raw audio buffers (Auto-cleaned)
    ├── Recordings.py      # Audio transcription engine
    ├── StructureEngine.py # NLP & Structure analysis logic
    ├── StorageEngine.py   # Database & Vector storage handler
    ├── DiscordBot.py      # Main Discord bot entry point
    ├── Dockerfile         # Container build instructions
    └── docker-compose.yml # Service orchestration

## 🛡️ Troubleshooting

**"Audio files are missing on my host machine"**
Ensure your `docker-compose.yml` has the correct volume mappings:

    volumes:
      - ./recordings:/app/recordings
      - ./processed:/app/processed

**"Bot connects but doesn't record"**
Make sure you have enabled the **Server Members Intent** and **Message Content Intent** in the Discord Developer Portal under the "Bot" tab.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
