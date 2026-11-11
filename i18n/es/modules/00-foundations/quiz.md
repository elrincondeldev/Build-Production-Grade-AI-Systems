# Cuestionario del módulo 0

> ⏱ ~20 min · Responde cada pregunta **antes** de abrir la respuesta. Suma 1 punto por cada pregunta que hayas acertado en lo esencial.
> **10+ / 12:** empieza el Módulo 1. **7–9:** relee las lecciones enlazadas en las respuestas que fallaste. **Menos de 7:** repite los pasos del lab de esos temas y vuelve a hacer el cuestionario en un par de días (el tiempo entre medias te ayuda a recordar). <!-- pass: 10 -->

[Inicio del curso](../../README.md) › [Módulo 0](README.md) › Cuestionario

---

**1.** El `pyproject.toml` de una persona de tu equipo dice `scikit-learn>=1.5` y no hay lock file. La CI pasó el mes pasado y hoy falla sin ningún cambio en el código. ¿Cuál es la causa más probable y cómo se arregla? <!-- id: q-0-1 -->

<details><summary>Respuesta</summary>

Hoy se resolvió una versión más nueva de una dependencia (directa o transitiva) que cambió el comportamiento. Solución: haz commit de un **lock file** (`uv.lock`) para que cada instalación obtenga versiones exactas y con hash; actualiza a propósito con `uv lock --upgrade` en un cambio propio y revisado. → [Lección 0.2](02-python-for-production.md)

</details>

**2.** ¿Cuáles de estos deberían validarse con Pydantic y cuáles pueden ser dataclasses normales? (a) el cuerpo JSON de `POST /score`, (b) un objeto `Metrics` que devuelve tu propia función de evaluación, (c) las variables de entorno, (d) el JSON que devuelve un LLM cuando le pides salida estructurada. <!-- id: q-0-2 -->

<details><summary>Respuesta</summary>

**Pydantic:** (a), (c) y (d), porque todos cruzan una frontera de confianza (clientes, el entorno, un modelo que puede devolver cualquier cosa). **Dataclass:** (b), datos internos que ha creado tu propio código. Regla: valida en los bordes, confía dentro. → [Lección 0.2](02-python-for-production.md)

</details>

**3.** Un endpoint `async def` llama a `time.sleep(2)` para «esperar a un lock». Con carga, la latencia de *todos* los endpoints se dispara. ¿Por qué? <!-- id: q-0-3 -->

<details><summary>Respuesta</summary>

`time.sleep` **bloquea el bucle de eventos**: mientras duerme, ninguna otra request de ese worker puede avanzar. Usa `await asyncio.sleep(...)` (o primitivas async) y mueve el trabajo bloqueante inevitable a un pool de hilos o de procesos. → [Lección 0.2](02-python-for-production.md)

</details>

**4.** Relaciona cada código de estado con la acción correcta: `422`, `429`, `503`, `403`. <!-- id: q-0-4 -->

<details><summary>Respuesta</summary>

- **422**: el cliente corrige el cuerpo de la request (falló la validación). Sin reintento.
- **429**: se ha superado el límite de peticiones (rate limit), así que espera (respeta `Retry-After`) y reintenta con backoff; si se mantiene, revisa las cuotas.
- **503**: el servicio está sobrecargado o no disponible, así que reintenta con backoff; el equipo responsable del servicio investiga.
- **403**: la llamada está autenticada pero no tiene permiso. Sin reintento; hace falta otro permiso.

→ [Lección 0.3](03-http-and-apis.md)

</details>

**5.** ¿Por qué es peligroso reintentar automáticamente `POST /payments` tras un timeout y cuál es la solución estándar? <!-- id: q-0-5 -->

<details><summary>Respuesta</summary>

Puede que la primera request haya **tenido éxito** y solo se haya perdido la response, así que un reintento puede cobrar dos veces. Solución: una **clave de idempotencia** que envía el cliente y que el servidor deduplica, devolviendo el resultado guardado en las repeticiones. → [Lección 0.3](03-http-and-apis.md)

</details>

**6.** El conjunto de test de Kestrel tiene 10 000 transacciones con 141 fraudes. Un modelo marca 30 transacciones, 20 de las cuales son fraude. Calcula la precision, el recall y la accuracy. <!-- id: q-0-6 -->

<details><summary>Respuesta</summary>

TP = 20, FP = 10, FN = 141 − 20 = 121, TN = 10 000 − 141 − 10 = 9849.
**Precision** = 20 / 30 = **66,7 %**. **Recall** = 20 / 141 = **14,2 %**. **Accuracy** = (20 + 9849) / 10 000 = **98,69 %**, apenas por encima del 98,59 % de «nunca es fraude». → [Lección 0.4](04-ml-in-one-hour.md)

</details>

