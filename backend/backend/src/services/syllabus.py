"""
Syllabus and prompting helpers for interview question generation.

Provides:
- Canonical roles and aliases mapping from free-form `track` to a target role
- Topic banks per role and difficulty for 'tech' and 'tech_allied'
- Behavioral topics list (from product requirements)
- Ratio helper to split the 5 questions into tech/tech_allied/behavioral buckets
"""
from __future__ import annotations

from typing import Dict, List, Tuple


CANONICAL_ROLES: List[str] = [
    "React Developer",
    "Node JS Developer",
    "Express JS Developer",
    "MERN Stack Developer",
    "UI Developer",
    "JavaScript Developer",
]

# Map common track keywords to one of the canonical roles
ROLE_ALIASES: Dict[str, str] = {
    "react": "React Developer",
    "frontend": "UI Developer",
    "ui": "UI Developer",
    "javascript": "JavaScript Developer",
    "js": "JavaScript Developer",
    "mern": "MERN Stack Developer",
    "fullstack": "MERN Stack Developer",
    "node": "Node JS Developer",
    "express": "Express JS Developer",
}


def derive_role(track: str) -> str:
    t = (track or "").strip().lower()
    for key, role in ROLE_ALIASES.items():
        if key in t:
            return role
    # Default fallback when we don't recognize the track
    return "JavaScript Developer"


