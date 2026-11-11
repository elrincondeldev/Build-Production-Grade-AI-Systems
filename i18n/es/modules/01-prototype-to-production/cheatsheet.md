# Hoja de referencia del módulo 1: Del prototipo a producción

[Inicio del curso](../../README.md) › [Módulo 1](README.md) › Hoja de referencia

## Del prototipo a producción (1.1)
- El modelo es ~5–10 % del sistema. El resto: datos, empaquetado, serving, monitorización, seguridad, operaciones.
- **El bucle del ciclo de vida:** datos → features/contexto → entrenar/adaptar → evaluar → empaquetar → servir → monitorizar → vuelta a los datos.
- **Causas del training/serving skew:** dos caminos de código · fuga de datos (información que no está disponible en el momento de predecir) · distinto origen o frescura de los datos · distintas versiones de bibliotecas.
- **Soluciones:** una única función de features compartida · un contrato de features que se comprueba al cargar · una lista de columnas prohibidas por fuga + un test · registrar las features servidas · feature store · particiones temporales.
- **Traspaso = artefactos + metadatos**, no un pickle. Pasa la «prueba del autobús».

## Arquitectura (1.2)
| Modo | Cuándo | Kestrel |
|---|---|---|
| Batch | Nadie espera; vale con datos no tan frescos | Volver a puntuar las cuentas cada noche, indexar documentos |
| Online | Alguien espera; datos del momento de la request | `POST /v1/score` |
| Streaming | Fresco en segundos; nada se bloquea | Consumidores de `transaction.scored` |
- Primero, un monolito modular; divide por ritmo de publicaciones, escalado, hardware, aislamiento o equipo responsable.
- Los consumidores de eventos tienen que ser **idempotentes** (entrega al menos una vez).
- Mantén los servicios **sin estado**; el estado va en almacenes compartidos.
- Las piezas: **API gateway · feature store · base de datos vectorial · registro de modelos · cola/stream · almacenamiento de objetos · seguimiento de experimentos · observabilidad · registro de prompts**.
- **Escribe primero un presupuesto de latencia.** Dominan las llamadas por red, no el modelo.

## Fiabilidad (1.3)
- n dependencias con disponibilidad p cada una → disponibilidad pⁿ (5 × 99,9 % ≈ 99,5 %). **Lo lento es peor que lo caído.**
- **Timeouts en cada llamada** (de conexión, corto; de lectura, ≈ 2–3× el p99 de la dependencia) + un **deadline** para toda la operación.
- Se reintenta: timeouts, errores de conexión, 429, 5xx. **Nunca** los 4xx. Si no es idempotente → clave de idempotencia.
- `sleep = uniform(0, min(cap, base × 2^(n−1)))`: backoff exponencial + **full jitter**.
- Reintenta en **una sola capa**; limita los intentos (2–3); **presupuesto de reintentos** (≈ 10 % de carga extra); circuit breaker para las dependencias caídas del todo.
- Colas: suavizan los picos, desacoplan, dan contrapresión (backpressure) y una DLQ para los mensajes envenenados.
- **Escalera de degradación** acordada con negocio; marca siempre `degraded`. Fail open o fail closed lo decide negocio.
- REST por defecto; **gRPC** para llamadas internas de mucho throughput que hayas medido y para contratos estrictos.
- Haz **streaming** de la salida del LLM con SSE; para cuando el cliente se desconecte; ojo con el buffering de los proxies; mide el TTFT por separado.

## Servicios (1.4)
```
api/      HTTP ↔ domain (schemas, status codes, middleware)
domain/   rules in pure Python; defines Protocols (ports)
adapters/ files, HTTP, LLMs; implement the ports
main.py   create_app(): composition root + lifespan (load once)
```
- La configuración, en variables de entorno (`KESTREL_*`), tipada y validada al arrancar; una sola imagen para todos los entornos.
- Secretos: ni en el código, ni en Git, ni en las imágenes, ni en los logs. `SecretStr`. Gestor de secretos en producción. Rota lo que se filtre.
- `async` para el trabajo limitado por I/O; `asyncio.gather` para las llamadas independientes; **nunca bloquees el bucle** (clientes síncronos, `time.sleep`, CPU pesada → pool de hilos o de procesos); acota la concurrencia.
- Logs JSON con nombres de `event` estables; ID de request sacado de la cabecera (validada) o generado, asociado a los logs, reenviado hacia abajo y devuelto al cliente.
| Sonda | Si falla → | Comprueba |
|---|---|---|
| Liveness `/health` | reinicio | que el proceso responde; **nunca** las dependencias |
| Readiness `/ready` | sin tráfico | modelo cargado + verificado |
| Startup | retrasa la liveness | margen para arranques lentos |

## Artefactos y contenedores (1.5)
- pickle/joblib **pueden ejecutar código**: solo artefactos propios, verifica el sha256 **antes** de cargar, fija las versiones; prefiere ONNX, safetensors o formatos nativos.
- Artefacto = **inmutable, con una versión única, metadatos que lo describen y un hash verificable**. Puntero `LATEST` atómico (escribir un temporal + renombrar). En producción, fija versiones explícitas.
- El sha256 demuestra la **integridad**, no la autoría (→ firmas) ni la calidad (→ evals).
- Dockerfile: base slim fijada · lock file · **dependencias antes que el código** · multietapa · **sin root** · `.dockerignore` · sin secretos en las capas · CMD en forma exec · HEALTHCHECK.
- Los tags son mutables; los **digests**, no. Nunca despliegues `:latest`.
- K8s: **Deployment** (réplicas, actualización gradual) · **Service** (nombre estable → pods listos) · **ConfigMap/Secret** · **sondas** · **requests/limits** · **securityContext**.

## Comandos que has usado
```bash
uv run python scripts/train.py                        # versioned artifact
shasum -a 256 artifacts/fraud-model/*/model.joblib    # verify / compare
uv run pytest                                         # 32 tests
uv run uvicorn kestrel_fraud.main:create_app --factory --port 8001
uv run python scripts/fake_feature_store.py --fail-rate 0.4
curl -N localhost:8001/v1/explain/<transaction_id>    # SSE stream
docker build -t kestrel/fraud-service:0.1.0 .
docker run --rm -p 8001:8001 kestrel/fraud-service:0.1.0
```

⬅️ [Presentación del módulo 1](README.md) · 📝 [Cuestionario](quiz.md)
