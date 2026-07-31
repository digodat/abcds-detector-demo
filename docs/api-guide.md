# ABCD Detector API — Guía para el equipo de frontend

## Contenido

1. [Resumen](#resumen)
2. [URL base](#url-base)
3. [Endpoints](#endpoints)
4. [POST /evaluate — Referencia completa](#post-evaluate)
5. [Respuesta](#respuesta)
6. [Códigos de error](#códigos-de-error)
7. [Catálogo de features](#catálogo-de-features)
8. [Ejemplos de uso](#ejemplos-de-uso)
9. [POST /evaluate/stream — Streaming SSE](#post-evaluatestream)
10. [Consideraciones de rendimiento](#consideraciones-de-rendimiento)
11. [Documentación interactiva](#documentación-interactiva)

---

## Resumen

El ABCD Detector evalúa piezas de video publicitario contra el framework ABCD de YouTube usando IA de Google (Gemini + Video Intelligence API). El servicio corre en **Cloud Run** y expone una API HTTP/JSON.

El servicio ofrece dos modos de uso:

- **`POST /evaluate`** — envía los videos y espera hasta recibir todos los resultados en una sola respuesta JSON.
- **`POST /evaluate/stream`** — mismo análisis, pero transmite el progreso en tiempo real (Server-Sent Events). Recomendado cuando se necesita feedback visual durante el procesamiento (pantalla de carga multi-step).

Ambos endpoints devuelven la misma estructura de resultados: una evaluación por video con el resultado de cada feature analizada — si fue detectada, el puntaje de confianza, la evidencia encontrada, las fortalezas y debilidades.

---

## URL base

```
https://<SERVICE_URL>
```

La URL del servicio la provee el equipo de backend una vez deployado en Cloud Run. Está disponible en GCP Console → Cloud Run → abcds-detector-demo.

---

## Endpoints

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check. Retorna `{"status": "ok"}` |
| `POST` | `/evaluate` | Evalúa uno o varios videos — retorna resultados al finalizar |
| `POST` | `/evaluate/stream` | Igual que `/evaluate` pero transmite el progreso en tiempo real (SSE) |

---

## POST /evaluate — Referencia completa

### Headers

```
Content-Type: application/json
```

### Body

Todos los campos marcados como **Requerido** deben estar presentes. El resto tiene valor por defecto.

---

#### Videos y bucket

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `video_uris` | `string[]` | Sí | — | Lista de URIs de los videos. Formato GCS: `gs://bucket/video.mp4`. Formato YouTube: `https://www.youtube.com/watch?v=...` |
| `bucket_name` | `string` | Sí | — | Nombre del bucket de GCS (sin `gs://`). Ej: `"mi-bucket"` |

---

#### Configuración GCP

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project_id` | `string` | No | Inferido de ADC | ID del proyecto GCP. Si el servicio corre con un service account configurado, se infiere automáticamente |
| `project_zone` | `string` | No | `"us-central1"` | Región GCP |
| `knowledge_graph_api_key` | `string` | No | `""` | API key para Knowledge Graph. Requerida solo si `extract_brand_metadata: true` y se quiere enriquecer la metadata de marca |

---

#### Datos de marca

Usados para que el modelo identifique correctamente la marca dentro del video. Son opcionales si `extract_brand_metadata: true` (el modelo la infiere del video), pero **recomendados** para mayor precisión.

Si `extract_brand_metadata` es `false`, los cuatro primeros campos se vuelven **obligatorios**.

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `brand_name` | `string` | `null` | Nombre principal de la marca. Ej: `"Coca-Cola"` |
| `brand_variations` | `string` | `""` | Variaciones del nombre de marca, separadas por coma. Ej: `"Coke, Cola"` |
| `branded_products` | `string` | `""` | Productos de la marca, separados por coma. Ej: `"Coca-Cola Zero, Coca-Cola Light"` |
| `branded_products_categories` | `string` | `""` | Categorías de productos, separadas por coma. Ej: `"bebida, gaseosa"` |
| `branded_call_to_actions` | `string` | `""` | CTAs propios de la marca, separados por coma. Ej: `"Visita nuestro sitio, Descarga la app"` |

---

#### Flags de evaluación

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `extract_brand_metadata` | `boolean` | `true` | Si `true`, el modelo extrae automáticamente metadata de la marca desde el video. Si `false`, se deben proveer los campos de marca manualmente |
| `use_llms` | `boolean` | `true` | Usar Gemini para evaluar features. Recomendado siempre activo |
| `use_annotations` | `boolean` | `false` | Usar Video Intelligence API (anotaciones) para features que lo soportan. Solo aplica a videos GCS. Aumenta la precisión pero también el tiempo y costo |
| `run_long_form_abcd` | `boolean` | `true` | Evaluar las 23 features del framework ABCD para video long-form |
| `run_shorts` | `boolean` | `true` | Evaluar las 20 features del framework para YouTube Shorts |
| `creative_provider_type` | `string` | `"GCS"` | Fuente de los videos. Valores: `"GCS"` (Google Cloud Storage) o `"YOUTUBE"` (URLs de YouTube). Con `"YOUTUBE"` solo se puede usar LLMs (`use_annotations` se ignora) |
| `features_to_evaluate` | `string[]` | `[]` | Lista de IDs de features. **Hoy se acepta y se guarda en la config, pero no filtra el catálogo** — se evalúan todas las features habilitadas por `run_long_form_abcd` / `run_shorts` sin importar este campo. Pendiente de decisión de producto: implementarlo o retirarlo del contrato. Ver [Catálogo de features](#catálogo-de-features) |
| `language` | `string` | `"EN"` | Idioma del output. Valores: `"EN"` (inglés) o `"ES"` (español). Afecta los campos de texto del modelo: `rationale`, `evidence`, `strengths`, `weaknesses`. Un valor inválido retorna HTTP `422` |

---

#### Salida en BigQuery

Opcional. Si se configura, los resultados se almacenan automáticamente en BigQuery además de devolverse en el response.

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `bigquery_dataset` | `string` | `"abcd_detector_ds"` | Nombre del dataset en BigQuery |
| `bigquery_table` | `string` | `""` | Nombre de la tabla. Si está vacío, no se guarda en BQ |

---

#### Parámetros del modelo LLM

En la mayoría de los casos no es necesario modificarlos.

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `llm_name` | `string` | `"gemini-2.5-pro"` | Modelo de Gemini a usar |
| `llm_location` | `string` | `"us-central1"` | Región del modelo |
| `max_output_tokens` | `integer` | `65535` | Máximo de tokens en la respuesta del modelo |
| `temperature` | `float` | `1.0` | Creatividad del modelo. Rango: `0.0–2.0` |
| `top_p` | `float` | `0.95` | Diversidad del muestreo. Rango: `0.0–1.0` |

---

## Respuesta

### Estructura del response

```json
{
  "status": "success",
  "assessments": [
    {
      "brand_name": "string",
      "video_uri": "string",
      "long_form_abcd": [ /* FeatureEvaluation[] */ ],
      "shorts": [ /* FeatureEvaluation[] */ ],
      "error": null
    }
  ]
}
```

- `assessments` contiene **un objeto por cada URI enviada en el request, en el mismo orden**, incluso si algún video falló.
- Si `run_long_form_abcd: false`, el campo `long_form_abcd` llega como array vacío `[]`.
- Si `run_shorts: false`, el campo `shorts` llega como array vacío `[]`.
- Si un video falló, `error` contiene el mensaje de error y `long_form_abcd` / `shorts` llegan como arrays vacíos `[]`. Los demás videos del batch sí incluyen sus resultados normalmente.
- `status` es `"success"` cuando todos los videos se procesaron correctamente, o `"partial"` cuando al menos uno falló.

---

### Objeto FeatureEvaluation

Cada elemento de `long_form_abcd` o `shorts` tiene esta forma:

```json
{
  "feature_id": "a_dynamic_start",
  "feature_name": "Dynamic Start",
  "category": "LONG_FORM_ABCD",
  "sub_category": "ATTRACT",
  "video_segment": "FULL_VIDEO",
  "detected": true,
  "confidence_score": 0.92,
  "rationale": "El primer corte ocurre en el segundo 1.8, cumpliendo el criterio de menos de 3 segundos.",
  "evidence": "Segundo 0–1.8: escena de apertura con plano general. Segundo 1.8: corte a primer plano del producto.",
  "strengths": "Inicio visualmente dinámico que captura la atención de forma inmediata.",
  "weaknesses": ""
}
```

#### Campos de identificación

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `feature_id` | `string` | ID único de la feature. Usar para filtrar y mapear resultados. Ver [Catálogo de features](#catálogo-de-features) |
| `feature_name` | `string` | Nombre legible de la feature en inglés |

#### Clasificación

| Campo | Tipo | Valores posibles | Descripción |
|-------|------|-----------------|-------------|
| `category` | `string` | `LONG_FORM_ABCD` \| `SHORTS` | Indica a qué tipo de análisis pertenece la feature. Las features de `long_form_abcd` siempre tienen `"LONG_FORM_ABCD"` y las de `shorts` siempre tienen `"SHORTS"` |
| `sub_category` | `string` | `ATTRACT` \| `BRAND` \| `CONNECT` \| `DIRECT` \| `NONE` | Letra del framework ABCD a la que pertenece la feature. `ATTRACT` = A, `BRAND` = B, `CONNECT` = C, `DIRECT` = D. `NONE` indica features sin clasificación ABCD (solo en Shorts) |
| `video_segment` | `string` | `FULL_VIDEO` \| `FIRST_5_SECS_VIDEO` | Segmento del video que analiza esta feature. `FULL_VIDEO` = video completo, `FIRST_5_SECS_VIDEO` = primeros 5 segundos |

#### Resultado de la evaluación

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `detected` | `boolean` | `true` si la feature fue detectada en el video |
| `confidence_score` | `float` | Puntaje de confianza del modelo. Rango: `0.0–1.0`. Valores cercanos a `1.0` indican alta certeza |

#### Análisis cualitativo

Estos campos contienen el razonamiento del modelo en texto libre. **Pueden llegar como string vacío `""`** cuando el modelo no encontró evidencia suficiente o la feature no aplica al segmento analizado. El frontend debe manejar este caso.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rationale` | `string` | Explicación del modelo sobre por qué detectó o no detectó la feature |
| `evidence` | `string` | Fragmentos o momentos concretos del video que respaldan la evaluación |
| `strengths` | `string` | Aspectos positivos del video para esta feature |
| `weaknesses` | `string` | Aspectos a mejorar. Si la feature fue detectada con alta confianza, puede ser `""` |

#### Campo de error por video

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `error` | `string \| null` | `null` en evaluaciones exitosas. Si el video falló (error de GCS, timeout de Gemini, URI incompatible con el provider, etc.), contiene el mensaje de error y los arrays `long_form_abcd` y `shorts` llegan vacíos |

> **Nota sobre `brand_name` en el response:** el campo refleja el valor enviado en el request (`brand_name`). Si no se envió `brand_name` (porque se usa `extract_brand_metadata: true` para que el modelo lo infiera), el campo llegará como `""`. El nombre que extrae el modelo se usa internamente para la evaluación pero no se retorna en el response.

---

### Ejemplo de respuesta completa

Request con un video GCS, `run_long_form_abcd: true`, `run_shorts: false`, y `features_to_evaluate: ["a_dynamic_start", "b_brand_visuals"]` (nota: el campo se acepta pero **hoy no filtra**; con `run_long_form_abcd: true` se evalúan todas las features long-form):

```json
{
  "status": "success",
  "assessments": [
    {
      "brand_name": "Mi Marca",
      "video_uri": "gs://mi-bucket/videos/ad_verano.mp4",
      "long_form_abcd": [
        {
          "feature_id": "a_dynamic_start",
          "feature_name": "Dynamic Start",
          "category": "LONG_FORM_ABCD",
          "sub_category": "ATTRACT",
          "video_segment": "FULL_VIDEO",
          "detected": true,
          "confidence_score": 0.92,
          "rationale": "El primer corte ocurre en el segundo 1.8, cumpliendo el criterio de menos de 3 segundos.",
          "evidence": "Segundo 0–1.8: escena de apertura con plano general. Segundo 1.8: corte a primer plano del producto.",
          "strengths": "Inicio visualmente dinámico que captura la atención de forma inmediata.",
          "weaknesses": ""
        },
        {
          "feature_id": "b_brand_visuals",
          "feature_name": "Brand Visuals",
          "category": "LONG_FORM_ABCD",
          "sub_category": "BRAND",
          "video_segment": "FULL_VIDEO",
          "detected": false,
          "confidence_score": 0.21,
          "rationale": "No se detectaron elementos visuales claros de la marca (logo, colores corporativos o packaging) en ningún momento del video.",
          "evidence": "",
          "strengths": "",
          "weaknesses": "La marca no aparece visualmente en el video. Incorporar logo o packaging incrementa el recuerdo de marca."
        }
      ],
      "shorts": [],
      "error": null
    }
  ]
}
```

### Ejemplo de respuesta parcial

Request con dos videos, donde el segundo falla (por ejemplo, el archivo no existe en GCS):

```json
{
  "status": "partial",
  "assessments": [
    {
      "brand_name": "Mi Marca",
      "video_uri": "gs://mi-bucket/videos/ad_verano.mp4",
      "long_form_abcd": [
        {
          "feature_id": "a_dynamic_start",
          "feature_name": "Dynamic Start",
          "category": "LONG_FORM_ABCD",
          "sub_category": "ATTRACT",
          "video_segment": "FULL_VIDEO",
          "detected": true,
          "confidence_score": 0.92,
          "rationale": "El primer corte ocurre en el segundo 1.8, cumpliendo el criterio de menos de 3 segundos.",
          "evidence": "Segundo 0–1.8: escena de apertura con plano general. Segundo 1.8: corte a primer plano del producto.",
          "strengths": "Inicio visualmente dinámico que captura la atención de forma inmediata.",
          "weaknesses": ""
        }
      ],
      "shorts": [],
      "error": null
    },
    {
      "brand_name": "Mi Marca",
      "video_uri": "gs://mi-bucket/videos/ad_navidad.mp4",
      "long_form_abcd": [],
      "shorts": [],
      "error": "404 GET https://storage.googleapis.com/mi-bucket/videos/ad_navidad.mp4: Not Found"
    }
  ]
}
```

- El primer video se procesó correctamente y tiene sus features.
- El segundo falló — `long_form_abcd` y `shorts` son arrays vacíos, y `error` contiene el mensaje.
- El response llega con HTTP `200` y `status: "partial"`.

---

## Códigos de error

| Código | Situación |
|--------|-----------|
| `200` | Evaluación completada. El campo `status` indica si fue `"success"` (todos los videos OK) o `"partial"` (al menos un video falló) |
| `400` | Request inválido. Causas: `project_id` no pudo determinarse, o `extract_brand_metadata: false` sin datos de marca provistos |
| `422` | Falta un campo requerido (`video_uris` o `bucket_name`) o un tipo de dato es incorrecto |
| `500` | Error fatal inesperado antes de comenzar la evaluación. El campo `detail` contiene el mensaje |

> **Errores por video individual:** se retornan con HTTP `200` y el assessment del video afectado incluye `"error": "mensaje"`. El batch continúa procesando los videos restantes.

### Formato del error

```json
{
  "detail": "Descripción del error"
}
```

---

## Catálogo de features

### Long-form ABCD (23 features)

| ID | Nombre | Segmento |
|----|--------|----------|
| `a_dynamic_start` | Dynamic Start | Video completo |
| `a_quick_pacing` | Quick Pacing | Video completo |
| `a_quick_pacing_1st_5_secs` | Quick Pacing (First 5 seconds) | Primeros 5 seg |
| `a_supers` | Supers | Video completo |
| `a_supers_with_audio` | Supers with Audio | Video completo |
| `b_brand_visuals` | Brand Visuals | Video completo |
| `b_brand_visuals_1st_5_secs` | Brand Visuals (First 5 seconds) | Primeros 5 seg |
| `b_brand_mention_speech` | Brand Mention (Speech) | Video completo |
| `b_brand_mention_speech_1st_5_secs` | Brand Mention (Speech) (First 5 seconds) | Primeros 5 seg |
| `b_product_visuals` | Product Visuals | Video completo |
| `b_product_visuals_1st_5_secs` | Product Visuals (First 5 seconds) | Primeros 5 seg |
| `b_product_mention_speech` | Product Mention (Speech) | Video completo |
| `b_product_mention_speech_1st_5_secs` | Product Mention (Speech) (First 5 seconds) | Primeros 5 seg |
| `b_product_mention_text` | Product Mention (Text) | Video completo |
| `b_product_mention_text_1st_5_secs` | Product Mention (Text) (First 5 seconds) | Primeros 5 seg |
| `c_overall_pacing` | Overall Pacing | Video completo |
| `c_presence_of_people` | Presence of People | Video completo |
| `c_presence_of_people_1st_5_secs` | Presence of People (First 5 seconds) | Primeros 5 seg |
| `c_visible_face` | Visible Face (First 5 seconds) | Primeros 5 seg |
| `c_visible_face_close_up` | Visible Face (Close Up) | Video completo |
| `d_audio_speech_early_1st_5_secs` | Audio Early (First 5 seconds) | Primeros 5 seg |
| `d_call_to_action_speech` | Call To Action (Speech) | Video completo |
| `d_call_to_action_text` | Call To Action (Text) | Video completo |

### Shorts (20 features)

| ID | Nombre |
|----|--------|
| `tight_framing_index` | Tight Framing & Visual Dominance |
| `shorts_human_voice` | Human Voice Presence |
| `shorts_direct_to_camera` | Direct to Camera |
| `shorts_has_supers` | Supers & Text-Audio Synchronicity |
| `shorts_product_closeup` | Product Close-Up |
| `shorts_product_extreme_closeup` | Product Extreme Close-Up |
| `shorts_product_context_index` | Product Context & Usage Quality |
| `shorts_casual_language` | Casual Language |
| `shorts_humor_index` | Humor & Comedic Timing |
| `character_driven` | Character-Driven |
| `shorts_audio_cta` | Call to Action (Audio) |
| `special_offer_speech` | Special Offer (Speech) |
| `shorts_production_style_index` | Production Style |
| `shorts_sfv_adaptation_high` | Short Form Video Adaptation |
| `shorts_emoji_usage` | Emoji Usage |
| `shorts_personal_character_talk` | Direct to Camera Character Talk |
| `shorts_native_brand_context` | Brand Secondary Element |
| `shorts_personal_character_type` | Everyday Persona Validation |
| `shorts_product_context` | Secondary Product Context |
| `shorts_video_format` | Vertical Format Designed For Mobile |

---

## Ejemplos de uso

### Evaluación mínima con LLMs (caso más común)

```js
const response = await fetch(`${SERVICE_URL}/evaluate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_uris: ['gs://mi-bucket/videos/ad_verano.mp4'],
    bucket_name: 'mi-bucket',
    brand_name: 'Mi Marca',
    use_llms: true,
    use_annotations: false,
    run_long_form_abcd: true,
    run_shorts: false,
    language: 'ES'
  })
})

const data = await response.json()
// data.assessments[0].long_form_abcd → array de FeatureEvaluation
// data.assessments[0].long_form_abcd[0].rationale → texto en español
```

---

### Evaluación de YouTube Shorts

```js
const response = await fetch(`${SERVICE_URL}/evaluate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_uris: ['https://www.youtube.com/watch?v=VIDEO_ID'],
    bucket_name: 'mi-bucket',
    creative_provider_type: 'YOUTUBE',
    run_long_form_abcd: false,
    run_shorts: true,
    brand_name: 'Mi Marca'
  })
})
```

> **Nota:** Con `creative_provider_type: "YOUTUBE"`, `use_annotations` se ignora automáticamente. Solo se usan LLMs.

---

### Evaluación de features específicas

> **Estado actual:** el campo `features_to_evaluate` se acepta en el request y se guarda en la config, pero **aún no filtra el catálogo**. El ejemplo de abajo documenta el contrato pretendido; hasta que se implemente el filtro (o se retire el campo), el runtime evalúa todas las features habilitadas por `run_long_form_abcd` / `run_shorts`.

Contrato pretendido (aún no aplicado) — evaluar solo un subconjunto de features para reducir tiempo y costo:

```js
const response = await fetch(`${SERVICE_URL}/evaluate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_uris: ['gs://mi-bucket/videos/ad_verano.mp4'],
    bucket_name: 'mi-bucket',
    features_to_evaluate: [
      'a_dynamic_start',
      'b_brand_visuals',
      'd_call_to_action_speech'
    ]
  })
})
```

---

### Evaluación completa con anotaciones y guardado en BigQuery

```js
const response = await fetch(`${SERVICE_URL}/evaluate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_uris: [
      'gs://mi-bucket/videos/ad_verano.mp4',
      'gs://mi-bucket/videos/ad_navidad.mp4'
    ],
    bucket_name: 'mi-bucket',
    brand_name: 'Mi Marca',
    brand_variations: 'Marca, MiMarca',
    branded_products: 'Producto A, Producto B',
    branded_products_categories: 'electrónica, gadgets',
    extract_brand_metadata: false,
    use_llms: true,
    use_annotations: true,
    run_long_form_abcd: true,
    run_shorts: false,
    bigquery_dataset: 'abcd_results',
    bigquery_table: 'evaluaciones_q1'
  })
})
```

---

### Calcular puntaje global desde el response

```js
function calcularPuntaje(features) {
  if (!features.length) return 0
  const detectadas = features.filter(f => f.detected).length
  return Math.round((detectadas / features.length) * 100)
}

const assessment = data.assessments[0]
const puntajeAbcd = calcularPuntaje(assessment.long_form_abcd)
const puntajeShorts = calcularPuntaje(assessment.shorts)

console.log(`ABCD: ${puntajeAbcd}% | Shorts: ${puntajeShorts}%`)
// Resultado: ≥80% Excelente | 65-79% Puede mejorar | <65% Necesita revisión
```

---

## POST /evaluate/stream

Este endpoint acepta el **mismo body** que `POST /evaluate` pero en lugar de esperar a que finalicen todos los videos, transmite el progreso en tiempo real usando **Server-Sent Events (SSE)**. Permite mostrar una pantalla de carga multi-step en el frontend.

### Headers

```
Content-Type: application/json
```

### Body

Idéntico al de `POST /evaluate`. Ver [referencia completa](#post-evaluate).

### Formato de eventos

Cada evento llega como una línea SSE estándar:

```
data: {"type": "...", ...}

```

### Tipos de evento

| `type` | Cuándo se emite |
|--------|----------------|
| `video_start` | Al iniciar el procesamiento de cada video |
| `step` | Antes y después de cada paso dentro de un video |
| `video_done` | Al terminar de procesar un video correctamente |
| `video_error` | Si un video individual falla. El batch continúa con los videos restantes |
| `done` | Al finalizar todos los videos — incluye los resultados completos (con `status: "success"` o `"partial"`) |
| `error` | Si ocurre un error fatal que aborta toda la evaluación |

### Pasos (`step`)

| `step` | Descripción | Solo para proveedor |
|--------|-------------|---------------------|
| `annotations` | Generación de anotaciones (Video Intelligence API) | GCS |
| `trim` | Recorte del segmento de los primeros 5 segundos | GCS |
| `long_form_abcd` | Evaluación de features ABCD full con LLMs | Todos |
| `shorts` | Evaluación de features Shorts con LLMs | Todos |
| `bigquery` | Almacenamiento de resultados en BigQuery | Solo si `bigquery_table` está configurado |

Cada evento `step` incluye `"status": "running"` al comenzar y `"status": "done"` al terminar.

### Esquema de cada evento

**`video_start`:**
```json
{
  "type": "video_start",
  "video_uri": "gs://mi-bucket/videos/ad_verano.mp4",
  "index": 1,
  "total": 2
}
```

**`step` — inicio de paso:**
```json
{
  "type": "step",
  "step": "long_form_abcd",
  "status": "running",
  "video_uri": "gs://mi-bucket/videos/ad_verano.mp4"
}
```

**`step` — fin de paso:**
```json
{
  "type": "step",
  "step": "long_form_abcd",
  "status": "done",
  "video_uri": "gs://mi-bucket/videos/ad_verano.mp4"
}
```

**`video_done`:**
```json
{
  "type": "video_done",
  "video_uri": "gs://mi-bucket/videos/ad_verano.mp4",
  "index": 1,
  "total": 2
}
```

**`video_error` — fallo en un video individual (el batch continúa):**
```json
{
  "type": "video_error",
  "video_uri": "gs://mi-bucket/videos/ad_navidad.mp4",
  "index": 2,
  "total": 2,
  "detail": "404 GET https://storage.googleapis.com/mi-bucket/videos/ad_navidad.mp4: Not Found"
}
```

**`done` — fin del batch, incluye todos los resultados:**
```json
{
  "type": "done",
  "status": "success",
  "assessments": [
    {
      "brand_name": "Mi Marca",
      "video_uri": "gs://mi-bucket/videos/ad_verano.mp4",
      "long_form_abcd": [
        {
          "feature_id": "a_dynamic_start",
          "feature_name": "Dynamic Start",
          "category": "LONG_FORM_ABCD",
          "sub_category": "ATTRACT",
          "video_segment": "FULL_VIDEO",
          "detected": true,
          "confidence_score": 0.92,
          "rationale": "El primer corte ocurre en el segundo 1.8, cumpliendo el criterio de menos de 3 segundos.",
          "evidence": "Segundo 0–1.8: escena de apertura con plano general. Segundo 1.8: corte a primer plano del producto.",
          "strengths": "Inicio visualmente dinámico que captura la atención de forma inmediata.",
          "weaknesses": ""
        }
      ],
      "shorts": [],
      "error": null
    }
  ]
}
```

La estructura de cada objeto en `assessments` es idéntica a la respuesta de `POST /evaluate`. `status` es `"success"` o `"partial"` según si todos los videos se procesaron correctamente. Ver [Respuesta](#respuesta).

**`error` — fallo fatal que aborta toda la evaluación:**
```json
{
  "type": "error",
  "detail": "project_id could not be determined."
}
```

### Secuencia completa de eventos para un batch de 2 videos

```
data: {"type":"video_start","video_uri":"gs://mi-bucket/ad_verano.mp4","index":1,"total":2}

data: {"type":"step","step":"trim","status":"running","video_uri":"gs://mi-bucket/ad_verano.mp4"}

data: {"type":"step","step":"trim","status":"done","video_uri":"gs://mi-bucket/ad_verano.mp4"}

data: {"type":"step","step":"long_form_abcd","status":"running","video_uri":"gs://mi-bucket/ad_verano.mp4"}

data: {"type":"step","step":"long_form_abcd","status":"done","video_uri":"gs://mi-bucket/ad_verano.mp4"}

data: {"type":"video_done","video_uri":"gs://mi-bucket/ad_verano.mp4","index":1,"total":2}

data: {"type":"video_start","video_uri":"gs://mi-bucket/ad_navidad.mp4","index":2,"total":2}

data: {"type":"video_error","video_uri":"gs://mi-bucket/ad_navidad.mp4","index":2,"total":2,"detail":"404 Not Found"}

data: {"type":"done","status":"partial","assessments":[...]}
```

### Ejemplo en JavaScript

```js
async function evaluarConProgreso(requestBody, onEvent) {
  const response = await fetch(`${SERVICE_URL}/evaluate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  })

  // Errores de setup (400, 422) llegan antes de que empiece el stream
  if (!response.ok) {
    const err = await response.json()
    throw new Error(err.detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop()

    for (const chunk of chunks) {
      if (!chunk.startsWith('data: ')) continue
      const event = JSON.parse(chunk.slice(6))
      onEvent(event)
      if (event.type === 'done') return event.assessments
      if (event.type === 'error') throw new Error(event.detail)
    }
  }
}

// Uso:
const assessments = await evaluarConProgreso(
  {
    video_uris: [
      'gs://mi-bucket/videos/ad_verano.mp4',
      'gs://mi-bucket/videos/ad_navidad.mp4',
    ],
    bucket_name: 'mi-bucket',
    brand_name: 'Mi Marca',
    run_long_form_abcd: true,
    run_shorts: false,
    language: 'ES',
  },
  (event) => {
    if (event.type === 'video_start') {
      console.log(`Iniciando video ${event.index}/${event.total}: ${event.video_uri}`)
    } else if (event.type === 'step' && event.status === 'running') {
      console.log(`  → ${event.step}...`)
    } else if (event.type === 'step' && event.status === 'done') {
      console.log(`  ✓ ${event.step}`)
    } else if (event.type === 'video_done') {
      console.log(`Video ${event.index} completado`)
    } else if (event.type === 'video_error') {
      console.warn(`Video ${event.index} falló: ${event.detail}`)
    }
  }
)

// assessments puede incluir objetos con error !== null si algún video falló
const exitosos = assessments.filter(a => a.error === null)
const fallidos = assessments.filter(a => a.error !== null)
```

> **Nota sobre `EventSource`:** La API nativa `EventSource` del browser no soporta `POST` ni body JSON. Usar `fetch()` con `response.body.getReader()` como en el ejemplo. Funciona en todos los browsers modernos (Chrome 94+, Firefox 102+, Safari 16+).

---

## Consideraciones de rendimiento

- **Latencia:** La evaluación con LLMs tarda entre **1 y 5 minutos** por video dependiendo de la cantidad de features. Planificar la UX con un estado de carga apropiado.
- **Timeout:** Cloud Run tiene un máximo de **3600 segundos** por request. Para batches grandes de videos, evaluar de a uno o en paralelo desde el frontend.
- **Anotaciones:** Activar `use_annotations: true` incrementa el tiempo y el costo de forma significativa. Recomendado solo cuando se necesita máxima precisión.
- **Múltiples videos:** Se pueden enviar varios URIs en un mismo request. El servicio los procesa de forma secuencial. Con `POST /evaluate` los resultados llegan todos juntos al final; con `POST /evaluate/stream` el frontend recibe progreso video a video en tiempo real.

---

## Documentación interactiva

FastAPI genera automáticamente una UI interactiva (Swagger) donde se pueden probar todos los endpoints:

```
https://<SERVICE_URL>/docs
```

También está disponible el schema OpenAPI en:

```
https://<SERVICE_URL>/openapi.json
```
