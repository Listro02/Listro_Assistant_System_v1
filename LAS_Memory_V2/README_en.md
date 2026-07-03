# LAS_Memory_V2 (xMemory Project)

🇰🇷 [Korean README](README.md)

> 📄 **Notice**: The research and implementation results of this project have been documented in an academic paper format as a comprehensive report.
> - **REPORT** : [Design of a Dynamic RAG Memory Architecture for Conversational AI Assistants (L.A.S.)](https://docs.google.com/document/d/18ILmrwDFlmWfqEnGTj1-TT7385jOK3mhoyg0MUQDJ-E/) — *A Hierarchical Approach to Preventing Long-Term Memory Poisoning and Optimizing Token Efficiency*

---

## 📖 Overview

The memory system of the existing L.A.S. was a JSONL-based 3-layer architecture (short-term, mid-term summary, long-term facts) which had the advantage of operating lightweight without an external database. However, as conversations accumulated, limitations such as **response delays due to memory loading**, **irreversible contamination of long-term memory (Memory Poisoning)**, and **token explosion** were identified.

To address these issues, the proposed **xMemory 4-Layer Architecture** moves away from the traditional flat JSONL structure and is a hierarchical memory system that combines SQLite-based immutable raw logs with ChromaDB-based hierarchical vector search (RAG).

---

## ✨ Key Improvements & Structure

The new xMemory architecture has the following characteristics:

1. **4-Layer Architecture**
   - **Level 3 (Theme Node):** Hardcoded top-level interest categories (for global search).
   - **Level 2 (Fact Node):** Independent, contradiction-free short propositions (supporting metadata and state management).
   - **Level 1 (Episode Node):** Multi-dimensional contextual indices of conversation chunks pushed out from short-term memory.
   - **Level 0 (Raw Conversation):** Unprocessed, raw conversation logs (stored in SQLite, O(1) loading).

2. **Sliding Window for Short-Term Memory**
   - Instead of the traditional file I/O scanning method, it utilizes a 20-turn in-memory queue (Deque) to preserve chronological context.

3. **Async Consolidation Pipeline**
   - Conversations pushed out of short-term memory undergo fact extraction and vector embedding through background workers without blocking the main response loop.

4. **Deep Search Tool Calling**
   - Typically, it saves tokens by injecting only Level 2 facts and Level 1 indices, and calls the `request_deep_search` tool to load Level 0 raw conversations only when the AI deems it necessary.

---

## 📂 Docs Guide

Please refer to the documents in the `docs` folder for detailed analysis and design specifications.

- **REPORT** : [Design of a Dynamic RAG Memory Architecture for Conversational AI Assistants (L.A.S.)](https://docs.google.com/document/d/18ILmrwDFlmWfqEnGTj1-TT7385jOK3mhoyg0MUQDJ-E/) — *A Hierarchical Approach to Preventing Long-Term Memory Poisoning and Optimizing Token Efficiency*

* [**`LAS_memory_analysis.md`**](./docs/LAS_memory_analysis.md)
  * In-depth analysis and limitation report of the existing L.A.S. memory system.
* [**`LAS_technology_analysis.md`**](./docs/LAS_technology_analysis.md)
  * Technology stack and structural analysis report of the overall L.A.S. project.
* [**`LAS_xMemory_Architecture_v2.md`**](./docs/LAS_xMemory_Architecture_v2.md)
  * **[Core]** Detailed design specifications and pipeline flowchart for the new xMemory 4-layer architecture.
* [**`LAS_xMemory_TechStack.md`**](./docs/LAS_xMemory_TechStack.md)
  * Tech stack decisions (ChromaDB, SQLite, OpenAI Embedding, etc.) and directory change plans for implementing xMemory.

---

## 📊 Memory Visualization (Knowledge Graph)

Since the new memory system stores and layers memory in the form of metadata, we have converted the past conversation history into structured knowledge using the implemented system. The following is its visualization as a knowledge graph.

- **`memory_graph.html`**: [View Knowledge Graph Visualization](https://listro02.github.io/Listro_Assistant_System_v1/LAS_Memory_V2/memory_graph.html)

---

## ⚙️ Getting Started
- None.
- This project fundamentally replaces the memory system of the L.A.S. v1 structure with xMemory. Therefore, the execution method is the same as L.A.S. v1. However, because the system contains many hardcoded parts, execution in external environments cannot be guaranteed.
- In conclusion, if you wish to test xMemory, please contact the project manager (Listro).

---

## 🚀 Conclusion

- This was an independent attempt to implement the RAG-based hierarchical memory architecture prior to L.A.S. V2.
- We have implemented an xMemory activation button in the existing L.A.S. Kivy UI so that users can interact based on the new memory architecture.