# Topic banks per role and difficulty
SYLLABUS: Dict[str, Dict[str, Dict[str, List[str]]]] = {
    # difficulty -> category -> topics
    "React Developer": {
        "easy": {
            "tech": [
                "JSX and rendering basics",
                "Props vs State",
                "Component composition and reusability",
                "useState/useEffect fundamentals",
                "Event handling and synthetic events",
                "Conditional rendering patterns",
                "Lists, keys, and reconciliation basics",
                "Basic forms and controlled components",
                "Default props and propTypes basics",
                "Inline vs CSS className styling trade-offs",
                "One-way data flow and immutability basics",
                "Lifting state up: when and how",
                "Keyed lists: stable keys and anti-patterns",
                "Ref basics (useRef) for DOM access",
                "Basic accessibility in React (labels, roles)",
                "Handling side effects in useEffect (deps array)",
                "Component file structure and naming",
                "Simple composition vs inheritance mindset",
            ],
            "tech_allied": [
                "ES6+ features (let/const, arrow functions, spread/rest)",
                "NPM/Yarn basics and scripts",
                "CSS approaches (CSS Modules, styled-components, Tailwind basics)",
                "Bundling with Vite/Webpack basics",
                "Data fetching with fetch/axios",
                "Basic testing with Jest/RTL",
                "Simple accessibility (labels, alt text, focus order)",
                "Basic TypeScript with React (FC, Props)",
                "Linting and formatting (ESLint/Prettier)",
                "Environment variables (.env) for frontend",
                "Devtools basics (React DevTools)",
                "HTTP status codes and simple error handling",
                "Package management (lockfiles, semver)",
                "Basic Git workflow (branch, commit, PR)",
            ],
        },
        "medium": {
            "tech": [
                "Context API vs prop drilling",
                "React reconciliation and keys",
                "Memoization (React.memo, useMemo, useCallback)",
                "Custom hooks patterns",
                "Error boundaries and error handling",
                "Forms: validation and complex inputs",
                "Performance (render cycles, batching)",
                "Derived state vs memoization",
                "Ref patterns (callback refs, measuring)",
                "Suspense for data fetching (basics)",
                "Compound component patterns",
                "Controlled vs uncontrolled components trade-offs",
                "Portals and overlay patterns",
                "State colocation and module boundaries",
                "Avoiding stale closures and race conditions",
            ],
            "tech_allied": [
                "Routing (React Router, nested routes)",
                "State mgmt (Redux/RTK, Zustand, Jotai)",
                "Testing (Jest, React Testing Library) including mocks",
                "Accessibility (ARIA, keyboard navigation, focus management)",
                "CSS performance and theming",
                "Code splitting and lazy loading",
                "TypeScript patterns (Discriminated unions, generics in props)",
                "API error states and retries",
                "Form libs (React Hook Form, Formik)",
                "Design tokens and theming in UI kits",
                "Storybook and component documentation",
                "i18n basics (react-intl, i18next)",
                "Analytics hooks and event tracking",
            ],
        },
        "hard": {
            "tech": [
                "Concurrent features (useTransition, Suspense)",
                "Server Components trade-offs",
                "SSR/SSG hydration nuances",
                "Advanced rendering and hydration failures",
                "Complex state orchestration (state machines)",
                "Rendering performance profiling and flame charts",
                "Isolating renders and avoiding tearing",
                "Architecting large React apps (module boundaries)",
                "Cache strategies with Suspense and RSC",
                "Avoiding waterfalls and network overfetching",
                "Non-visual hooks and resource lifecycles",
                "Accessibility at scale (virtualized/grids)",
            ],
            "tech_allied": [
                "Microfrontends architectures",
                "Advanced code splitting and prefetching",
                "Security (XSS, CSP in SPAs, sandboxing)",
                "Internationalization at scale (pluralization, RTL)",
                "Design systems governance and tokens",
                "Bundle budgets and performance regressions",
                "SSR/SSG/ISR strategies (Next.js deep dive)",
                "Edge rendering and CDN caching",
                "Web vitals instrumentation and SLOs",
                "A/B testing and feature flags integration",
                "Error boundaries strategy at app scale",
                "Release strategies (canary, dark launches)",
            ],
        },
    },
    "UI Developer": {
        "easy": {
            "tech": [
                "Semantic HTML",
                "CSS layout (Flexbox, Grid) basics",
                "Responsive design fundamentals",
                "Vanilla JS DOM manipulation",
                "Forms, inputs, simple validation",
                "SVG and icons basics",
                "Box model and stacking context basics",
                "Media queries and mobile-first",
                "Units (px, rem, em, vw/vh) and scaling",
                "Positioning (static, relative, absolute, fixed, sticky)",
                "Basic accessibility semantics (landmarks, headings)",
            ],
            "tech_allied": [
                "Accessibility basics (landmarks, roles, labels)",
                "Color contrast & typography",
                "Asset optimization (images, fonts)",
                "Browser DevTools essentials",
                "Core Web Vitals (LCP/FID/CLS) basics",
                "Image formats (PNG/JPEG/WebP/AVIF/SVG)",
                "Icon systems and sprite sheets",
                "Design handoff (Figma/Zeplin) basics",
                "Simple build setups (Vite) for static sites",
                "Reset vs normalize CSS",
            ],
        },
        "medium": {
            "tech": [
                "Advanced CSS (Grid areas, container queries)",
                "Component libraries (MUI/Ant/Tailwind)",
                "Complex UI state & events",
                "SPA patterns and routing",
                "Web APIs (IntersectionObserver, Storage, Clipboard)",
                "Animation basics (CSS/WAAPI)",
                "CSS architecture (BEM, ITCSS)",
                "Dark mode and prefers-color-scheme",
                "Accessible custom widgets (tabs, menus)",
                "Virtualized lists basics",
                "Drag-and-drop interactions",
            ],
            "tech_allied": [
                "WCAG 2.x and a11y testing",
                "Design tokens and theming",
                "Build tooling (Vite/Webpack/Rollup)",
                "Unit/E2E testing (RTL, Playwright)",
                "Performance audits (Lighthouse) and budgets",
                "Fonts: variable fonts, FOIT/FOUT mitigation",
                "Internationalization (RTL, locale data)",
                "Content security basics for UI",
                "Design QA and visual regression testing",
                "UX heuristics and usability basics",
            ],
        },
        "hard": {
            "tech": [
                "Rendering pipelines and paint optimizations",
                "Virtualization for large lists",
                "Complex form architectures",
                "Statecharts/XState for UI flows",
                "Canvas/WebGL/SVG advanced rendering",
                "Accessibility of complex widgets",
                "3D and high-performance rendering",
                "Optimizing animations (RAF, GPU accel)",
                "Offline-first patterns (Service Worker)",
                "Complex focus management and roving tabindex",
            ],
            "tech_allied": [
                "Advanced a11y (focus traps, screen readers)",
                "Internationalization at scale",
                "Design systems governance & documentation",
                "Performance budgets and regressions",
                "Security (clickjacking, CSP)",
                "Cross-browser/platform QA at scale",
                "Experimentation frameworks",
                "Privacy and consent management (CMP)",
                "Monitoring front-end errors (Sentry)",
            ],
        },
    },
    "JavaScript Developer": {
        "easy": {
            "tech": [
                "Types and coercion",
                "Scope and closures",
                "Hoisting and TDZ",
                "Array/object methods",
                "Promises basics",
                "Modules and imports",
                "Template literals and destructuring",
                "Spread vs rest operators",
                "this binding basics",
                "Equality (== vs ===)",
            ],
            "tech_allied": [
                "NPM scripts",
                "ESLint/Prettier",
                "Debugging with DevTools",
                "Basic testing (Jest)",
                "HTTP basics and fetch",
                "JSON and serialization",
                "Basic regex in JS",
                "Error objects and stack traces",
                "Console API and logging best practices",
            ],
        },
        "medium": {
            "tech": [
                "Event loop and task queue",
                "Async/await patterns",
                "Error handling strategies",
                "Functional programming patterns",
                "Performance (debounce/throttle)",
                "Immutability and structural sharing",
                "Iterators and generators",
                "Map/Set/WeakMap/WeakSet usage",
                "Module patterns and bundling",
                "Typed Arrays and buffers basics",
            ],
            "tech_allied": [
                "Bundlers and tree shaking",
                "TypeScript fundamentals",
                "Testing pyramids",
                "Security (XSS, CSRF basics)",
                "Node.js basics",
                "Transpilation (Babel) and targets",
                "Polyfills and core-js",
                "Source maps and debugging",
                "Code splitting and dynamic import",
            ],
        },
        "hard": {
            "tech": [
                "V8 internals (hidden classes, ICs)",
                "Streaming and backpressure",
                "Memory leaks and GC",
                "Metaprogramming (Proxy, Reflect)",
                "Concurrency patterns (Web Workers, Atomics)",
                "Performance profiling",
                "Event loop internals (micro/macrotasks)",
                "Transpilation pitfalls and runtime semantics",
                "Security hardening for JS runtimes",
                "Cross-realm and iframes quirks",
            ],
            "tech_allied": [
                "TypeScript advanced types",
                "Security hardening",
                "Testing at scale (contract tests)",
                "Module system quirks (ESM/CJS)",
                "Performance profiling",
                "Monorepos (pnpm workspaces, Nx, Turborepo)",
                "Package publishing and semantic-release",
                "API design with TS (zod/io-ts)",
                "Runtime type validation vs compile-time",
            ],
        },
    },
    "Node JS Developer": {
        "easy": {
            "tech": [
                "Node process model",
                "CommonJS vs ESM",
                "HTTP server basics",
                "NPM and scripts",
                "Environment variables",
                "Filesystem & path APIs",
                "Buffers and streams basics",
                "Events and EventEmitter",
                "Asynchronous patterns (callbacks, promises)",
                "Process signals and exit codes",
            ],
            "tech_allied": [
                "REST fundamentals",
                "Simple logging",
                "dotenv and config handling",
                "Basic testing (Jest)",
                "Error handling basics",
                "HTTP status codes and content types",
                "Package management and semver",
                "Debugging (node --inspect)",
                "Basic containerization (Dockerfile)",
            ],
        },
        "medium": {
            "tech": [
                "Event loop phases",
                "Streams and backpressure",
                "Async concurrency patterns",
                "Cluster vs worker_threads",
                "Security (helmet, rate limiting)",
                "Configuration and 12-factor",
                "Graceful shutdown and lifecycle hooks",
                "TLS/HTTPS and HTTP/2 basics",
                "Native module bindings overview",
                "Memory profiling and heap snapshots",
            ],
            "tech_allied": [
                "Databases (Mongo/Postgres) drivers",
                "Caching (Redis)",
                "Observability (logs/metrics/traces)",
                "Authentication/JWT",
                "Testing: integration/E2E",
                "API documentation (OpenAPI/Swagger)",
                "Background jobs and queues (BullMQ)",
                "Secrets management",
                "Container orchestration basics",
            ],
        },
        "hard": {
            "tech": [
                "High-throughput APIs",
                "Resilience patterns (circuit breaker, retries)",
                "Streaming architectures",
                "Native addons overview",
                "Performance profiling (clinic)",
                "Security reviews and threat modeling",
                "Load shedding and backpressure strategies",
                "Timeouts and retries at scale",
                "Distributed locks and idempotency",
                "Zero-downtime reloads and blue/green",
            ],
            "tech_allied": [
                "Horizontal scaling",
                "Zero-downtime deploys",
                "Message queues (Kafka/RabbitMQ)",
                "Distributed tracing",
                "Advanced security (OWASP ASVS)",
                "Circuit breakers and rate limits at edge",
                "API gateways and service meshes",
                "Chaos engineering and resilience testing",
                "Cost/perf trade-offs and SLOs",
            ],
        },
    },
    "Express JS Developer": {
        "easy": {
            "tech": [
                "Routing and middleware",
                "Request/response lifecycle",
                "Error handlers",
                "Static files",
                "Template engines basics",
                "Body parsing and validation basics",
                "Serving JSON and content negotiation",
                "Route params and query strings",
                "Simple auth guards (middleware order)",
                "Cookie parsing basics",
            ],
            "tech_allied": [
                "RESTful design",
                "Validation (Joi/Zod)",
                "CORS",
                "Sessions/cookies",
                "Basic security headers",
                "OpenAPI basics for Express",
                "Error logging and correlation IDs",
                "Simple rate limiting",
                "Basic pagination patterns",
            ],
        },
        "medium": {
            "tech": [
                "Advanced middleware composition",
                "Auth strategies (JWT/OAuth)",
                "File uploads and streaming",
                "Rate limiting and caching",
                "Testing routes/controllers",
                "Error propagation and logging",
                "Async error handling patterns",
                "Modular routers and versioning",
                "Template engines vs APIs trade-offs",
                "Compression and caching headers",
            ],
            "tech_allied": [
                "ORM/ODM (Prisma/Sequelize/Mongoose)",
                "API versioning",
                "OpenAPI/Swagger",
                "Monitoring/alerts",
                "CI/CD basics",
                "Migrations and schema drift",
                "Background processing (bull/agenda)",
                "SaaS integrations (Stripe/SendGrid)",
                "Observability (OpenTelemetry for Node)",
            ],
        },
        "hard": {
            "tech": [
                "Multi-tenant architectures",
                "GraphQL with Express",
                "WebSockets and real-time",
                "Security hardening",
                "Large file streaming",
                "Backpressure and timeouts",
                "API composition and BFF patterns",
                "Idempotent APIs and exactly-once semantics",
                "RBAC/ABAC at scale",
                "Protecting against SSRF/SSRF-like vectors",
            ],
            "tech_allied": [
                "Microservices gateways",
                "Service meshes",
                "Feature flags and rollouts",
                "Distributed cache",
                "Chaos testing",
                "Multi-region deployments and latency",
                "Advanced auth (OAuth device/code flows)",
                "Schema evolution and backward compatibility",
                "Blue/green vs canary deployments",
            ],
        },
    },
    "MERN Stack Developer": {
        "easy": {
            "tech": [
                "Mongo basics (CRUD, indexes)",
                "Express routing",
                "React components",
                "Node runtime basics",
                "Simple deployment",
                "Env management",
                "Basic API integration from React",
                "Collections and embedded docs vs refs",
                "Simple auth flows across stack",
                "Monorepo basics for MERN",
            ],
            "tech_allied": [
                "Data modeling basics",
                "State management intro",
                "Env/config management",
                "Unit testing",
                "Auth basics",
                "Docker Compose for local dev",
                "Simple logging across services",
                "Static asset hosting (CDN) basics",
                "Local debugging of full stack",
            ],
        },
        "medium": {
            "tech": [
                "Aggregation pipelines",
                "API design and pagination",
                "React performance patterns",
                "API consumption and caching",
                "SSR/SSG with Next.js basics",
                "State normalization and caching (RTK Query)",
                "Transactions in Mongo and consistency",
                "Index design and query plans",
                "File storage (GridFS/S3) patterns",
                "API error handling end-to-end",
            ],
            "tech_allied": [
                "DevOps (Docker Compose)",
                "Monitoring/logging stack",
                "E2E testing",
                "Scaling database reads/writes",
                "Security and secrets",
                "CI/CD for multi-service apps",
                "Feature flags and configuration",
                "Performance tracing across tiers",
                "Cost awareness (queries, bandwidth)",
            ],
        },
        "hard": {
            "tech": [
                "Sharding/replication (Mongo)",
                "Advanced caching strategies",
                "Streaming/real-time",
                "Design for high availability",
                "Complex React concurrency",
                "Cross-cutting concerns (auth, logging) across stack",
                "Read/write splitting and eventual consistency",
                "Saga/outbox patterns for workflows",
                "Backpressure across services",
                "Multi-tenant data isolation",
            ],
            "tech_allied": [
                "K8s deployments",
                "CDNs and edge caching",
                "Data migrations at scale",
                "Performance SLOs",
                "Cost optimization",
                "Observability end-to-end with traces",
                "Infrastructure as Code at scale",
                "Disaster recovery and backups",
                "Multi-region active/passive setups",
            ],
        },
    },
}


