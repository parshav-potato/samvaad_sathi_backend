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
                "useState/useEffect fundamentals",
                "Component composition",
                "Basic event handling",
            ],
            "tech_allied": [
                "ES6+ features (let/const, arrow functions)",
                "NPM/Yarn basics",
                "CSS Modules vs styled-components",
                "Simple bundling (Vite/Webpack basics)",
                "Basic API calls with fetch/axios",
            ],
        },
        "medium": {
            "tech": [
                "Context API vs prop drilling",
                "React reconciliation and keys",
                "Memoization (React.memo, useMemo, useCallback)",
                "Forms and controlled components",
                "Error boundaries",
            ],
            "tech_allied": [
                "Routing (React Router)",
                "State mgmt (Redux/RTK, Zustand)",
                "Performance optimizations",
                "Testing (Jest, React Testing Library)",
                "Accessibility (ARIA, keyboard nav)",
            ],
        },
        "hard": {
            "tech": [
                "Concurrent features (useTransition, Suspense)",
                "Server Components trade-offs",
                "SSR/SSG hydration nuances",
                "Custom hooks patterns and pitfalls",
                "Rendering performance profiling",
            ],
            "tech_allied": [
                "Microfrontends",
                "Code splitting strategies",
                "Security (XSS, CSP in SPAs)",
                "Internationalization at scale",
                "Design systems and theming architecture",
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
                "Form basics and validation",
            ],
            "tech_allied": [
                "Accessibility basics (labels, roles)",
                "Color contrast and typography",
                "Image optimization basics",
                "Browser DevTools essentials",
                "Basic performance metrics (LCP/FID/CLS)",
            ],
        },
        "medium": {
            "tech": [
                "Advanced CSS (Grid areas, container queries)",
                "Component libraries (MUI/Ant/Tailwind)",
                "State and events in complex UIs",
                "Client-side routing and SPA patterns",
                "Web APIs (IntersectionObserver, Storage)",
            ],
            "tech_allied": [
                "WCAG 2.x conformance",
                "Design tokens and theming",
                "Build tooling (Vite/Webpack/Rollup)",
                "Unit/E2E testing (RTL, Playwright)",
                "Performance audits (Lighthouse)",
            ],
        },
        "hard": {
            "tech": [
                "Rendering pipelines and paint optimizations",
                "Virtualization for large lists",
                "Complex form architectures",
                "Statecharts/XState for UI flows",
                "Canvas/SVG advanced rendering",
            ],
            "tech_allied": [
                "Advanced a11y (focus traps, screen readers)",
                "Internationalization at scale",
                "Design systems governance",
                "Performance budgets and regressions",
                "Security (clickjacking, CSP)",
            ],
        },
    },
    "JavaScript Developer": {
        "easy": {
            "tech": [
                "Types and coercion",
                "Scope and closures",
                "Array/object methods",
                "Promises basics",
                "Modules and imports",
            ],
            "tech_allied": [
                "NPM scripts",
                "ESLint/Prettier",
                "Debugging with DevTools",
                "Basic testing (Jest)",
                "HTTP basics and fetch",
            ],
        },
        "medium": {
            "tech": [
                "Event loop and task queue",
                "Async/await patterns",
                "Error handling strategies",
                "Functional programming patterns",
                "Performance (debounce/throttle)",
            ],
            "tech_allied": [
                "Bundlers and tree shaking",
                "TypeScript fundamentals",
                "Testing pyramids",
                "Security (XSS, CSRF basics)",
                "Node.js basics",
            ],
        },
        "hard": {
            "tech": [
                "V8 internals (hidden classes, ICs)",
                "Streaming and backpressure",
                "Memory leaks and GC",
                "Metaprogramming (Proxy, Reflect)",
                "Concurrency patterns (Web Workers)",
            ],
            "tech_allied": [
                "TypeScript advanced types",
                "Security hardening",
                "Testing at scale (contract tests)",
                "Module system quirks (ESM/CJS)",
                "Performance profiling",
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
            ],
            "tech_allied": [
                "REST fundamentals",
                "Simple logging",
                "dotenv and config handling",
                "Basic testing (Jest)",
                "Error handling basics",
            ],
        },
        "medium": {
            "tech": [
                "Event loop phases",
                "Streams and backpressure",
                "Async concurrency patterns",
                "Cluster vs worker_threads",
                "Security (helmet, rate limiting)",
            ],
            "tech_allied": [
                "Databases (Mongo/Postgres) drivers",
                "Caching (Redis)",
                "Observability (logs/metrics/traces)",
                "Authentication/JWT",
                "Testing: integration/E2E",
            ],
        },
        "hard": {
            "tech": [
                "High-throughput APIs",
                "Resilience patterns (circuit breaker)",
                "Streaming architectures",
                "Native addons overview",
                "Performance profiling (clinic)",
            ],
            "tech_allied": [
                "Horizontal scaling",
                "Zero-downtime deploys",
                "Message queues (Kafka/RabbitMQ)",
                "Distributed tracing",
                "Advanced security (OWASP ASVS)",
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
            ],
            "tech_allied": [
                "RESTful design",
                "Validation (Joi/Zod)",
                "CORS",
                "Sessions/cookies",
                "Basic security headers",
            ],
        },
        "medium": {
            "tech": [
                "Advanced middleware composition",
                "Auth strategies (JWT/OAuth)",
                "File uploads and streaming",
                "Rate limiting and caching",
                "Testing routes/controllers",
            ],
            "tech_allied": [
                "ORM/ODM (Prisma/Sequelize/Mongoose)",
                "API versioning",
                "OpenAPI/Swagger",
                "Monitoring/alerts",
                "CI/CD basics",
            ],
        },
        "hard": {
            "tech": [
                "Multi-tenant architectures",
                "GraphQL with Express",
                "WebSockets and real-time",
                "Security hardening",
                "Large file streaming",
            ],
            "tech_allied": [
                "Microservices gateways",
                "Service meshes",
                "Feature flags and rollouts",
                "Distributed cache",
                "Chaos testing",
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
            ],
            "tech_allied": [
                "Data modeling basics",
                "State management intro",
                "Env/config management",
                "Unit testing",
                "Auth basics",
            ],
        },
        "medium": {
            "tech": [
                "Aggregation pipelines",
                "API design and pagination",
                "React performance patterns",
                "API consumption and caching",
                "SSR/SSG with Next.js basics",
            ],
            "tech_allied": [
                "DevOps (Docker Compose)",
                "Monitoring/logging stack",
                "E2E testing",
                "Scaling database reads/writes",
                "Security and secrets",
            ],
        },
        "hard": {
            "tech": [
                "Sharding/replication (Mongo)",
                "Advanced caching strategies",
                "Streaming/real-time"
                ,"Design for high availability",
                "Complex React concurrency",
            ],
            "tech_allied": [
                "K8s deployments",
                "CDNs and edge caching",
                "Data migrations at scale",
                "Performance SLOs",
                "Cost optimization",
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

