import re


EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".md": "markdown",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
}


def detect_language(diff: str) -> str:
    filenames = re.findall(r"--- (.+?) ---", diff)

    for filename in filenames:
        filename = filename.strip()
        for ext, language in EXTENSION_MAP.items():
            if filename.endswith(ext):
                print(f"  Detected {language} from {filename}")
                return language

    # fallback — look for code patterns in the diff
    if "def " in diff and "import " in diff:
        return "python"
    if "function " in diff or "const " in diff or "let " in diff:
        return "javascript"
    if "public class" in diff or "void " in diff:
        return "java"
    if "func " in diff and "package " in diff:
        return "go"

    return "unknown"