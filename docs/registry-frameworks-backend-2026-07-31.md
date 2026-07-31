# Plan: registry de frameworks + campo `framework_id` (backend)

## Objetivo

Introducir un mecanismo de registro de "frameworks" de evaluación (mismo patrón que ya
existe para `creative_providers/`), con **ABCD como único framework registrado por
ahora**, y conectar ese registro a un campo `framework_id` real en el contrato de la API
(request y response). El objetivo NO es diseñar Monks Framework — es dejar la plomería
lista para que, cuando exista un segundo framework, agregarlo sea "registrar una
implementación nueva" en vez de tocar `if/elif` en varios archivos.

Este cambio es **aditivo y no debe romper nada del comportamiento actual**: un request
sin `framework_id` (o con `framework_id: null`) tiene que comportarse exactamente igual
que hoy.

## Contexto

Hoy no existe ningún concepto de "framework" en el backend. Lo que hay es
`AbcdContentFormat` (enum con `LONG_FORM_ABCD`/`SHORTS`), que es una variante de
**formato** dentro de ABCD, no un framework distinto. El catálogo de features se resuelve
así:

- `features_repository/feature_configs_handler.py`: `FeaturesConfigsHandler` tiene un
  `if/elif` sobre `AbcdContentFormat` en `get_feature_configs_by_category` que decide si
  llamar a `get_long_form_abcd_feature_configs()` o `get_shorts_feature_configs()`. Hay un
  singleton a nivel de módulo: `features_configs_handler = FeaturesConfigsHandler()`.
- `evaluation_services/video_evaluation_service.py` (`VideoEvaluationService.evaluate_features`)
  llama a ese singleton en dos puntos:
  - línea 42: `feature_configs_handler.features_configs_handler.get_features_by_category_by_group_config(features_category)`
  - línea 129: `feature_configs_handler.features_configs_handler.get_feature_by_id(evaluated_feature.get("id"))`
  Estos son los **únicos** dos call sites del singleton que participan en el camino real
  de un request (`get_all_features`/`get_feature_configs_by_category` se llaman
  transitivamente desde ahí, no hay otro caller fuera de tests).

Ya existe un patrón de Protocol + Factory + registro explícito por import para
"creative providers" (`creative_providers/creative_provider_proto.py`,
`creative_provider_factory.py`, `creative_provider_registry.py`), usado desde `main.py`.
Este plan replica ese mismo patrón para frameworks, pero con una diferencia importante:
**el registry tiene que quedar en el camino real de resolución de features**, no solo
validar un string. Si el registry existiera únicamente para chequear
`framework_id in ids_conocidos` sin que nada dependa de él para decidir el catálogo, sería
metadata decorativa — exactamente el tipo de cosa que se limpió en Nivel 0
(`evaluation_method`, que se escribía pero nunca se leía para decidir nada). Por eso la
Tarea 4 reemplaza los dos call sites de arriba para que pasen por el registry.

Diseño ya validado en `plan-para-escalar-frameworks/01-preguntas-por-confirmar.md`
(preguntas B2 y B3) — este plan es la implementación de esa parte específica, sin tocar
todavía el resto de lo que B2 diseña (por ejemplo el array unificado `features[]` en la
respuesta — ver "Fuera de alcance" al final).

## Archivos relevantes

- `frameworks/framework_proto.py` (nuevo)
- `frameworks/framework_factory.py` (nuevo)
- `frameworks/framework_registry.py` (nuevo)
- `features_repository/feature_configs_handler.py` (sin cambios de lógica, solo pasa a
  ser la implementación ABCD del framework)
- `evaluation_services/video_evaluation_service.py` (líneas 42 y 129)
- `configuration.py` (`__init__`, `set_parameters`)
- `api_models.py` (`EvaluateRequest`, `VideoAssessmentResponse`, `from_video_assessment`)
- `models.py` (`VideoAssessment`, línea ~70)
- `server.py` (`_setup_config`, línea ~31)
- `main.py` (`execute_abcd_assessment_for_videos`, dos construcciones de
  `models.VideoAssessment`: la del camino exitoso y la del `except`)
