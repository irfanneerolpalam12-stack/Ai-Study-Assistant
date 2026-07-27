# 📚 AI Study Assistant

> A private, containerized full-stack web application for document analysis, study summaries, and interactive Q&A powered by local LLMs.

---

## 🚀 Overview

**AI Study Assistant** allows students and developers to interact with study materials using fully private, on-device AI. Powered by **Ollama** and **Gemma 2**, the app processes documents locally—ensuring **zero API costs, zero rate limits, and 100% data privacy**.

---

## ✨ Key Features

- 📄 **Document Q&A & Analysis:** Upload study materials to generate summaries, key takeaways, and practice questions.
- 🔒 **100% Local AI:** Driven by Ollama (`gemma2` & `nomic-embed-text`) with zero third-party cloud LLM dependencies.
- 🔐 **Dual Authentication:** Secure session management via Django REST Framework, SimpleJWT, and Google OAuth2.
- 🐳 **Dockerized Workflow:** Simple single-command setup using Docker Compose to orchestrate Django and Ollama.
- 🎨 **Responsive UI:** Clean, modern interface built with Vanilla JS, HTML5, and CSS with markdown and code syntax highlighting.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, Django 5.x, Django REST Framework (DRF), SimpleJWT
- **Frontend:** Vanilla JavaScript, HTML5, CSS3
- **AI Engine:** Ollama (Gemma 2, Nomic Embed Text)
- **Authentication:** Google OAuth 2.0, JWT Tokens
- **Database:** SQLite / ChromaDB
- **DevOps:** Docker, Docker Compose, Git

---

## ⚙️ Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/) installed

### 🐳 Running with Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/irfanneerolpalam12-stack/Ai-Study-Assistant.git](https://github.com/irfanneerolpalam12-stack/Ai-Study-Assistant.git)
   cd Ai-Study-Assistant/src/ai_assistant
