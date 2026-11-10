# Curated free resources

Every resource here is **free**. Lessons link the specific resource for each topic; this page is the master list for browsing and long-term reference.

Legend: ⭐ best first read · 📘 book/course · 📄 paper · 🛠 docs/tool · ✍️ blog post

---

## Course-wide companions

These run in parallel with the whole course. If you only bookmark five links, bookmark these.

| | Resource | What it covers |
|---|---|---|
| ⭐📘 | [Machine Learning in Production (CMU, Christian Kästner)](https://mlip-cmu.github.io/book/) | Online book + lectures; the closest free match to this course's scope |
| ⭐📘 | [Made With ML (Goku Mohandas)](https://madewithml.com) | Notebook → tested, tracked, served ML system |
| ⭐📘 | [MLOps Zoomcamp (DataTalks.Club)](https://github.com/DataTalksClub/mlops-zoomcamp) | MLflow, orchestration, deployment, monitoring: hands-on |
| ⭐✍️ | [What We Learned from a Year of Building with LLMs](https://applied-llms.org) | Production LLM lessons from practitioners |
| ⭐📘 | [Google SRE books (SRE Book + Workbook)](https://sre.google/books/) | Reliability, SLOs, incident response, release engineering |
| 📘 | [Stanford CS 329S: ML Systems Design](https://stanford-cs329s.github.io) | Lecture notes on ML systems design |
| 📘 | [Full Stack Deep Learning](https://fullstackdeeplearning.com) | Course + LLM Bootcamp videos |
| 📘 | [The Missing Semester of Your CS Education (MIT)](https://missing.csail.mit.edu) | Shell, Git, editors, debugging |

## Module 0 · Foundations
| | Resource |
|---|---|
| 🛠 | [uv documentation](https://docs.astral.sh/uv/) |
| 🛠 | [Ollama](https://ollama.com): run LLMs locally |
| 🛠 | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) |
| ⭐📘 | [Google Machine Learning Crash Course](https://developers.google.com/machine-learning/crash-course) |
| 📘 | [Hugging Face LLM Course](https://huggingface.co/learn/llm-course) |

## Module 1 · From Prototype to Production
| | Resource |
|---|---|
| ⭐✍️ | [Rules of Machine Learning (Martin Zinkevich, Google)](https://developers.google.com/machine-learning/guides/rules-of-ml) |
| 📄 | *Hidden Technical Debt in Machine Learning Systems* (Sculley et al., NeurIPS 2015): search the title |
| ⭐🛠 | [MLOps: Continuous delivery and automation pipelines in ML (Google Cloud)](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning) |
| ⭐✍️ | [Timeouts, retries and backoff with jitter (AWS Builders' Library)](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) |
| ✍️ | [Patterns for Building LLM-based Systems & Products (Eugene Yan)](https://eugeneyan.com/writing/llm-patterns/) |
| ⭐🛠 | [The Twelve-Factor App](https://12factor.net) |
| 🛠 | [FastAPI: Concurrency and async/await](https://fastapi.tiangolo.com/async/) |
| 🛠 | [Docker: Get started](https://docs.docker.com/get-started/) |
| 🛠 | [Kubernetes Basics tutorial](https://kubernetes.io/docs/tutorials/kubernetes-basics/) |
| 🛠 | [gRPC introduction](https://grpc.io/docs/what-is-grpc/introduction/) |

## Module 2 · Data and Model Pipelines
| | Resource |
|---|---|
| ⭐📘 | [Data Engineering Zoomcamp (DataTalks.Club)](https://github.com/DataTalksClub/data-engineering-zoomcamp) |
| 🛠 | [DVC documentation](https://dvc.org/doc) |
| 🛠 | [Pandera](https://pandera.readthedocs.io) and [Great Expectations](https://greatexpectations.io) |
| ⭐✍️ | [Introducing Contextual Retrieval (Anthropic)](https://www.anthropic.com/news/contextual-retrieval) |
| 📄 | [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) |
| 📄 | [From Local to Global: A Graph RAG Approach](https://arxiv.org/abs/2404.16130) |
| 🛠 | [Qdrant documentation](https://qdrant.tech/documentation/) |
| 🛠 | [MLflow documentation](https://mlflow.org/docs/latest/index.html) |
| ⭐📘 | [Deep Learning Tuning Playbook (Google Research)](https://github.com/google-research/tuning_playbook) |
| 📄 | [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) |
| 📘 | [The Ultra-Scale Playbook (Hugging Face)](https://huggingface.co/spaces/nanotron/ultrascale-playbook) |

## Module 3 · Serving, Inference and Optimization
| | Resource |
|---|---|
| ⭐✍️ | [Making Deep Learning Go Brrrr From First Principles (Horace He)](https://horace.io/brrr_intro.html) |
| ✍️ | [Transformer Inference Arithmetic (kipply)](https://kipp.ly/transformer-inference-arithmetic/) |
| ⭐📘 | [How to Scale Your Model (Google DeepMind)](https://jax-ml.github.io/scaling-book/) |
| 📄 | [Efficient Memory Management for LLM Serving with PagedAttention (vLLM)](https://arxiv.org/abs/2309.06180) |
| 🛠 | [vLLM documentation](https://docs.vllm.ai) |
| ✍️ | [How continuous batching enables 23x throughput (Anyscale)](https://www.anyscale.com/blog/continuous-batching-llm-inference) |
| ⭐✍️ | [A Visual Guide to Quantization (Maarten Grootendorst)](https://newsletter.maartengrootendorst.com/p/a-visual-guide-to-quantization) |
| 📘 | [MIT 6.5940 TinyML and Efficient Deep Learning (Song Han)](https://efficientml.ai) |
| 📄 | [FlashAttention](https://arxiv.org/abs/2205.14135) · [Speculative decoding](https://arxiv.org/abs/2211.17192) |
| 🛠 | [ONNX Runtime](https://onnxruntime.ai) |
| 🛠 | [Artificial Analysis](https://artificialanalysis.ai): model price and speed comparisons |

## Module 4 · Evaluation and Monitoring
| | Resource |
|---|---|
| ⭐🛠 | [scikit-learn: Probability calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| ⭐✍️ | [Your AI Product Needs Evals (Hamel Husain)](https://hamel.dev/blog/posts/evals/) |
| ✍️ | [Creating a LLM-as-a-Judge That Drives Business Results (Hamel Husain)](https://hamel.dev/blog/posts/llm-judge/) |
| ✍️ | [Evaluating the Effectiveness of LLM-Evaluators (Eugene Yan)](https://eugeneyan.com/writing/llm-evaluators/) |
| 🛠 | [Ragas](https://docs.ragas.io) · [DeepEval](https://github.com/confident-ai/deepeval) · [promptfoo](https://www.promptfoo.dev) |
| ⭐✍️ | [Data Distribution Shifts and Monitoring (Chip Huyen)](https://huyenchip.com/2022/02/07/data-distribution-shifts-and-monitoring.html) |
| 🛠 | [OpenTelemetry](https://opentelemetry.io/docs/) · [Prometheus](https://prometheus.io/docs/introduction/overview/) · [Grafana tutorials](https://grafana.com/tutorials/) |
| 🛠 | [Evidently AI](https://www.evidentlyai.com): open-source drift reports and a free ML observability course |

## Module 5 · Security and Governance
| | Resource |
|---|---|
| ⭐🛠 | [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) |
| ⭐✍️ | [Simon Willison on prompt injection](https://simonwillison.net/tags/prompt-injection/) |
| 🛠 | [MITRE ATLAS](https://atlas.mitre.org) |
| 🛠 | [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org) |
| 🛠 | [Microsoft Presidio](https://microsoft.github.io/presidio/) |
| ⭐📘 | [Interpretable Machine Learning (Christoph Molnar)](https://christophm.github.io/interpretable-ml-book/) |
| 🛠 | [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) |
| 🛠 | [EU AI Act explorer](https://artificialintelligenceact.eu) |

## Module 6 · Scaling and Operations
| | Resource |
|---|---|
| 🛠 | [Kubernetes documentation](https://kubernetes.io/docs/home/) · [Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) |
| ⭐📘 | [Dagster University](https://courses.dagster.io) |
| ⭐🛠 | [PagerDuty Incident Response guide](https://response.pagerduty.com) |
| ✍️ | [CanaryRelease](https://martinfowler.com/bliki/CanaryRelease.html) · [BlueGreenDeployment](https://martinfowler.com/bliki/BlueGreenDeployment.html) (Martin Fowler) |
| ⭐✍️ | [Building Effective Agents (Anthropic)](https://www.anthropic.com/research/building-effective-agents) |
| ✍️ | [System Design for Recommendations and Search (Eugene Yan)](https://eugeneyan.com/writing/system-design-for-discovery/) |
| ⭐🛠 | [ML system design: 650+ case studies (Evidently AI)](https://www.evidentlyai.com/ml-system-design) |

---

Found a dead link or a better free resource? Please open an issue or a PR.
