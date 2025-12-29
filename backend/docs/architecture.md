# System Architecture

## High-Level System Context
This diagram illustrates how the Samvaad Sathi Backend interacts with external users and systems.

```mermaid
graph TD
    User[Candidate / User]
    
    subgraph "Samvaad Sathi System"
        API[Backend API]
        Auth[Auth Service\n(Cognito)]
        DB[(Database\nAurora/Supabase)]
        LLM[LLM Provider\n(OpenAI/Anthropic)]
    end

    User -->|HTTPS/REST| API
    API -->|Authenticate| Auth
    API -->|Read/Write| DB
    API -->|Generate/Analyze| LLM
```

## Component Architecture
This diagram details the internal structure of the backend, highlighting the flow of data from the API through services to the data layer.

```mermaid
graph TD
    subgraph "API Layer"
        Router_Interview[Interview Router]
        Router_Audio[Audio Router]
        Router_Analysis[Analysis Router]
        Router_Report[Report Router]
    end

    subgraph "Service Layer"
        Service_Orch[Interview Orchestrator]
        Service_Audio[Audio Processor\n(Whisper)]
        Service_LLM[LLM Service]
        Service_Metrics[Metrics Engine\n(Pace/Pause)]
        Service_Report[Report Generator]
    end

    subgraph "Data Layer"
        Repo_Interview[Interview Repository]
        Repo_User[User Repository]
        Repo_Analysis[Analysis Repository]
    end

    %% Relationships
    Router_Interview --> Service_Orch
    Router_Audio --> Service_Audio
    Router_Analysis --> Service_Metrics
    Router_Report --> Service_Report

    Service_Orch --> Service_LLM
    Service_Orch --> Repo_Interview
    
    Service_Audio --> Service_LLM
    Service_Audio --> Repo_Analysis
    
    Service_Metrics --> Repo_Analysis
    
    Service_Report --> Repo_Interview
    Service_Report --> Repo_Analysis

    %% External Dependencies
    Service_LLM -.->|API Call| External_AI[External AI Models]
```
