# L.A.S. (Listro Assistant System)

🇰🇷 [Korean README](README.md)

This project developed L.A.S., an AI assistant operating as an independent agent that utilizes the OpenAI API to perform functions such as situation judgment, memory management, and conversation summarization. It was primarily designed to operate in a Discord environment and provides a GUI environment.

Beyond a simple chatbot, it has a structure that remembers the user's past conversations and judges the current situation to provide appropriate tools (such as playing music) or responses.

## 💻 Features
- **Situation Judgment (Judge)**: Analyzes user requests to determine whether it is a general conversation or the execution of a specific function (e.g., playing music) and branches the operation accordingly.
- **Memory Maintenance (Memory)**: Records important facts during conversations with the user in JSONL format and uses them as context in future conversations.
- **Automatic Summarization (Summary)**: Summarizes and manages conversation content to maintain continuous conversation context.
- **Logging System**: Systematically tracks and stores execution flows and conversation records through Python decorators (`@input_record`) and a custom logger.
- **GUI Environment Support**: Interacts with the user through a custom graphical user interface (GUI) based on the Kivy framework.

## 🛠 Tech Stack
- **Language**: Python 3
- **AI/LLM**: OpenAI API (separated purposes by model, such as `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4.1-nano`)
- **GUI**: Kivy
- **Data Storage**: JSONL (local lightweight data storage for conversation logs, memory, etc.)

## 📁 Project Structure
```
Project/
├── main.py                # Program entry point
├── MODULE/                # Core logic collection
│   ├── LAS.py             # AI Assistant Core System (judgment, memory, summary management)
│   ├── OPENAI_ai.py       # OpenAI API communication module
│   ├── GUI_LAS.py         # Kivy-based GUI controller
│   ├── las_gui_.kv        # Kivy layout file
│   └── log_*.py           # Custom logging and JSONL I/O handlers
├── DATABASE/              # (Git Ignore) User conversation logs and memory storage
├── .env                   # (Git Ignore) Environment variables for API keys and paths
└── .gitignore             # Git ignored items definitions
```

## ⚙️ Getting Started
- None.
- This project was not developed for deployment purposes, so there will be no instructions provided on how to run it.

## 🌱 TODO
Since this was created during my high school days when I did not know much about programming architecture, there are many inefficient logic, structures, and hardcoded parts. Therefore, I plan to refactor this and proceed with a new project called 'Listro_Assistant_System_v2' in the future.

- Advanced Error Handling
- Refactoring inter-module dependencies and hardcoded parts
- Integration of additional features (in the form of plugins)

## ✒️ Regarding partial feature improvements
Before L.A.S. v2, the improvement of the memory system was temporarily implemented and verified in v1. This can be checked in Issue Tracking.

Here is the report of the task:
- https://docs.google.com/document/d/18ILmrwDFlmWfqEnGTj1-TT7385jOK3mhoyg0MUQDJ-E/edit?usp=sharing 

Additionally, the prototype design and validation of the new RAG-based hierarchical memory system combining SQLite and ChromaDB can be found at the link below:
- [**LAS_Memory_V2 (xMemory Project) README**](./LAS_Memory_V2/README_en.md)

