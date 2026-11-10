# Hoja de referencia del módulo 0: Fundamentos

[Inicio del curso](../../README.md) › [Módulo 0](README.md) › Hoja de referencia

## 🧰 Herramientas

| Herramienta | Resuelve | Comandos clave |
|---|---|---|
| **uv** | Python y paquetes exactos | `uv sync` · `uv run <cmd>` · `uv add <pkg>` · `uv lock --upgrade` |
| **Git** | Historial, revisión, rollback | `git switch -c <branch>` · `git add -A && git commit -m "..."` · `git pull upstream main` |
| **Docker** | Distribuir todo el entorno de ejecución | `docker build -t name .` · `docker run --rm -p 8000:8000 name` |
| **Ollama** | LLMs locales gratis | `ollama pull qwen2.5:1.5b-instruct` · `ollama run <model> "prompt"` · API en `:11434` |

Haz commit de `pyproject.toml` + `uv.lock`. Nunca hagas commit de `.venv/`, `.env`, datos ni artefactos de modelos.

## 🐍 Python para producción

- **Valida en los bordes** (Pydantic: cuerpos HTTP, configuración, archivos, salida del LLM); **confía dentro** (dataclasses).
- **Configuración desde el entorno**: `KESTREL_*` con `pydantic-settings`; secretos como `SecretStr`; falla rápido ante una configuración incorrecta.
- **Testeable = inyectable**: pasa los clientes y los transports como parámetros; sustituye la red por un fake (`httpx.MockTransport`), no la lógica.
- **Usa logging, no print.** Niveles, marcas de tiempo, sin secretos ni PII.
- **async** ayuda con el trabajo **limitado por I/O** (llamadas al LLM, a la base de datos, HTTP). No con el limitado por CPU. **Nunca bloquees el bucle de eventos** (`time.sleep`, `requests`).

## 🌐 HTTP

```
METHOD /path?query  + headers + body   →   STATUS + headers + body
```

| Código | Significado | ¿Reintentar? |
|---|---|---|
| 2xx | OK | — |
| 400 / 422 | Request incorrecta / validación fallida | ❌ corrige la request |
| 401 / 403 | Sin autenticar / sin permiso | ❌ |
| 404 | No encontrado | ❌ |
| **429** | Límite de peticiones superado (rate limit) | ✅ tras `Retry-After`, con backoff |
| 500 | Bug en el servidor | ⚠️ con cautela |
| **502 / 503 / 504** | Falló el upstream / sobrecarga / se agotó el tiempo | ✅ con backoff |

- **Idempotente** = se puede repetir sin riesgo. `POST` no lo es, así que usa una `Idempotency-Key`.
- Siempre: **timeouts**, `raise_for_status()`, **IDs de request**, **límites de tamaño** en la entrada.
- Nunca devuelvas errores con el código 200.

## 📈 Lo básico de ML

- Features → modelo → predicción. El entrenamiento es offline; la inferencia, en cada request. El modelo es un **artefacto**.
- **Partición**: entrenamiento (ajustar) / validación (afinar) / test (comprobación final). **Estratifica** las clases poco frecuentes. Usa particiones temporales para datos ordenados en el tiempo.
- **Sobreajuste (overfitting)** = entrenamiento ≫ test. **Subajuste (underfitting)** = malo en ambos.
- **La accuracy miente con eventos raros.** Compárala siempre con un baseline trivial.

|  | Pred. fraude | Pred. no fraude |
|---|---|---|
| **Fraude** | TP | FN (no detectado) |
| **No fraude** | FP (falsa alarma) | TN |

- **Precision** = TP / (TP + FP): «de lo que marcamos, ¿cuánto era fraude?»
- **Recall** = TP / (TP + FN): «de todo el fraude, ¿cuánto detectamos?»
- **Umbral** ↓ → recall ↑, precision ↓. Elegirlo es una decisión **de negocio**.
- **Fuga de datos (leakage)**: si no lo sabrías *en el momento de predecir*, no es una feature (`chargeback_filed`).
- Pon el preprocesamiento **dentro del pipeline** para evitar el desajuste entre entrenamiento y serving (training/serving skew).

## 🤖 Lo básico de los LLMs

- **Token** ≈ 4 caracteres de texto en inglés ≈ 0,75 palabras. El precio, los límites, la latencia y el contexto se miden en tokens.
- LLM = **predictor del siguiente token**. No es una base de datos, tiene una fecha de corte de entrenamiento y optimiza lo *plausible*, no lo *verdadero* → **alucinación**.
- **Temperatura** baja = respuestas centradas, alta = variadas. **Top-p** = muestrea entre los tokens más probables cuya probabilidad acumulada llega a p. Ninguna de las dos garantiza la verdad.
- **Ventana de contexto** = límite de entrada + salida. Los contextos más grandes cuestan más, son más lentos y pueden enterrar información.
- **Embeddings** = significado como vectores; **similitud coseno** = cercanía. Léxica (palabras) frente a semántica (significado) → combina ambas: **híbrida**.
- **RAG** = recupera tus pasajes → ponlos en el prompt → responde con citas. Reduce las alucinaciones; no las elimina.
- **Coste por llamada** = entrada/1M × precio_entrada + salida/1M × precio_salida. En RAG, el **contexto suele dominar**.
- **TTFT** (tiempo hasta el primer token) frente a **tiempo total**; el streaming mejora la latencia percibida.
- Programa contra **una única interfaz de LLM**: `fake` (tests) · `ollama` (local) · `openai` (cualquier API compatible con OpenAI).

## 🔢 Números del Lab 0 que vale la pena recordar

| Dato | Valor |
|---|---|
| Tasa base de fraude | 1,41 % (141 fraudes en un conjunto de test de 10 000 filas) |
| Accuracy de «nunca es fraude» | 98,59 %, recall 0 % |
| Regresión logística con umbral 0,5 | 1 de 141 fraudes detectados |
| Regresión logística con umbral 0,1 | 23 detectados, 110 falsas alarmas |
| Árbol de decisión sin límite | 100 % de recall en entrenamiento frente a 7 % en test |
| «refund a fee» frente a «get my money back…» | hash 0,000 · MiniLM 0,719 |

---
⬅️ [Cuestionario](quiz.md) · ➡️ [Módulo 1: From Prototype to Production](../../../../modules/01-prototype-to-production/README.md)
