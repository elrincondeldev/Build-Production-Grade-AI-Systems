# Cuestionario del módulo 1: Del prototipo a producción

[Inicio del curso](../../README.md) › [Módulo 1](README.md) › Cuestionario

> 14 preguntas · ~25 min · Responde cada una **antes** de abrir la solución. Suma 1 punto por pregunta; apunta a **11 o más (80 %)**.
> Las preguntas 12–14 son de **repaso espaciado** del Módulo 0: están aquí a propósito, porque recuperar lo que aprendiste hace tiempo es lo que hace que se quede.

---

**1.** *Detective de fugas.* El ROC-AUC de un modelo de abandono (churn) salta de 0,72 a 0,94 después de añadir `days_since_last_support_ticket_closed`. Los tickets de soporte a menudo se cierran *como parte del* proceso de baja. ¿Qué sospechas y qué pregunta lo resuelve? <!-- id: q-1-1 -->

<details><summary>Respuesta</summary>

**Fuga de la label.** La feature la causa en parte el propio resultado (darse de baja cierra los tickets). La pregunta que lo resuelve: *«En el momento en que hacemos esta predicción en producción, ¿existe este valor y significa lo mismo?»*. Si solo se conoce durante el abandono o después, no se puede usar. (Lección 1.1)

</details>

**2.** *Skew en estado salvaje.* El entrenamiento calcula `avg_amount_30d` a partir de una tabla nocturna completa del data warehouse. El serving lo calcula a partir de una caché de Redis que, para los clientes nuevos, solo guarda los últimos 7 días. ¿Qué tipo de training/serving skew es este? Di dos soluciones. <!-- id: q-1-2 -->

<details><summary>Respuesta</summary>

**Distintos orígenes o frescura de los datos** entre offline y online. Soluciones: calcular la feature una sola vez en un feature store que sirva tanto los valores offline (correctos en el tiempo, point-in-time) como los online; registrar los valores de las features servidas y entrenar con ellos; añadir monitorización que compare las distribuciones de las features online y offline. (Lecciones 1.1 y 1.2)

</details>

**3.** *Modo de inferencia.* Elige batch, online o streaming para cada caso, con una razón de una línea: (a) volver a puntuar los 2 millones de cuentas para la revisión trimestral de riesgos; (b) decidir si se aprueba un pago con tarjeta; (c) marcar patrones de inicio de sesión sospechosos en menos de 30 segundos para el dashboard del equipo de seguridad. <!-- id: q-1-3 -->

<details><summary>Respuesta</summary>

(a) **Batch**: nadie espera; es lo más barato a gran volumen. (b) **Online**: el pago está bloqueado esperando una decisión que usa datos del momento de la request. (c) **Streaming**: fresco en segundos, pero no hay ninguna request bloqueada esperando. (Lección 1.2)

</details>

**4.** *Presupuesto de latencia.* El equipo de pagos le da al fraud-service 100 ms en el p99. La red + el gateway se llevan 15 ms, el p99 del feature store es de 35 ms, el modelo 4 ms y el logging 1 ms. ¿Te puedes permitir un reintento de la llamada al feature store? Muestra las cuentas. <!-- id: q-1-4 -->

<details><summary>Respuesta</summary>

Camino base: 15 + 35 + 4 + 1 = **55 ms**, quedan 45 ms. Un reintento cuesta hasta otros 35 ms más el backoff (pongamos 0–10 ms con jitter): ~45 ms en el peor caso. **Cabe justo, sin margen.** En la práctica: fija un timeout por intento más ajustado (p. ej., 25 ms) para que timeout + backoff + reintento queden bastante por debajo de 45 ms, y aplica un deadline global. (Lecciones 1.2 y 1.3)

</details>

**5.** *Qué reintentar.* Para cada caso, ¿reintentar o no?: (a) `GET /features` → timeout; (b) `GET /features` → 404; (c) `POST /refunds` → conexión reiniciada, sin clave de idempotencia; (d) `GET /features` → 429 con `Retry-After: 1`. <!-- id: q-1-5 -->

<details><summary>Respuesta</summary>

(a) **Sí** (idempotente, transitorio). (b) **No** (la request está mal o el recurso no existe). (c) **No**: puede que el reembolso ya se haya aplicado; primero añade una clave de idempotencia. (d) **Sí, después de al menos 1 s** (si tu deadline lo permite). (Lección 1.3)

</details>

**6.** *Amplificación de reintentos.* Cuatro servicios en cadena hacen hasta 3 intentos cada uno. El último está caído. ¿Cuántas requests le llegan por una sola acción de un usuario y cuáles son dos defensas? <!-- id: q-1-6 -->

<details><summary>Respuesta</summary>

Hay 3 capas que reintentan por encima de él (si la llamada de cara al usuario también reintenta, son 4): 3³ = **27** (o 3⁴ = 81). Defensas: reintentar en una sola capa; presupuestos de reintentos; deadlines; circuit breakers; limitar los intentos a 2–3. (Lección 1.3)

</details>

**7.** *Jitter.* Explica en dos frases por qué `sleep = base × 2^n` por sí solo es peligroso cuando miles de clientes fallan en el mismo momento, y qué cambia el full jitter. <!-- id: q-1-7 -->

<details><summary>Respuesta</summary>

Todos los clientes calculan los mismos retrasos, así que sus reintentos llegan en oleadas sincronizadas (una estampida o thundering herd) que pueden tumbar a un servicio que se está recuperando. El full jitter elige un retraso aleatorio en `[0, cap]`, lo que reparte los reintentos de manera uniforme por la ventana. (Lección 1.3)

