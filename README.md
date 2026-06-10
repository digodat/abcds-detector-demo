
## June, 2025 Update: Enhanced Capabilities and Flexibility

We're excited to announce major enhancements to the ABCDs Detector, significantly expanding its capabilities and offering greater flexibility in how you analyze your video creatives.

### What's New:

1.  **YouTube Shorts Evaluation with Research-Backed Top 20 Features:**
    *  Introducing SHORTS evaluation, specifically tailored for YouTube Shorts. Advanced research has identified the top 20 creative attributes that explain video performance variation, enabling more efficient creative optimization.

    **Top 20 YouTube Shorts Evaluation Features:**
    1. **Tight Framing & Visual Dominance** - Quantifies spatial dominance of the primary subject (≥60% of frame).
    2. **Human Voice Presence** - Quantifies the presence, duration, and quality of human speech.
    3. **Direct to Camera** - Quantifies the duration and intensity of direct eye contact with the lens.
    4. **Supers & Text-Audio Synchronicity** - Quantifies presence and synchronization of text overlays with spoken audio.
    5. **Product Close-Up** - Quantifies segments where the product occupies at least 30% of the frame.
    6. **Product Extreme Close-Up** - Quantifies segments where the product occupies 60% or more of the frame.
    7. **Product Context & Usage Quality** - Evaluates physical interaction and authentic utility demonstration.
    8. **Casual Language** - Quantifies script informality, everyday language, and conversational filler.
    9. **Humor & Comedic Timing** - Detects attempts at humor, physical comedy, satire, or comedic timing.
    10. **Character-Driven** - Evaluates a relatable character whose journey resonates with the audience.
    11. **Call to Action (Audio)** - Detects spoken instructions that direct the viewer to take action.
    12. **Special Offer (Speech)** - Detects audio announcements of a special offer, discount, or deal.
    13. **Production Style** - Quantifies 'Lo-Fi' aesthetics and User Generated Content (UGC) authenticity.
    14. **SFV Native Adaptation** - Measures how effectively the video mimics organic social content.
    15. **Emoji Usage** - Detects intentional, creative use of emojis, stickers, and animated effects.
    16. **Direct to Camera Character Talk** - Evaluates the intimacy and continuity of direct lens address.
    17. **Brand Secondary Element** - Evaluates if the brand feels like a natural, secondary part of the environment.
    18. **Everyday Persona Validation** - Verifies the video is led by an authentic, relatable 'everyday person'.
    19. **Secondary Product Context** - Evaluates if the product appears naturally as a secondary element.
    20. **Vertical Format Designed For Mobile** - Verifies 9:16 portrait optimization and detects letter/pillarboxing.

2.  **Direct YouTube URL Support:**
    *   You can now directly provide **YouTube URLs** for evaluation. This is applicable for public YouTube videos or videos from channels where the user is the owner.
    *   **Important Note:** Currently, YouTube URLs are evaluated using **LLMs only**. Annotation-based evaluation for YouTube URLs is not supported.

3.  **Flexible Creative Provisioning with Factory Pattern:**
    *   A new **Creative Provider** architecture, built on a factory pattern, allows developers to easily integrate and pull creatives from various data sources.
    *   **Supported Providers:**
        *   **Google Cloud Storage Creative Provider:** Retrieve individual videos or folders of videos from a GCS bucket.
        *   **YouTube Creative Provider:** Designed to retrieve a list of YouTube URLs. This can be adapted to integrate with the YouTube API for automated retrieval.
    *   **Custom Providers:** Implement your own creative providers by registering them in the `creative_provider_registry.py` file. Ensure your custom provider class implements the `get_creative_uris` method as specified in the `creative_provider_proto.py` file to return a list of creative URIs. Configuration in the system's `configuration.py` file is required to specify the provider type, please see the `set_parameters` function.

4.  **Feature Evaluation Methods:**
    *   Features are now evaluated using one of three methods:
        *   **LLMs Only:** Ideal for abstract concepts or when annotations are not available.
        *   **Annotations Only:** For features that can be reliably extracted or calculated from video metadata and vision models.
        *   **Combination of LLMs and Annotations:** For features requiring both structured data and nuanced understanding, especially those involving reasoning and calculations.
    *   The specific evaluation method for each feature is determined by extensive research and testing during pipeline implementation.

