# AI Agent System Overview

This repository contains an AI-driven agent system designed to automate wellness checks, video recommendations, class enrollments, and document inquiries. The Wellness Check Agent conducts surveys, identifies red flags, and alerts human CNAs when necessary. The Video Agent helps users filter and play relevant video content, while the Classes Agent facilitates activity recommendations, enrollments, and calendar updates. The Document Inquiry Agent retrieves information from a vector database using retrieval-augmented generation (RAG) for context-aware responses. The Master Agent processes user interactions, routes requests to the appropriate agents, retrieves necessary data, and sends responses back through /agent_endpoint. Data sources include a vector database for enhanced document retrieval, MongoDB for storing health and application data, and an agent memory for session context. Future enhancements involve implementing additional agents for resource booking and order processing, integrating more data sources, and improving AI-driven recommendations. 


 **Agent Architecture**
 
![Agent Architecture](https://github.com/ikram98ai/health_agent/blob/main/imgs/Agent%20Architecture.png)



# Project Setup Instructions

Follow these steps to set up and start the project:

## Prerequisites

- Node.js (v14 or higher)
- Docker

## Steps

1. **Clone the repository:**
    ```bash
    git clone https://github.com/ikram98ai/health_agent.git
    cd health_agent
    ```

2. **Install dependencies:**
    ```bash
    npm install
    ```

3. **Create the `.env` file:**
    ```bash
    cp .env.example .env
    ```

4. **Install and run Qdrant using Docker:**
    ```bash
    docker pull qdrant/qdrant
    docker run -p 6333:6333 qdrant/qdrant
    ```

5. **Start the project:**
    ```bash
    npm run start
    ```

You should now have the project running locally.

