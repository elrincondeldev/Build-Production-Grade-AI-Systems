# Build Production-Grade AI Systems · Edición en español

Esta es la edición en español del curso. Sigue al original en inglés archivo a archivo, con los mismos IDs estables, así que el progreso, las tarjetas de repaso y los labs son los mismos en los dos idiomas.

| Módulo | Estado |
|---|---|
| [0 · Fundamentos](modules/00-foundations/README.md) | Traducido |
| [1 · Del prototipo a producción](modules/01-prototype-to-production/README.md) | Traducido |
| 2–6 | Solo en inglés por ahora: [ir al curso en inglés](../../README.md) |

El resto del curso (datasets, handbook, plantillas, capstone y código de los labs) está en inglés; los enlaces de esta edición llevan allí cuando algo no está traducido.

---

## Para quien traduce o revisa

### Cómo se trabaja

- Cada archivo traducido vive en la misma ruta que su original bajo `i18n/es/`: `modules/00-foundations/01-setup-your-workbench.md` se traduce en `i18n/es/modules/00-foundations/01-setup-your-workbench.md`.
- Un primer borrador puede hacerse con ayuda de un LLM, siguiendo esta guía, pero **nada entra en `main` sin revisión humana**: la PR es la revisión. Nunca se publica una traducción automática sin revisar.
- [`translated-from.yaml`](translated-from.yaml) apunta, para cada archivo traducido, el commit del original en inglés del que sale. Cuando el inglés cambia, la plataforma marca como desactualizadas las secciones afectadas y muestra el inglés hasta que se revisen. Al actualizar una traducción, actualiza también su commit.
- Un módulo se publica en la plataforma solo cuando todos sus archivos (README, lecciones, cuestionario y lab) están traducidos.
- `python3 tools/check_ids.py` comprueba que cada archivo traducido lleva exactamente los IDs de su original, en el mismo orden.

### Lo que nunca cambia

- **Los IDs**: cada comentario `<!-- id: … -->` se copia tal cual, en el mismo sitio.
- **La estructura**: los mismos encabezados en el mismo orden, con los mismos emojis y números (`## 4. …` sigue siendo `## 4. …`), las mismas preguntas y los mismos pasos.
- **El código**: los bloques de código, comandos, nombres de archivos, identificadores y salidas de herramientas se quedan en inglés, sin tocar (comentarios incluidos). Algunos contienen a propósito ejemplos de prompt injection.
- **Los comentarios HTML que no son IDs**: se copian sin traducir.
- **Los nombres de los personajes** y sus cargos, que van en inglés: `> **De: Maya (Engineering Manager)**`.

### El formato en español

La plataforma lee la estructura por estas palabras, así que deben escribirse exactamente así:

| En inglés | En español |
|---|---|
| `# Lesson 0.1: Title` | `# Lección 0.1: Título` |
| `# Module 0: Title` | `# Módulo 0: Título` |
| `# Module 0 quiz: Title` | `# Cuestionario del módulo 0: Título` |
| `# 🛠 Lab 0: Title` | `# 🛠 Lab 0: Título` |
| `## 📨 The situation` | `## 📨 La situación` |
| `> **From: Maya (Engineering Manager)**` | `> **De: Maya (Engineering Manager)**` |
| `## 🎯 By the end you can` | `## 🎯 Al terminar podrás` |
| `## 🤔 Predict first` | `## 🤔 Predice primero` |
| `## 🧪 Try it` | `## 🧪 Pruébalo` |
| `## 🏭 In the real world` | `## 🏭 En el mundo real` |
| `## ✅ Check yourself` con `<summary>Q1. …` | `## ✅ Comprueba lo aprendido` con `<summary>P1. …` |
| `## 💬 Explain it back` | `## 💬 Explícalo con tus palabras` |
| `## 🔑 Key takeaways` | `## 🔑 Ideas clave` |
| `## 📚 Go deeper (free)` | `## 📚 Para profundizar (gratis)` |
| `<details><summary>Answer</summary>` | `<details><summary>Respuesta</summary>` |
| `🔁 *(Module 0)*` | `🔁 *(Módulo 0)*` |
| `### Step 3 · Title` (`(optional, …)`) | `### Paso 3 · Título` (`(opcional, …)`) |
| `⏱ ~60 min · 🎚 Level: … · 🧰 Needs: …` | `⏱ ~60 min · 🎚 Nivel: … · 🧰 Requisitos: …` |
| `[Course home] › [Module 0] › Lesson 0.1` | `[Inicio del curso] › [Módulo 0] › Lección 0.1` |
| `⬅️ [Previous] · ➡️ [Next]` | `⬅️ [Anterior] · ➡️ [Siguiente]` |