5.  **Custom Evaluation Functions for Core ABCDs:**
    *   For **Core ABCDs evaluation**, users can now implement their own custom evaluation functions for individual features. This is particularly useful for scenarios requiring a unique combination of LLMs and Annotations.
    *   Simply ensure your custom function complies with the defined interface and returns the expected standard evaluation response. You can return either True/False or an object with the evaluation details, please see the `VIDEO_RESPONSE_SCHEMA` object in `models.py` for more details.

6.  **Dynamic and Configurable Features:**
    *   All features are now **dynamic and configurable** via the `features_repository.py` file.
    *   To introduce a new feature, simply add it to the feature array within `features_repository.py` and configure its parameters; ABCD Detector will automatically evaluate it.
    *   Features can be **grouped** to be evaluated in a single prompt for efficiency, or configured with `NO_GROUPING` for individual evaluation (One API request per feature). Users should consider the potential cost implications when opting for individual evaluation.

# ABCDs Detector

The ABCDs Detector solution streamlines the assessment of your video ads against YouTube's ABCD framework. Powered by Google AI, this tool automates the evaluation process, providing detailed reports on how well your ads align with key attention-driving metrics. Simplify your YouTube ad analysis and gain valuable insights for optimization with the ABCDs Detector.

## The Approach

### Overview

The solution leverages:

**Video content annotation:** Google AI extracts features and identifies key moments within your video ads.

**Large Language Model (LLM) integration:** LLMs are used to assess features against YouTube's ABCD framework rubrics. This enables the detector to "ask questions" and determine if the ad adheres to each rubric.

By combining these techniques, ABCDs Detector automates the evaluation process and delivers comprehensive reports on how well your ads align with the ABCD framework. This empowers you to optimize your YouTube ad campaigns for maximum impact.

### Detailed approach

1. Video Intelligence API: To get annotations for the following features:
  - Label annotations
  - Face annotations
  - Text annotations
  - Object annotations
  - People annotations
  - Speech annotations
  - Shot annotations
  - Logo annotations


2. Gemini: To perform video Q&A about the features to evaluate if the video adheres to the ABCD rubrics. The colab will send a request to Gemini with tailored prompts to evaluate each rubric.

ABCDs Detector will perform 2 verifications, first with annotations and then with LLMs. Since the LLM approach is prone to hallucinations, False Positives or False Negatives will be expected. The solution will still require human QA if 100% accuracy is required for the evaluation.

ABCDs Detector MVP supports a single video evaluation for the following features/rubrics:
  - Quick Pacing
  - Quick Pacing (First 5 seconds)
  - Dynamic Start
  - Supers
  - Supers with Audio
  - Brand Visuals
  - Brand Visuals (First 5 seconds)
  - Brand Mention (Speech)
  - Brand Mention (Speech) (First 5 seconds)
  - Product Visuals
  - Product Visuals (First 5 seconds)
  - Product Mention (Text)
  - Product Mention (Text) (First 5 seconds)
  - Product Mention (Speech)
  - Product Mention (Speech) (First 5 seconds)
  - Visible Face (First 5 seconds)
  - Visible Face (Close Up)
  - Presence of People
  - Presence of People (First 5 seconds)
  - Overall Pacing
  - Audio Speech Early
  - Call To Action (Text)
  - Call To Action (Speech)