BEHAVIORAL_TOPICS: List[str] = [
    "Teamwork and collaboration",
    "Conflict resolution",
    "Problem-solving and debugging approaches",
    "Adaptability and quick learning",
    "Ownership and taking initiative",
    "Handling mistakes and learning from feedback",
    "Work ethic, time management, and prioritization",
    "Communication with technical and non-technical peers",
    "Coping with tight deadlines or pressure",
    "Receiving and incorporating feedback",
]


# Cross-cutting question archetypes to encourage variety
ARCHETYPES: Dict[str, List[str]] = {
    "tech": [
        "Concept understanding (define, explain with example)",
        "Why/How/Trade-offs",
        "Debug/fix a broken snippet or scenario",
        "Design a component/module/system",
        "Predict output/behavior (code or scenario)",
        "Optimize for performance or memory",
        "Security or edge-case analysis",
    ],
    "tech_allied": [
        "Tooling/setup decisions and rationale",
        "Testing strategy and coverage",
        "CI/CD and release process",
        "Monitoring/observability, logs/metrics/traces",
        "Security and compliance considerations",
        "Data modeling and migrations",
    ],
    "behavioral": [
        "STAR: situation-task-action-result",
        "Teamwork & collaboration specifics",
        "Conflict resolution specifics",
        "Ownership and initiative",
        "Handling mistakes & feedback",
        "Communication with non-technical peers",
        "Working under pressure/time constraints",
    ],
}


