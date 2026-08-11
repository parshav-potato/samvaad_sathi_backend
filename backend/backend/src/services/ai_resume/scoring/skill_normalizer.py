import re
from typing import Set

class SkillNormalizer:
    """
    Production-grade Skill Normalizer.
    Converts diverse text representations and variations of technologies 
    into unified canonical tokens for 100% accurate set intersection matching.
    """

    def __init__(self):
        # Clean up punctuation except technical essentials like +, #, .
        self.cleanup_pattern = re.compile(r'[^\w\s\-\#\.\+]')
        
        # Comprehensive canonical mapping database (Expandable to 250+ entries easily)
        self.alias_matrix = {
            # --- API & Protocols ---
            "rest": "rest", "rest api": "rest", "rest apis": "rest",
            "restful api": "rest", "restful apis": "rest", "restful": "rest",
            "restful web services": "rest", "graphql": "graphql", "soap": "soap",
            "websockets": "websockets", "websocket": "websockets", "ws": "websockets",

            # --- Languages ---
            "javascript": "javascript", "js": "javascript", "ecmascript": "javascript", "es6": "javascript",
            "typescript": "typescript", "ts": "typescript",
            "python": "python", "py": "python",
            "java": "java",
            "c++": "cpp", "cpp": "cpp", "cplusplus": "cpp",
            "c#": "csharp", "csharp": "csharp",
            "golang": "go", "go": "go",
            "ruby": "ruby", "rust": "rust", "php": "php",

            # --- Frontend Frameworks & Libraries ---
            "react": "react", "reactjs": "react", "react.js": "react", "react js": "react",
            "nextjs": "nextjs", "next.js": "nextjs", "next js": "nextjs", "next": "nextjs",
            "vue": "vue", "vuejs": "vue", "vue.js": "vue", "vue js": "vue",
            "angular": "angular", "angularjs": "angular", "angular.js": "angular", "angular js": "angular",
            "svelte": "svelte", "sveltekit": "svelte",
            "tailwind": "tailwindcss", "tailwind css": "tailwindcss", "tailwindcss": "tailwindcss",
            "bootstrap": "bootstrap", "bootstrap5": "bootstrap",
            "html": "html", "html5": "html",
            "css": "css", "css3": "css", "sass": "sass", "scss": "sass",

            # --- Backend Frameworks ---
            "nodejs": "nodejs", "node": "nodejs", "node.js": "nodejs", "node js": "nodejs",
            "express": "express", "expressjs": "express", "express.js": "express", "express js": "express",
            "django": "django",
            "fastapi": "fastapi", "fast api": "fastapi",
            "flask": "flask",
            "spring": "springboot", "springboot": "springboot", "spring boot": "springboot",

            # --- Databases ---
            "postgres": "postgresql", "postgresql": "postgresql", "postgres db": "postgresql",
            "mongo": "mongodb", "mongodb": "mongodb", "mongo db": "mongodb",
            "mysql": "mysql", "my sql": "mysql",
            "sqlite": "sqlite", "sqlite3": "sqlite",
            "redis": "redis",
            "oracle": "oracle", "oracledb": "oracle",
            "dynamodb": "dynamodb", "dynamo db": "dynamodb",
            "cassandra": "cassandra",

            # --- Cloud & DevOps ---
            "aws": "aws", "amazon web services": "aws",
            "gcp": "gcp", "google cloud": "gcp", "google cloud platform": "gcp",
            "azure": "azure", "microsoft azure": "azure",
            "docker": "docker", "containerization": "docker", "containers": "docker",
            "kubernetes": "kubernetes", "k8s": "kubernetes",
            "ci/cd": "cicd", "cicd": "cicd", "continuous integration": "cicd", "ci cd": "cicd",
            "git": "git", "github": "github", "gitlab": "gitlab", "bitbucket": "bitbucket",
            "jenkins": "jenkins", "terraform": "terraform", "ansible": "terraform",

            # --- Design & Tools ---
            "figma": "figma", "adobe xd": "adobexd", "postman": "postman",

            # --- AI / ML / Data ---
            "openai": "openai", "langchain": "langchain", "tensorflow": "tensorflow",
            "pytorch": "pytorch", "pandas": "pandas", "numpy": "numpy"
        }

        # Human-readable presentation mapping for clean React Dashboard display cards
        self.display_names = {
            "rest": "REST APIs",
            "websockets": "WebSockets",
            "graphql": "GraphQL",
            "soap": "SOAP",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "python": "Python",
            "java": "Java",
            "cpp": "C++",
            "csharp": "C#",
            "go": "Go",
            "react": "React.js",
            "nextjs": "Next.js",
            "vue": "Vue.js",
            "angular": "Angular",
            "svelte": "Svelte",
            "tailwindcss": "Tailwind CSS",
            "bootstrap": "Bootstrap",
            "html": "HTML5",
            "css": "CSS3",
            "sass": "Sass",
            "nodejs": "Node.js",
            "express": "Express.js",
            "django": "Django",
            "fastapi": "FastAPI",
            "flask": "Flask",
            "springboot": "Spring Boot",
            "postgresql": "PostgreSQL",
            "mongodb": "MongoDB",
            "mysql": "MySQL",
            "sqlite": "SQLite",
            "redis": "Redis",
            "aws": "AWS",
            "gcp": "GCP",
            "azure": "Azure",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "cicd": "CI/CD",
            "git": "Git",
            "github": "GitHub",
            "figma": "Figma",
            "postman": "Postman",
            "openai": "OpenAI",
            "langchain": "LangChain"
        }
    def normalize(self, raw_string: str) -> str:
        """Normalizes an individual token or short phrase phrase into its canonical tech ID."""
        if not raw_string:
            return ""
        
        # Structural sanitation tracking loop
        clean_target = raw_string.strip().lower()
        
        # Direct structural translation match check
        if clean_target in self.alias_matrix:
            return self.alias_matrix[clean_target]
            
        # Fallback mutation step: strip spaces, dots, dashes, and trailing 'js' tags
        mutated = clean_target.replace(" ", "").replace(".", "").replace("-", "").replace("js", "")
        if mutated in self.alias_matrix:
            return self.alias_matrix[mutated]
            
        return clean_target

    def get_display_name(self, canonical_token: str) -> str:
        """Converts internal raw tokens back to elegant UI display names."""
        return self.display_names.get(canonical_token, canonical_token.capitalize())