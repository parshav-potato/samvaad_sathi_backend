# Data Architecture & Model Training Strategy (Phase 2/3)

## Overview
This document outlines the data management strategy and model training architecture for Samvaad Sathi. The system is designed to handle high-fidelity audio processing while leveraging active research in Automatic Speech Recognition (ASR) to adapt to Indian English accents using the NPTEL2020 dataset.

## Data Architecture & Flow

The following diagram illustrates the flow of data from ingestion to storage, inference, and the feedback loop for model adaptation.

```mermaid
graph TD
    subgraph "Data Acquisition"
        User((User)) -->|Upload Audio/Resume| API[FastAPI Gateway]
        NPTEL[(NPTEL2020 Dataset)]
    end

    subgraph "Data Management Layer"
        API -->|Validation| Validator{Quality Check}
        Validator -->|Pass| Norm[Normalization\n(16kHz Mono)]
        Validator -->|Fail| Reject[Reject Request]
        
        Norm -->|Store Raw| ObjStore[Object Storage\n(S3/MinIO)]
        Norm -->|Store Meta| DB[(PostgreSQL)]
    end

    subgraph "Inference Pipeline (Phase 2)"
        ObjStore -->|Stream| FeatureExt[Feature Extraction\n(Librosa)]
        ObjStore -->|Stream| Whisper[Whisper ASR\n(Base Model)]
        
        Whisper -->|Text| LLM[LLM Analysis\n(OpenRouter)]
        Whisper -->|Phonemes| Pronunc[Pronunciation Scorer\n(GOP/MDD)]
        FeatureExt -->|Prosody| PacePause[Pace & Pause\nAnalysis]
        
        LLM --> DB
        Pronunc --> DB
        PacePause --> DB
    end

    subgraph "Training & Adaptation (Phase 3)"
        direction TB
        NPTEL -->|Curated Audio| Trainer[Fine-Tuning Engine]
        ObjStore -.->|Anonymized Samples| Trainer
        
        Trainer -->|PEFT/LoRA| Adapter[Accent Adapter]
        Adapter -.->|Update Weights| Whisper
    end
```

## Data Management Approach

### 1. Collection & Ingestion
-   **Gateway:** A secure **FastAPI** interface handles multipart uploads.
-   **Validation:** Immediate validation checks for file format (WAV/MP3/M4A), size limits, and audio duration.
-   **Normalization:** All incoming audio is normalized to **16kHz mono** using `ffmpeg` to match Whisper's input requirements and ensure consistent feature extraction.

### 2. Storage & Access Control
-   **Object Storage:** Raw and processed audio files are stored in an S3-compatible object store, organized by `user_id/session_id`.
-   **Structured Database:** **PostgreSQL** stores metadata, transcription text, and computed metrics.
-   **Access Control:** Strict Row-Level Security (RLS) and signed URLs ensure users can only access their own data.

## Model Training & Research Alignment

### Dataset: NPTEL2020 Indian English Speech
We utilize the **NPTEL2020 Indian English Speech Dataset**, released by AI4Bharat.
-   **Relevance:** Contains diverse Indian accents often underrepresented in standard Western-centric datasets (e.g., LibriSpeech).
-   **Rights:** Publicly released for research and academic use; utilized in compliance with its license.

### Fine-Tuning Strategy (Phase 3)
Our approach is inspired by active research in **Parameter-Efficient Fine-Tuning (PEFT)** and **Mispronunciation Detection and Diagnosis (MDD)**.

#### A. Accent Adaptation via LoRA
Instead of full fine-tuning, we employ **Low-Rank Adaptation (LoRA)** on the Whisper encoder layers.
-   **Why:** Allows the model to adapt to Indian English prosody and phonemes without catastrophic forgetting of its general English capabilities.
-   **Process:** The NPTEL dataset is used to train lightweight adapter layers that are injected into the frozen Whisper model during inference.

#### B. Pronunciation Scoring (GOP)
We move beyond simple text-to-text comparison by implementing **Goodness of Pronunciation (GOP)** scores.
-   **Method:** We extract frame-level posterior probabilities from the Whisper decoder.
-   **Alignment:** Forced alignment aligns the audio with the target transcript (phonemes).
-   **Scoring:** The log-likelihood ratio of the spoken phoneme vs. the target phoneme provides a granular pronunciation score, identifying specific mispronounced sounds common in Indian English.

## Technology Stack

-   **Frameworks:** FastAPI, PyTorch, Hugging Face Transformers.
-   **Audio Processing:** Librosa, FFmpeg, NumPy.
-   **Database:** PostgreSQL (Metadata), S3-compatible storage (Blobs).
-   **AI/ML:** OpenAI Whisper (Base), OpenRouter (LLM Access).

## Governance & Compliance

-   **Data Privacy:** Compliant with **DPDP (Digital Personal Data Protection Act)** principles.
-   **Encryption:** AES-256 for data at rest; TLS 1.3 for data in transit.
-   **Consent:** Explicit user consent is required for data collection. An "Opt-in" mechanism allows users to contribute anonymized data for model improvement.
-   **Right to Forget:** Automated scripts (`delete_user_data.py`) allow for complete removal of user data upon request.