DEPTH_GUIDELINES: Dict[str, str] = {
    "easy": "Test fundamentals and terminology; include a small applied example but keep scope narrow.",
    "medium": "Cover implementation details and trade-offs; include constraints, alternatives, and simple edge cases.",
    "hard": "Address scaling, performance, failure modes, and security; require nuanced trade-offs and multiple constraints.",
}


def get_topics_for(role: str, difficulty: str) -> Dict[str, List[str]]:
    diff = (difficulty or "medium").lower()
    if diff not in ("easy", "medium", "hard"):
        diff = "medium"
    role_key = role if role in SYLLABUS else derive_role(role)
    buckets = SYLLABUS.get(role_key) or SYLLABUS["JavaScript Developer"]
    level = buckets.get(diff) or buckets["medium"]
    return {
        "tech": list(level.get("tech", [])),
        "tech_allied": list(level.get("tech_allied", [])),
        "behavioral": list(BEHAVIORAL_TOPICS),
        "archetypes": ARCHETYPES.get("tech", []) + ARCHETYPES.get("tech_allied", []) + ARCHETYPES.get("behavioral", []),
        "depth_guidelines": [DEPTH_GUIDELINES.get(diff, DEPTH_GUIDELINES["medium"])],
    }


def compute_category_ratio(years_experience: float | None, has_resume_text: bool, has_skills: bool) -> Dict[str, int]:
    """
    Derive the 5-question split across categories:
    - Normal: 2 tech, 2 tech_allied, 1 behavioral
    - If no job experience: 3 tech, 1 tech_allied, 1 behavioral
    - If resume data exists but skills are thin: 3 tech, 0 tech_allied, 2 behavioral

    Note: This mapping follows the product note "Effects of supplement" and can be tuned easily.
    """
    if years_experience is None or years_experience < 1:
        return {"tech": 3, "tech_allied": 1, "behavioral": 1}
    if has_resume_text and not has_skills:
        return {"tech": 3, "tech_allied": 0, "behavioral": 2}
    return {"tech": 2, "tech_allied": 2, "behavioral": 1}