For a definition for each of these signals please take a look at the [long_form_abc_features.py](https://github.com/google-marketing-solutions/abcds-detector/blob/main/features_repository/long_form_abcd_features.py) and [shorts_features.py](https://github.com/google-marketing-solutions/abcds-detector/blob/main/features_repository/shorts_features.py) files.

The final result of the assessment (Excellent, Might Improve or Needs Review) is defined in the [generics_helpers.py](https://github.com/google-marketing-solutions/abcds-detector/blob/main/helpers/generic_helpers.py?plain=1#L186) and can be customized based on preferences.

### Google Cloud Cost breakdown

1. Video Intelligence API: Prices are per minute. Partial minutes are rounded up to the next full minute. Volume is per month. For more details please check the official [documentation](https://cloud.google.com/video-intelligence/pricing).

2. Gemini: With the Multimodal models in Vertex AI, you can input either text or media (images, video). Text input is charged by every 1,000 characters of input (prompt) and every 1,000 characters of output (response). Characters are counted by UTF-8 code points and white space is excluded from the count. Prediction requests that lead to filtered responses are charged for the input only. At the end of each billing cycle, fractions of one cent ($0.01) are rounded to one cent. Media input is charged per image or per second (video). For more details please check the official documentation: https://cloud.google.com/vertex-ai/generative-ai/pricing

For questions, please reach out to: abcds-detector@google.com

## Requirements
Please esure you have access to all of the following before starting:
* [Google Cloud Project](https://cloud.google.com) with enabled APIs:
    * [Video Intelligence API](https://console.cloud.google.com/marketplace/product/google/videointelligence.googleapis.com) - Optional if you are only using LLMs.
    * [Vertex AI API](https://console.cloud.google.com/marketplace/product/google/aiplatform.googleapis.com) - Optional if you are only using Annotations.
    * [Knowledge Graph API](https://console.cloud.google.com/marketplace/product/google/kgsearch.googleapis.com) - Optional if you are only using LLMs.
    * [Cloud Storage API](https://console.cloud.google.com/marketplace/product/google/storage.googleapis.com)
    * [BigQuery](https://cloud.google.com/bigquery/docs/reference/rest) - Optional if you don't want to store the results in BQ.
* [API Key](https://cloud.google.com/docs/authentication/api-keys) provisioned. - Optional if you are only using LLMs.
* [Project Billing](https://cloud.google.google.com/billing/) enabled.
* Python libraries:
    * `google-cloud-videointelligence`
    * `google-cloud-aiplatform`
* FFMPEG (not needed for colab)
  * Save the platform specific [FFMPEG Binary](https://evermeet.cx/ffmpeg/) locally.
  * Set the **IMAGEIO_FFMPEG_EXE** variable to the FFMPEG binary path.

You can see more on the ABCD methodology [here.](https://www.thinkwithgoogle.com/intl/en-emea/future-of-marketing/creativity/youtube-video-ad-best-practices/)

## Where to start?

There are three ways to run ABCDs Detector:

| Mode | Best for |
|------|----------|
| **Cloud Run HTTP Service** | Consuming the evaluator from a frontend or external system |
| **Google Colab Notebook** | Interactive exploration and one-off evaluations |
| **CLI (local)** | Debugging and development |

---

## Cloud Run HTTP Service

The project includes a FastAPI HTTP server (`server.py`) that exposes the evaluator as a REST endpoint, ready to deploy as a **Cloud Run Service**.

### Deploy via repository connection

1. Connect this repository to Cloud Run in the [Google Cloud Console](https://console.cloud.google.com/run).
2. Cloud Run detects the `Dockerfile` automatically.
3. Configure the following environment variables in the service settings (todas opcionales):

| Variable | Description |
|----------|-------------|
| `KG_API_KEY` | Knowledge Graph API key (use Secret Manager) |
| `PROJECT_ID` | GCP project ID — solo necesario si el service account no tiene proyecto configurado en sus credenciales (caso infrecuente) |

El `project_id` se resuelve automáticamente en este orden: (1) campo `project_id` en el body del request, (2) Application Default Credentials del service account de Cloud Run, (3) variable de entorno `PROJECT_ID`.

4. Set **concurrency to 1** per instance to avoid temp file conflicts when processing large batches. Increase when needed after validating.

### API reference

**Health check**
```
GET /health
→ {"status": "ok"}
```

**Evaluate videos**
```
POST /evaluate
Content-Type: application/json

{
  "video_uris": ["gs://my-bucket/video.mp4"],
  "bucket_name": "my-bucket",
  "project_id": "my-gcp-project",      // optional: inferred from ADC if omitted
  "brand_name": "My Brand",            // optional if extract_brand_metadata=true
  "use_llms": true,
  "use_annotations": false,
  "run_long_form_abcd": true,
  "run_shorts": false,
  "extract_brand_metadata": true
}
```

Response:
```json
{
  "status": "success",
  "assessments": [
    {
      "brand_name": "My Brand",
      "video_uri": "gs://my-bucket/video.mp4",
      "long_form_abcd": [
        {
          "feature_id": "a_dynamic_start",
          "feature_name": "Dynamic Start",
          "detected": true,
          "confidence_score": 0.9,
          "rationale": "...",
          "evidence": "...",
          "strengths": "...",
          "weaknesses": "..."
        }
      ],
      "shorts": []
    }
  ]
}
```

Interactive API docs are available at `<service-url>/docs` once deployed.

### GCP APIs required for Cloud Run

Enable the following APIs in your project:
- [Vertex AI API](https://console.cloud.google.com/marketplace/product/google/aiplatform.googleapis.com) — for Gemini LLM evaluation
- [Cloud Storage API](https://console.cloud.google.com/marketplace/product/google/storage.googleapis.com) — to read videos
- [Cloud Run API](https://console.cloud.google.com/marketplace/product/google/run.googleapis.com)
- [Video Intelligence API](https://console.cloud.google.com/marketplace/product/google/videointelligence.googleapis.com) — only if `use_annotations: true`
- [BigQuery](https://console.cloud.google.com/marketplace/product/google/bigquery.googleapis.com) — only if storing results in BQ

The service account attached to Cloud Run needs the following roles: `roles/aiplatform.user`, `roles/storage.objectViewer`, `roles/bigquery.dataEditor` (optional), `roles/cloudvideointelligence.serviceAgent` (optional).

---

## Colab / Local usage

1. Navigate to [colab.research.google.com](http://colab.research.google.com).
2. In the dialog, open a Notebook from GitHub.
3. Enter the url from this page.

**Note:** This repository provides python modules that can be executed on local machines for easier debugging and troubleshooting.

## Instructions
Please follow the steps below before executing the ABCDs Detector solution. Every **[VARIABLE]** is a parameter you can configure in the **Define ABCDs Detector Parameters** section.

1. Store your videos on [Google Cloud Storage](https://console.cloud.google.com/storage/browser) with the following folder structure:
  * **[BUCKET_NAME]** - name of bucket, ensure you have write permission. Same as paramter below.
    * **[brand_name]** - a folder, must be same as parameter below.
      * **videos** - a folder called videos, hard coded. Consider only **10-15 videos max** due to processing time limitations.
        * **some_video.mp4** - upload video to analyze, must be **mp4** and must be **[<= 50 MB](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models)**.
      * **annotations** - a folder created by this tool to store AI data. No need to create this.

1. Make sure the requirements are met:
  * Enable APIs:
    * [Video Intelligence API](https://console.cloud.google.com/marketplace/product/google/videointelligence.googleapis.com)
    * [Vertex AI API](https://console.cloud.google.com/marketplace/product/google/aiplatform.googleapis.com)
    * [Knowledge Graph API](https://console.cloud.google.com/marketplace/product/google/kgsearch.googleapis.com)
    * [Cloud Storage API](https://console.cloud.google.com/marketplace/product/google/storage.googleapis.com)
    * [BigQuery](https://console.cloud.google.com/marketplace/product/google/bigquery.googleapis.com)
  * Provision [An API Key](https://cloud.google.com/docs/authentication/api-keys):
    1. Visit [Credentials Page](https://cloud.console.google.com/apis/credentials).
    1. Create a **New API Key** and copy it into **[KNOWLEDGE_GRAPH_API_KEY]** below.
    1. We recommend editing and restricting the key to the above APIs.

1. Define all the parameters.
  * Required:
    * Google Cloud Project Details
    * Brand And Product Details
  * Optional
    * Solution Setup
    * ABCD Framework Details
    * LLM Configuration

1. Run all of the steps in sequence.
  * Some steps do not produce output, they only define functions.
  * If a step asks you to **Restart Runtime**, do so.
  * If a step displays an error, stop and debug it. Debug the following:
    * APIs are enabled.
    * Storage bucket is correctly configured.
    * The video is the correct size.
    * API Key has correct restrictions.
    * Previous colab sections completed.
    * Select _Runtime > Reset Session and Run All_ as a last resort.
  * The **Execute Bulk ABCD Assessment** produces the video analysis.

1. For questions, please reach out to: abcds-detector@google.com

**Note:** Please check the official [Gemini API documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini) to learn more about the LLM parameters (temperature, top_k, top_p, etc) that are used in this colab.

## Customization:

* Change the default parameters used for the ABCDs detection.
* Modify the ABCDs signals detection logic to fit yours.
* Add or remove ABCDs signals.
* Specify your own logic for calculating ABCDs score per video.
* ABCD features are dynamically added to a JSON list. If you want to add/remove features, please do that directly in the features_config/features.py file.
* To optimize LLM execution, features support grouping by 'full_video' and 'first_5_secs_video'. If you want to execute the features separately, please specify 'no_grouping' in the "group_by" field.

**Note:**

* This notebook is a starting point and can be further customized to fit your specific needs.

## Roadmap

1. Improvement: cut the video in shorter segments to improve LLM accuracy.
2. Improvement: leverage a [consensus approach](https://arxiv.org/pdf/2310.20151.pdf) to increase response confidence.

## Additional Resources:

* [Google Video Intelligence API](https://cloud.google.com/video-intelligence?hl=en)
* [Vertex AI](https://cloud.google.com/vertex-ai)
* [ABCD Framework best practices](https://www.thinkwithgoogle.com/intl/en-emea/future-of-marketing/creativity/youtube-video-ad-best-practices/)