- `tests/test_server_integration.py`
- Un archivo de test nuevo para el registry (elegir el nombre siguiendo la convención
  existente, ej. `tests/test_framework_registry.py`)

## Tareas

- [ ] **1. Crear el Protocol del framework** en `frameworks/framework_proto.py`, mirroring
  el estilo de `creative_providers/creative_provider_proto.py`:

  ```python
  from typing import Protocol
  import models


  class EvaluationFrameworkProto(Protocol):
    """Structural interface for an evaluation framework's feature catalog."""

    def get_features_by_category_by_group_config(
        self, category: models.AbcdContentFormat
    ) -> dict:
      """Returns feature configs for the given category, grouped by group_by."""
      ...

    def get_feature_by_id(self, feature_id: str) -> models.VideoFeature | None:
      """Looks up a single feature config by id across the whole framework."""
      ...
  ```

  Nota: el parámetro `category: AbcdContentFormat` queda tal cual está hoy (no se
  generaliza a un "variant" abstracto). Es lo que existe realmente y lo único que ABCD
  necesita; generalizarlo sin un segundo framework concreto para validar contra sería
  adivinar una forma. Cuando exista Monks y su propio concepto de variantes, se revisa
  esta interfaz.

- [ ] **2. Crear la factory** en `frameworks/framework_factory.py`, mirroring
  `creative_providers/creative_provider_factory.py`, pero registrando **instancias**, no
  clases (a diferencia de `CreativeProviderFactory`, que instancia bajo demanda). Razón:
  `features_configs_handler.features_configs_handler` ya es un singleton sin estado
  propio de request, no tiene sentido crear una instancia nueva por cada `get_framework`.

  ```python
  class FrameworkFactory:
    """Factory to register/retrieve evaluation framework implementations."""

    def __init__(self):
      self._frameworks = {}

    def register_framework(self, framework_id: str, framework) -> None:
      self._frameworks[framework_id] = framework

    def get_framework(self, framework_id: str):
      framework = self._frameworks.get(framework_id)
      if framework is None:
        raise ValueError(framework_id)
      return framework

    def list_framework_ids(self) -> list[str]:
      return list(self._frameworks.keys())
  ```

- [ ] **3. Crear el registro** en `frameworks/framework_registry.py`, mirroring
  `creative_providers/creative_provider_registry.py` (registro explícito en tiempo de
  import, sin decoradores):

  ```python
  from features_repository import feature_configs_handler
  from frameworks import framework_factory

  framework_factory_instance = framework_factory.FrameworkFactory()


  def register_frameworks():
    """Register the different evaluation frameworks."""
    framework_factory_instance.register_framework(
        "abcd", feature_configs_handler.features_configs_handler
    )


  register_frameworks()
  ```

  Verificar con `python3 -c "from frameworks import framework_registry; print(framework_registry.framework_factory_instance.list_framework_ids())"`
  que imprime `['abcd']` sin errores.

