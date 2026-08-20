# AI & ML Prototypes

A monorepo of machine-learning and AI engineering prototypes by [Ikram](https://github.com/ikram98ai) — spanning production-style AI applications, AWS SageMaker MLOps pipelines, LLM fine-tuning, and classic predictive modeling.

> **Note on history:** seven projects were merged in from formerly standalone repositories with their **full git history preserved** (via `git filter-repo` + `--allow-unrelated-histories` merges): `health_agent`, `mediscribe`, `passport_verification`, `hierRAG`, `compliance_verification`, `fakenews_detection`, and `turnover_prediction`. Run `git log <project-dir>` to see any project's original commits.

## Repository Map

```
prototypes/
├── ai-solutions/       # End-to-end AI applications (agents, RAG, vision, audio)
├── llm-finetuning/     # LLM/VLM fine-tuning experiments and one production project
├── sagemaker/          # AWS SageMaker training & deployment pipelines
├── predictive-models/  # Classic ML on tabular data (mostly Kaggle-style problems)
└── fastai-models/      # Deep-learning experiments with fastai
```

---

## ai-solutions/ — End-to-end AI applications

Full applications with backends, UIs, and infrastructure. Each subdirectory has its own README with setup instructions.

| Project | Description | Stack |
|---|---|---|
| [health_agent](ai-solutions/health_agent/) | Multi-agent wellness system: a master agent routes requests to wellness-check, video, classes, and document-inquiry (RAG) agents; escalates red flags to human CNAs | TypeScript, LangGraph, MongoDB, vector DB |
| [mediscribe](ai-solutions/mediscribe/) | Healthcare audio POC: record or upload patient consultations, transcribe and summarize into SOAP notes with Gemini | FastAPI, React + Tailwind, S3, DynamoDB |
| [passport_verification](ai-solutions/passport_verification/) | Passport information extraction plus face verification (passport photo vs. selfie), deployed with Docker and CI/CD | FastAPI, Docker, Terraform, GitHub Actions |
| [hierRAG](ai-solutions/hierRAG/) | Hierarchical-metadata RAG compared against standard semantic RAG, with a Gradio demo app, synthetic data generation, and a full evaluation and test suite | Python, Gradio, uv |
| [sales-agents](ai-solutions/sales-agents/) | Notebooks building AI agent pipelines for sales, customer outreach, and customer support | CrewAI-style agents |

Standalone notebooks in this folder cover hybrid RAG with Qdrant ([hybrid_rag.py](ai-solutions/hybrid_rag.py)), multimodal RAG, voice cloning with Dia, financial analysis, content creation at scale, support-data insight analysis, and text↔image generation.

## llm-finetuning/ — Fine-tuning LLMs and VLMs

| Project | Description |
|---|---|
| [compliance_verification](llm-finetuning/compliance_verification/) | Product-compliance and trademark-detection service: Qwen2.5-VL (7B), ViT, and Gemma-3 fine-tuning plus a RAG-backed FastAPI app deployed to AWS Lambda via Terraform and GitHub Actions |

Notebooks include PEFT/LoRA fine-tuning of Llama-3.1 (Sovai docs, chatbot human-preference prediction), FLAN-T5 fine-tuning, detoxifying summaries with RLHF-style tuning, Gemma GRPO for math reasoning (AIMO), Qwen2.5-VL 3B fine-tuning with Unsloth for invoice extraction, structured output with Outlines on SmolVLM, and US patent phrase matching.

## sagemaker/ — AWS MLOps pipelines

| Project | Description |
|---|---|
| [fakenews_detection](sagemaker/fakenews_detection/) | Automated SageMaker pipeline that cleans and balances a fake-news dataset, trains a RoBERTa classifier, evaluates against quality gates, and registers the model for human-approved deployment |
| [turnover_prediction](sagemaker/turnover_prediction/) | XGBoost pipeline forecasting product turnover days per retail partner; retailers trigger training on demand via Lambda + API Gateway and get a serverless inference endpoint |

Also: BERT and XGBoost pipeline notebooks and a clothes-review sentiment project using SageMaker Autopilot and BlazingText.

## predictive-models/ — Tabular ML

Kaggle-style notebooks covering churn prediction, employee retention, demand forecasting (Rohlik), taxi-fare and tipping prediction, TikTok claim classification, insurance claims, academic-success classification, Melbourne property price prediction, Santander customer transactions, and Titanic survival.

## fastai-models/ — fastai experiments

Collaborative filtering and paddy disease image classification.

---

## Working in this repo

- **Per-project setup**: the application projects (`health_agent`, `mediscribe`, `passport_verification`, `compliance_verification`) each carry their own README, dependency manifest (`package.json`, `pyproject.toml` + `uv.lock`, or `requirements.txt`), and where applicable a `makefile`, `Dockerfile`, and `terraform/` directory. Treat each as an independent app — there are no shared dependencies across projects.
- **Notebooks** are self-contained; open them in Jupyter or Colab. SageMaker notebooks expect an AWS account with SageMaker execution roles.
- **Secrets**: projects with a `.env.example` need it copied to `.env` and filled in (AWS credentials, Gemini/OpenAI API keys, etc.). Never commit `.env` files.
- **CI/CD note**: the `deploy.yml` workflows inside `passport_verification` and `compliance_verification` came from their original standalone repos; GitHub Actions ignores workflow files outside the root `.github/workflows/`, so they are inactive here until moved to the repo root with path filters.

## License

MIT — see [LICENSE](LICENSE). Some subprojects carry their own LICENSE files.