Los niveles se quedan como en el original (`Core`, `Advanced`), igual que los títulos de los módulos que aún no están traducidos cuando se mencionan.

### Estilo

- **Español neutro internacional**, para España y Latinoamérica: `tú`, sin `vosotros` ni `vos`, sin modismos regionales.
- **Sin formas con género dirigidas a quien aprende ni a los personajes**: «Te damos la bienvenida», no «Bienvenido»; «quien aprende», «el equipo», «cada persona». Reformula en lugar de usar «@», «x» o «-e». A los personajes se les nombra por su nombre, nunca con pronombres con género.
- **Claro y directo**, como el original: frases cortas, segunda persona, imperativo para las instrucciones («Ejecuta…», «Comprueba…»).
- **Números y unidades**: coma decimal en el texto (`0,8`), espacio antes de `%` (`92,4 %`) y espacio como separador de miles a partir de cinco cifras (`50 000`); los valores dentro del código no se tocan.

### Términos

Los términos de oficio se quedan en inglés cuando así se usan en la industria. En caso de duda, manda esta tabla; si un término no está, sigue el uso más común en equipos técnicos hispanohablantes y añádelo aquí.

| Se queda en inglés | Se traduce |
|---|---|
| prompt, token, embedding, RAG, LLM, fine-tuning | model → modelo, training → entrenamiento, inference → inferencia |
| pipeline, dataset, feature (de un modelo), label | weights → pesos, overfitting → sobreajuste (overfitting) |
| API, endpoint, request/response (en contexto HTTP) | deploy → desplegar, deployment → despliegue |
| CI, on-call, canary, rollback, health check, timeout | retry → reintento, latency → latencia, hallucination → alucinación |
| accuracy, precision, recall, F1 | context window → ventana de contexto |
| lab, handbook, Engineer y demás cargos | quiz → cuestionario, cheat sheet → hoja de referencia |
| Core, Advanced (niveles) | workbench → entorno de trabajo |
| Definition of Done, baseline, streaming, rate limit, backoff, jitter | header → cabecera, body → cuerpo, path → ruta, status code → código de estado |
| lock file, fixtures, notebook, commit, fork, runtime, worker, staging | leakage → fuga de datos (leakage), underfitting → subajuste, threshold → umbral |
| training/serving skew, prefill, decode, groundedness | event loop → bucle de eventos, coroutine → corrutina, idempotency key → clave de idempotencia |
| Mermaid: los diagramas son bloques de código y se quedan en inglés | Break it → Rómpelo, Extend it → Amplíalo, Hint → Pista, Solution → Solución |
| | Production tip → Consejo de producción, Common mistake → Error común, Under the hood → Por dentro, Expected output → Salida esperada |

### Enlaces

- A un archivo que también está traducido: la misma ruta relativa que en el original (de la lección 0.1 a la 0.2, `02-python-for-production.md`).
- A cualquier otra cosa (otros módulos, `docs/`, `datasets/`, código de los labs): la ruta al original en inglés, desde el archivo traducido. Desde `i18n/es/modules/00-foundations/` eso es `../../../../` más la ruta desde la raíz del repo (`../../../../modules/02-data-and-model-pipelines/README.md`).
- «Inicio del curso» (`../../README.md` desde un módulo) lleva a esta página.
- Los anclas (`#…`) cambian con el encabezado traducido: apunta al ancla del encabezado en español.