**7.** Omar dice que «no detectar un fraude nos cuesta mucho más que una falsa alarma». ¿El umbral debería subir o bajar desde 0,5? ¿Qué pasará con la precision y el recall? <!-- id: q-0-7 -->

<details><summary>Respuesta</summary>

**Bajar.** Se marcan más transacciones, así que **el recall sube** y **la precision suele bajar** (más falsas alarmas). El umbral exacto debería salir del coste de cada tipo de error (Módulo 4). → [Lección 0.4](04-ml-in-one-hour.md)

</details>

**8.** Un modelo obtiene un 100 % de recall con los datos de entrenamiento y un 7 % con los de test. Di cuál es el problema y una solución que *no* implique recoger más datos. <!-- id: q-0-8 -->

<details><summary>Respuesta</summary>

**Sobreajuste (overfitting).** Soluciones: reducir la complejidad del modelo (limitar la profundidad del árbol, exigir un mínimo de muestras por hoja, regularización), usar ensembles con parada temprana (early stopping), elegir los hiperparámetros con un conjunto de validación. → [Lección 0.4](04-ml-in-one-hour.md)

</details>

**9.** Para cada feature candidata de un modelo de fraude en tiempo real, di *usar* o *fuga*: (a) `txn_count_24h` calculada a partir de las transacciones *anteriores* a esta, (b) `chargeback_filed`, (c) `analyst_review_outcome`, (d) `device_is_new`. <!-- id: q-0-9 -->

<details><summary>Respuesta</summary>

(a) **Usar**, porque se conoce en el momento de puntuar *si* se calcula solo con el pasado. (b) **Fuga**, el contracargo se presenta a posteriori. (c) **Fuga**, es prácticamente la label. (d) **Usar**, se conoce cuando llega la transacción. La prueba: *¿conocería este valor en el momento en que se necesita la predicción?* → [Lección 0.4](04-ml-in-one-hour.md)

</details>

**10.** Verdadero o falso, y por qué: «Poner la temperatura a 0 evita las alucinaciones». <!-- id: q-0-10 -->

<details><summary>Respuesta</summary>

**Falso.** Con temperatura 0 se elige el token más probable en cada paso, lo que reduce la *aleatoriedad*, no la *falsedad*. Si el modelo no conoce el dato, la continuación más probable puede seguir siendo errónea, y lo será siempre de la misma forma. Lo que aborda la corrección es anclar la respuesta en fuentes (grounding con RAG), las citas y las evaluaciones. → [Lección 0.5](05-llms-in-one-hour.md)

</details>

**11.** Los embeddings por hash sitúan «How do partners get support?» en primer lugar para la consulta «Can I get my money back for a fee?». Explica por qué y di qué tipo de recuperación combina los puntos fuertes de ambos enfoques. <!-- id: q-0-11 -->

<details><summary>Respuesta</summary>

Los embeddings por hash capturan **palabras compartidas** (aquí, «get») en lugar de significado, además de colisiones de hash aleatorias. Los embeddings semánticos capturan paráfrasis, pero pueden difuminar identificadores exactos. La **recuperación híbrida** combina la búsqueda léxica (p. ej., BM25) y la semántica (vectores densos), normalmente seguida de reranking (Lección 2.5). → [Lección 0.5](05-llms-in-one-hour.md)

</details>

**12.** Una respuesta de RAG usa 2000 tokens de entrada y 300 tokens de salida. Con precios ilustrativos de 2,50 USD por cada millón de tokens de entrada y 10,00 USD por cada millón de tokens de salida, ¿cuánto cuesta una llamada y cuánto cuesta un millón de llamadas? Di dos formas de reducir ese coste. <!-- id: q-0-12 -->

<details><summary>Respuesta</summary>

Entrada: 2000 / 1 000 000 × 2,50 USD = 0,005 USD. Salida: 300 / 1 000 000 × 10,00 USD = 0,003 USD. **0,008 USD por llamada, unos 8000 USD por cada millón de llamadas.** Redúcelo recuperando menos fragmentos y más ajustados, acortando los prompts, enviando las preguntas fáciles a un modelo más pequeño, cacheando las preguntas repetidas o limitando la longitud de la respuesta. → [Lección 0.5](05-llms-in-one-hour.md)

</details>

---

### 🔁 Repaso espaciado

Todavía no hay módulos anteriores. A partir del Módulo 1, cada cuestionario termina con preguntas de módulos anteriores. **Pon un recordatorio en tu calendario para repetir este cuestionario dentro de una semana**: recuperar las respuestas tras un tiempo es una de las formas más eficaces de fijarlas.

---
⬅️ [Lab 0](lab/README.md) · ➡️ [Hoja de referencia](cheatsheet.md) · ⏭️ [Módulo 1](../../../../modules/01-prototype-to-production/README.md)