</details>

**8.** *¿Fail open o fail closed?* El fraud-service está completamente inaccesible. ¿Quién decide si los pagos se aprueban o se rechazan y de qué debería depender la decisión? <!-- id: q-1-8 -->

<details><summary>Respuesta</summary>

**Negocio** (Risk/Omar), acordado de antemano e implementado en quien llama. Depende del coste relativo de los errores: bloquear a clientes legítimos frente a dejar pasar el fraude, a menudo dividido por importe o por nivel de riesgo (p. ej., aprobar por debajo de 50 € y revisar por encima). Ingeniería implementa y prueba la política. (Lección 1.3)

</details>

**9.** *Capas.* ¿En qué capa (API, dominio, adaptadores) va cada cosa?: (a) convertir `hour: 25` en una response 422; (b) la regla «rechazar si la puntuación ≥ 0,8»; (c) el cliente httpx con reintentos para el feature store; (d) `build_feature_vector`. <!-- id: q-1-9 -->

<details><summary>Respuesta</summary>

(a) **API** (validación del esquema). (b) **Dominio** (`DecisionPolicy`). (c) **Adaptadores** (`HttpFeatureStore`). (d) **Dominio** (`features.py`, compartido por el entrenamiento y el serving). (Lección 1.4)

</details>

**10.** *Bloquear el bucle.* Un endpoint `async def` hace `df = pd.read_csv("big.csv")` (3 s de CPU y disco) en cada request. Con carga, `/health` agota su timeout y Kubernetes reinicia el pod. Explica la cadena de sucesos y da dos soluciones. <!-- id: q-1-10 -->

<details><summary>Respuesta</summary>

La llamada bloqueante retiene durante 3 s el único hilo del bucle de eventos, así que no se ejecuta ninguna otra corrutina, tampoco `/health`. Las sondas de liveness agotan su timeout → Kubernetes mata el pod → la capacidad baja todavía más. Soluciones: hacer el trabajo pesado una sola vez al arrancar (lifespan) o por lotes; ejecutarlo en un pool de hilos o de procesos (`run_in_threadpool`, `asyncio.to_thread`); declarar el endpoint con `def` normal para que FastAPI use un pool de hilos. (Lección 1.4)

</details>

**11.** *Artefactos y contenedores.* (a) ¿Qué demuestra un sha256 que coincide y qué no demuestra? (b) ¿Por qué el Dockerfile del Lab 1 copia `pyproject.toml` y `uv.lock` antes que `src/`? <!-- id: q-1-11 -->

<details><summary>Respuesta</summary>

(a) Demuestra que el archivo es, byte a byte, el que registran los metadatos (que no está corrupto ni se ha sustituido *sin* actualizar los metadatos). **No** demuestra quién lo produjo (para eso hace falta una firma) ni que el modelo sea bueno (para eso hace falta una evaluación). (b) Por la caché de capas: las dependencias cambian poco, así que su capa de instalación sigue en caché y los cambios que solo tocan el código se reconstruyen en segundos. (Lección 1.5)

</details>

---

### 🔁 Repaso espaciado (Módulo 0)

**12.** 🔁 *(Módulo 0)* *Códigos de estado HTTP.* ¿Qué diferencia hay entre un código de estado 4xx y uno 5xx, y qué familia suele merecer la pena reintentar? <!-- id: q-1-12 -->

<details><summary>Respuesta</summary>

**4xx**: la request del cliente está mal (entrada incorrecta, sin autorización, no encontrado). **5xx**: el servidor no ha podido atender una request válida. Los 5xx (más el 429, que técnicamente es un 4xx pero significa «ve más despacio») suelen merecer un reintento; el resto de los 4xx, no. ([Lección 0.3](../00-foundations/03-http-and-apis.md))

</details>

**13.** 🔁 *(Módulo 0)* *La accuracy con datos desequilibrados.* ¿Por qué un 99 % de accuracy no impresiona en la detección de fraude con una tasa de fraude del 1,4 %? <!-- id: q-1-13 -->

<details><summary>Respuesta</summary>

Un modelo trivial que siempre predice «no es fraude» saca un 98,6 % de accuracy sin detectar ni un solo fraude. La accuracy la domina la clase mayoritaria; necesitas precision, recall y PR-AUC (Módulo 4). ([Lección 0.4](../00-foundations/04-ml-in-one-hour.md))

</details>

**14.** 🔁 *(Módulo 0)* *Tokens y latencia.* ¿Por qué el tiempo total de respuesta de un LLM crece con la longitud de la respuesta, y cómo cambia el streaming la experiencia *del usuario* sin cambiar el tiempo total? <!-- id: q-1-14 -->

<details><summary>Respuesta</summary>

Los LLMs generan la salida **de token en token**, así que más tokens de salida significan más pasos de generación uno detrás de otro. El streaming envía cada token en cuanto se genera, así que el usuario ve texto tras el tiempo hasta el primer token en lugar de esperar a la respuesta completa. ([Lección 0.5](../00-foundations/05-llms-in-one-hour.md))

</details>

---

**Puntuación:** ___ / 14 · ¿Menos de 11? Vuelve a las lecciones que se mencionan en las respuestas que fallaste y repite el cuestionario dentro de dos días (espaciar funciona). <!-- pass: 11 -->

⬅️ [Presentación del módulo 1](README.md) · 📄 [Hoja de referencia](cheatsheet.md)

🚀 **¿Terminado?** Marca el Módulo 1 en tu registro de progreso y sigue con el [Módulo 2: Data and Model Pipelines](../../../../modules/02-data-and-model-pipelines/README.md).