- [ ] **4. Conectar el registry al camino real de evaluación** en
  `evaluation_services/video_evaluation_service.py`:
  - Importar `from frameworks import framework_registry`.
  - Al principio de `evaluate_features` (antes de la línea que hoy es 42), resolver:
    ```python
    framework = framework_registry.framework_factory_instance.get_framework(
        config.framework_id
    )
    ```
  - Reemplazar la línea 42 (`feature_configs_handler.features_configs_handler.get_features_by_category_by_group_config(...)`)
    por `framework.get_features_by_category_by_group_config(features_category)`.
  - Reemplazar la línea 129 (`feature_configs_handler.features_configs_handler.get_feature_by_id(...)`)
    por `framework.get_feature_by_id(evaluated_feature.get("id"))`.
  - El import directo de `feature_configs_handler` en este archivo puede quedar si se
    usa en otro lado del archivo; si no se usa más, borrarlo (no dejar imports muertos).
  - Comportamiento esperado: como `config.framework_id` siempre va a ser `"abcd"` en la
    práctica (es el único registrado y el valor se resuelve/valida antes de llegar acá,
    ver Tarea 6), el resultado tiene que ser **idéntico byte a byte** al actual.
  - Nota para cuando exista un segundo framework: `get_feature_by_id` en
    `FeaturesConfigsHandler` resuelve vía `get_all_features()`, que concatena **las dos**
    categorías (`LONG_FORM_ABCD` + `SHORTS`) sin importar cuál se está evaluando en ese
    momento. Esto es correcto hoy porque ABCD es el único framework. Cualquier
    implementación futura de `EvaluationFrameworkProto` (Monks u otro) tiene que hacer que
    su propio `get_feature_by_id` busque en **todo** su catálogo, no solo en la categoría
    de la llamada en curso — si no, satisface el Protocol (compila) pero devuelve `None`
    para ids válidos de otras categorías, y esos features se pierden silenciosamente
    (ver el `else: logging.warning(...)` unas líneas más abajo en este mismo archivo).

- [ ] **5. Agregar `framework_id` a `Configuration`** (`configuration.py`):
  - En `__init__` (cerca de la línea 52, junto a `run_long_form_abcd`/`run_shorts`):
    `self.framework_id: str = "abcd"`.
  - En `set_parameters`, agregar el parámetro `framework_id: str = "abcd"` **con default**
    (para no romper los otros dos callers existentes: `utils.py` línea 38 y
    `tests/test_server_integration.py` línea 31, que no lo van a pasar). Asignar
    `self.framework_id = framework_id` dentro del método.
  - No agregar validación acá: la validación contra el registry vive en `server.py`
    (Tarea 6), porque `Configuration` no debería depender de `frameworks/`.

- [ ] **6. Agregar `framework_id` al request y validarlo** (`api_models.py` + `server.py`):
  - En `api_models.py`, `EvaluateRequest`: agregar, junto al bloque de "Feature flags"
    (cerca de `run_long_form_abcd`/`run_shorts`):
    ```python
    # Which evaluation framework to run. None/omitted means "abcd" (the default and,
    # for now, only registered framework). Must be validated against the framework
    # registry — never silently coerced to a value the caller didn't ask for.
    framework_id: Optional[str] = None
    ```
  - En `server.py`, `_setup_config` (línea ~31): antes de llamar a `config.set_parameters`,
    importar `from frameworks import framework_registry` y resolver:
    ```python
    resolved_framework_id = request.framework_id or "abcd"
    if resolved_framework_id not in framework_registry.framework_factory_instance.list_framework_ids():
      raise HTTPException(
          status_code=400,
          detail=(
              f"Unknown framework_id '{resolved_framework_id}'. Known frameworks: "
              f"{framework_registry.framework_factory_instance.list_framework_ids()}"
          ),
      )
    ```
    Este es el mismo patrón (mismo status code, mismo estilo de mensaje) que ya usa la
    validación de `invalid_brand_metadata` unas líneas más abajo en la misma función —
    seguirlo, no inventar un patrón nuevo.
  - Pasar `framework_id=resolved_framework_id` a `config.set_parameters(...)`.
  - Importante: **no** usar `Literal["abcd"]` en el modelo Pydantic para este campo. A
    diferencia de `language` (que es un `Literal` fijo), los valores válidos de
    `framework_id` vienen de un registry dinámico, no de un enum estático — por diseño,
    para no tener que tocar `api_models.py` cada vez que se registre un framework nuevo.