def tech_allied_from_resume(
    resume_text: str | None,
    skills: List[str] | None,
    fallback: List[str] | None = None,
) -> List[str]:
    """
    Build tech_allied topics primarily from resume content when available, else fallback.
    - Uses explicit skills (if present) as first-class allied topics.
    - Augments with lightweight keyword scan from resume text for common tools/platforms.
    """
    topics: List[str] = []
    seen: set[str] = set()

    def add(item: str):
        key = item.strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            topics.append(key)

    # 1) Add declared skills from profile extraction
    for s in (skills or []):
        add(str(s))

    # 2) Derive from resume text by scanning for common tech keywords
    corpus = (resume_text or "").lower()
    if corpus:
        keyword_bank = [
            # Frontend/UI
            "react", "redux", "next.js", "nextjs", "vite", "webpack", "babel", "typescript", "tailwind", "mui", "ant design", "sass", "styled-components", "rtl", "jest", "cypress", "playwright",
            # Backend/Node
            "node", "express", "nestjs", "koa", "fastify", "graphql", "rest", "websocket", "socket.io",
            # Databases/Cache/Queues
            "mongodb", "mongoose", "postgres", "mysql", "redis", "kafka", "rabbitmq",
            # DevOps/Cloud
            "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "terraform", "github actions", "ci/cd", "jenkins",
            # Security/Auth
            "oauth", "oauth2", "oidc", "jwt", "helmet", "cors",
            # Observability
            "prometheus", "grafana", "opentelemetry", "sentry",
        ]
        for kw in keyword_bank:
            if kw in corpus:
                add(kw)

    if not topics and fallback:
        # Default back to role syllabus allied topics if resume gave nothing
        for f in fallback:
            add(f)

    return topics

