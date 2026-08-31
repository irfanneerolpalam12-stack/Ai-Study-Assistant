# 📚 AI Study Assistant

> A private, containerized full-stack web application for document analysis, study summaries, and interactive Q&A powered by local LLMs.

---

## 🚀 Overview

**AI Study Assistant** allows students and developers to interact with their study materials using fully private, on-device AI.

The application uses **Ollama with Llama 3** to analyze documents, generate summaries, answer questions, and create study materials locally.

Embeddings are generated using **Nomic Embed Text**, allowing documents to be stored and searched efficiently for context-aware responses.

### 🔒 Privacy First

All AI processing happens locally through Ollama.

* ✅ No external LLM API required
* ✅ No API costs
* ✅ No API rate limits
* ✅ Study documents remain on your local machine
* ✅ Llama 3 runs locally through Ollama

---

## ✨ Key Features

### 📄 Document Analysis

Upload study materials and use AI to:

* Generate document summaries
* Extract key points
* Identify important topics
* Generate study notes
* Create practice questions
* Ask questions about uploaded documents

### 💬 Interactive Q&A

Ask questions about your uploaded study materials and receive answers based on the document content.

The application uses document retrieval to provide relevant context to **Llama 3** before generating an answer.

### 🔒 Local AI

Powered by:

* **Llama 3** — Local language model
* **Nomic Embed Text** — Local embedding model
* **Ollama** — Local AI model runtime

No cloud-based LLM API is required.

### 🔐 Authentication

The application supports secure authentication using:

* Django REST Framework
* JWT authentication
* Session authentication
* Google OAuth 2.0

### 🐳 Dockerized

The project can be run using Docker and Docker Compose, making it easier to configure and run the application consistently.

### 🎨 Responsive Interface

The frontend is built using:

* HTML5
* CSS3
* Vanilla JavaScript

The interface supports:

* Responsive design
* Markdown responses
* Code syntax highlighting
* Document interaction
* AI chat functionality

---

## 🛠️ Tech Stack

### Backend

* Python 3.11
* Django 5.x
* Django REST Framework
* SimpleJWT

### Frontend

* HTML5
* CSS3
* Vanilla JavaScript

### AI

* Ollama
* Llama 3
* Nomic Embed Text

### Authentication

* JWT
* Django Authentication
* Google OAuth 2.0

### Database & Vector Storage

* SQLite
* ChromaDB

### DevOps

* Docker
* Docker Compose
* Git

---

## 🧠 AI Architecture

The application uses a local Retrieval-Augmented Generation (RAG) workflow.

```text
                ┌─────────────────────┐
                │     Study Document  │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Document Parser   │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Text Chunking     │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Nomic Embed Text    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │     ChromaDB        │
                └──────────┬──────────┘
                           │
                     User Question
                           │
                           ▼
                ┌─────────────────────┐
                │ Relevant Documents  │
                │      Retrieved      │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │      Llama 3        │
                │    Local LLM        │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │     AI Response     │
                └─────────────────────┘
```

---

## ⚙️ Getting Started

### Prerequisites

Before running the project, install:

* Docker Desktop
* Git
* Ollama (if running Ollama outside Docker)

Make sure Docker Desktop is running before starting the application.

---

## 🐳 Running with Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/irfanneerolpalam12-stack/Ai-Study-Assistant.git
```

### 2. Navigate to the Project

```bash
cd Ai-Study-Assistant/src/ai_assistant
```

### 3. Start the Application

```bash
docker compose up --build
```

Docker Compose will build and start the required services.

---

## 🤖 Ollama Setup

If Ollama is running locally on your machine, make sure the required models are installed.

### Install Llama 3

```bash
ollama pull llama3
```

### Install Nomic Embed Text

```bash
ollama pull nomic-embed-text
```

### Check Installed Models

```bash
ollama list
```

You should see something similar to:

```text
NAME                       SIZE
llama3:latest              ...
nomic-embed-text:latest    ...
```

---

## 🔧 Environment Variables

Create a `.env` file based on the project's environment configuration.

Example:

```env
DEBUG=True

SECRET_KEY=your-secret-key

OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

> Do not commit your real `.env` file or secret keys to GitHub.

---

## 📁 Project Structure

A typical project structure looks like:

```text
Ai-Study-Assistant/
│
├── src/
│   └── ai_assistant/
│       │
│       ├── manage.py
│       │
│       ├── ai_assistant/
│       │   ├── settings.py
│       │   ├── urls.py
│       │   └── ...
│       │
│       ├── accounts/
│       ├── documents/
│       ├── chat/
│       ├── ...
│       │
│       ├── static/
│       ├── templates/
│       │
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── requirements.txt
│       └── .env
│
├── .gitignore
└── README.md
```

> The exact folders may differ depending on the current project structure.

---

## 🔑 Authentication

The application supports multiple authentication mechanisms.

### JWT Authentication

JWT tokens are used for secure API authentication.

### Google OAuth 2.0

Users can authenticate using their Google account through OAuth 2.0.

### Django Authentication

Django's authentication system handles user accounts and sessions.

---

## 📚 Document Workflow

The general document-processing workflow is:

```text
Upload Document
       ↓
Extract Text
       ↓
Split Into Chunks
       ↓
Generate Embeddings
       ↓
Store Embeddings
       ↓
User Asks Question
       ↓
Search Relevant Chunks
       ↓
Send Context to Llama 3
       ↓
Generate Answer
```

This allows the AI to answer questions based on the user's uploaded study material instead of relying only on the model's general knowledge.

---

## 💻 Running Without Docker

If you want to run Django directly on your machine:

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment — Windows

```powershell
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Migrations

```bash
python manage.py migrate
```

### Start Django

```bash
python manage.py runserver
```

The application will normally be available at:

```text
http://127.0.0.1:8000/
```

---

## 🧪 Testing

Run Django tests with:

```bash
python manage.py test
```

If the project uses pytest:

```bash
pytest
```

---

## 🔒 Security

For production deployments:

* Set `DEBUG=False`
* Use a strong Django `SECRET_KEY`
* Configure allowed hosts
* Configure CORS correctly
* Never commit `.env`
* Use HTTPS
* Protect Google OAuth credentials
* Use secure JWT configuration
* Keep Ollama accessible only to trusted clients

---

## 💰 Cost

The application is designed around local AI inference.

| Component             | Cost                             |
| --------------------- | -------------------------------- |
| Django                | Free                             |
| Django REST Framework | Free                             |
| Ollama                | Free                             |
| Llama 3               | Free                             |
| Nomic Embed Text      | Free                             |
| ChromaDB              | Free                             |
| SQLite                | Free                             |
| Docker                | Free for applicable personal use |

No paid cloud LLM API is required for the core AI functionality.

---

## 🗺️ Future Improvements

Possible future features include:

* 📑 PDF document preview
* 🧠 Improved RAG pipeline
* 📝 Automatic quiz generation
* 🎯 Personalized study plans
* 📊 Learning progress dashboard
* 🔊 AI-generated audio summaries
* 🗂️ Multiple document collections
* 🔎 Advanced semantic search
* 💾 Conversation history
* 🌐 Production deployment

---

## 📜 License

This project is intended for educational and personal development purposes.

---

## 👨‍💻 Author

**Mohammed Irfan K**

Python Django React Full Stack Developer

---

⭐ If you find this project useful, consider giving the repository a star.