- [ ] **7. Agregar `framework_id` a `VideoAssessment` y propagarlo hasta la respuesta**:
  - `models.py`, `VideoAssessment` (línea ~70): agregar el campo `framework_id: str = "abcd"`
    al final del dataclass (después de `error: str | None = None`, para no romper el
    orden de dataclass fields sin default).
  - `main.py`, `execute_abcd_assessment_for_videos`: en las **dos** construcciones de
    `models.VideoAssessment(...)` (la del camino exitoso, ~línea 131, y la del bloque
    `except`, ~línea 181), agregar `framework_id=config.framework_id`.
  - `api_models.py`, `VideoAssessmentResponse`: agregar el campo `framework_id: str`, y en
    `from_video_assessment` poblarlo con `framework_id=assessment.framework_id`.
  - Resultado esperado: la respuesta de `/evaluate` y `/evaluate/stream` siempre trae
    `framework_id` (hoy sería siempre `"abcd"`), sin tocar `long_form_abcd`/`shorts` (esos
    quedan exactamente como están).

- [ ] **8. Tests** (agregar, no reemplazar los existentes):
  - Test nuevo (archivo nuevo o agregado a uno existente, a criterio del junior siguiendo
    la convención del repo) que verifique:
    - `framework_factory_instance.list_framework_ids() == ["abcd"]`.
    - `framework_factory_instance.get_framework("abcd")` devuelve el mismo objeto que
      `feature_configs_handler.features_configs_handler`.
    - `framework_factory_instance.get_framework("monks")` (id inexistente) levanta
      `ValueError`.
  - En `tests/test_server_integration.py`:
    - Un test que arme un `EvaluateRequest` con `framework_id="no-existe"` y verifique
      que `_setup_config` (o el endpoint, según cómo estén armados los tests existentes
      en ese archivo) levanta `HTTPException` con `status_code=400`.
    - Un test (o ajuste de uno existente) que confirme que un `EvaluateRequest` **sin**
      `framework_id` (el default `None`) resuelve a `"abcd"` y no cambia el comportamiento
      de ningún test que ya pasaba antes de este plan.
  - Correr `pytest tests/` completo al final. La baseline antes de este plan es **14
    tests pasando, 0 fallando**. Al terminar tiene que dar 14 + la cantidad de tests
    nuevos que se hayan agregado, pasando, 0 fallando. Si da menos de eso, hay una
    regresión — no está permitido justificarlo como "parte de un refactor": arreglarlo
    antes de reportar el plan como terminado.

## Fuera de alcance (a propósito, no lo toques en este plan)

- El array unificado `features: list[FeatureEvaluationResponse]` en
  `VideoAssessmentResponse` que describe B2 (pensado para cuando un segundo framework
  tenga una forma distinta a `long_form_abcd`/`shorts`). Hoy, con un solo framework
  registrado, ese array no tiene ningún consumidor real — se diseña junto con Monks, no
  antes.
- Reordenar `execute_abcd_assessment_for_videos` para que las dos ramas
  `run_long_form_abcd`/`run_shorts` dejen de estar hardcodeadas en `main.py`. Esa
  orquestación (loop genérico vs. ramas específicas de ABCD) es un cambio más profundo
  que ya se identificó como de mayor riesgo/esfuerzo en B3, y no es necesario para que el
  registry sea real — el registry ya queda conectado en el nivel de resolución de
  features (Tarea 4), que es el que decide comportamiento hoy.
- Ningún flag nuevo en la CLI (`utils.py` / `main()`) para elegir `framework_id`. La CLI
  y el notebook de Colab siguen funcionando con el default `"abcd"` sin cambios.
- Ninguna referencia a "Monks" en código o nombres — este plan es 100% sobre la
  infraestructura del registry con ABCD como único framework.

## Notas finales

- No toques nada de `creative_providers/` — es el patrón que se está imitando, no algo
  a modificar.
- No renombres `AbcdContentFormat`, `AbcdSubCategory` ni ningún símbolo ya renombrado en
  Nivel 0 (`plan-para-escalar-frameworks/03-nivel-0-completado.md` en el repo front tiene
  el historial completo si hace falta contexto).
- Al terminar, correr `pytest tests/` y confirmar 0 tests rotos. Si algo no compila o un
  test falla, arreglarlo antes de dar el plan por terminado — no dejar un estado a medias.
- No hacer `git add`/`git commit`/`git push`. Dejar los cambios sin commitear en el
  working tree; el commit lo hace el usuario o se coordina aparte.
