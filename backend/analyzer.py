import os
import re
import shutil
import stat
import tempfile
import subprocess
from statistics import mean
from bs4 import BeautifulSoup
from git import Repo
from github import Github  # pip install PyGithub
import random

SUPPORTED_CODE_EXTS = ('.py', '.js', '.java', '.cpp', '.c', '.ts')

# -------------------------------------------------------------------
# ✨ Speed-optimised sampling version
# -------------------------------------------------------------------
import random                     #  <-- make sure this is imported once.

# Tweak these three knobs to trade speed vs. accuracy.
MAX_REPOS            = 10         # analyse at most N repos per user
MAX_FILES_PER_REPO   = 10         # sample at most N files in each repo
CLONE_DEPTH          = 1          # shallow-clone (depth=1) is much faster

def _sample_source_files(root_dir: str) -> list[str]:
    """
    Collect all files in the repo tree that match SUPPORTED_CODE_EXTS,
    then pick at most MAX_FILES_PER_REPO of them at random.
    """
    candidates = []
    for r, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith(SUPPORTED_CODE_EXTS):
                candidates.append(os.path.join(r, f))
    return random.sample(candidates, min(len(candidates), MAX_FILES_PER_REPO))

def analyze_user_code_quality(username: str, github_api):
    """
    FAST version:
      • shallow-clone each repo  (depth=1)
      • sample up to MAX_FILES_PER_REPO files
      • stop after MAX_REPOS repos
    Returns overall average readability / style score.
    """
    results = []
    user_repos = github_api.get_user(username).get_repos()

    for repo in user_repos:
        if repo.fork:
            continue
        if len(results) >= MAX_REPOS:
            break                                 # early-exit for speed

        try:
            tmp = tempfile.mkdtemp()
            Repo.clone_from(repo.clone_url, tmp, depth=CLONE_DEPTH)

            sampled = _sample_source_files(tmp)
            if not sampled:                       # no supported files
                shutil.rmtree(tmp, onerror=on_rm_error)
                continue

            scores = [score_code_readability(fp)["score"] for fp in sampled]
            avg    = round(mean(scores), 2)
            results.append(
                {"repo": repo.name,
                 "sampled_files": len(sampled),
                 "avg_quality_score": avg}
            )

        except Exception as err:
            print(f"❌ {repo.name}: {err}")

        finally:
            shutil.rmtree(tmp, onerror=on_rm_error)

    overall = round(mean(r["avg_quality_score"] for r in results), 2) if results else 0
    return {
        "username": username,
        "average_code_quality": overall,
        "repo_scores": results,
        "repos_analysed": len(results),
    }
# -------------------------------------------------------------------


def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)

def run_lizard_on_folder(folder_path):
    try:
        result = subprocess.run(
            ['lizard', folder_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return result.stdout
    except Exception as e:
        return f"Error running Lizard: {e}"

def extract_avg_ccn_from_lizard_output(output):
    match = re.search(r'AvgCCN:\s*([\d.]+)', output)
    if match:
        avg_ccn = float(match.group(1))
        return max(0, min(100, 100 - (avg_ccn - 1) * 12.5))
    return 50

def score_html_quality(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    soup = BeautifulSoup(content, 'html.parser')
    lines = content.splitlines()

    semantic_tags = ['article', 'section', 'main', 'nav', 'header', 'footer', 'aside', 'figure']
    semantic_count = sum(len(soup.find_all(tag)) for tag in semantic_tags)
    semantic_score = min(semantic_count, 5) / 5 * 25

    indent_types = set()
    for line in lines:
        if line.startswith(" "): indent_types.add("space")
        elif line.startswith("\t"): indent_types.add("tab")
    indent_score = 20 if len(indent_types) <= 1 else 10

    long_lines = sum(1 for line in lines if len(line) > 120)
    line_length_score = 15 if long_lines == 0 else max(0, 15 - long_lines)

    img_tags = soup.find_all('img')
    img_with_alt = [img for img in img_tags if img.get('alt')]
    alt_score = (len(img_with_alt) / max(len(img_tags), 1)) * 10 if img_tags else 10

    inline_styles = sum(1 for tag in soup.find_all(True) if tag.get("style"))
    style_tags = len(soup.find_all('style'))
    inline_penalty = min((inline_styles + style_tags), 5) / 5 * 10
    inline_score = max(0, 10 - inline_penalty)

    open_tags = len(re.findall(r'<[^/!][^>]*?>', content))
    close_tags = len(re.findall(r'</[^>]+>', content))
    balance_score = 20 if abs(open_tags - close_tags) <= 3 else 10

    total_score = round(semantic_score + indent_score + line_length_score +
                        alt_score + inline_score + balance_score, 2)
    return {"score": total_score}

def score_css_quality(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    lines = content.splitlines()
    class_selectors = len(re.findall(r'\.[a-zA-Z0-9_-]+', content))
    id_selectors = len(re.findall(r'#[a-zA-Z0-9_-]+', content))
    modularity_score = min(25, 25 - min(id_selectors, 10))

    properties = re.findall(r'([a-zA-Z-]+)\s*:', content)
    duplicate_props = len(properties) - len(set(properties))
    duplication_penalty = min(duplicate_props, 5) * 2
    reuse_score = max(0, 20 - duplication_penalty)

    rule_count = len(re.findall(r'{', content))
    rule_score = 15 if 3 <= rule_count <= 200 else 5

    long_lines = sum(1 for line in lines if len(line) > 120)
    format_score = max(0, 20 - long_lines)

    comment_lines = len(re.findall(r'/\*.*?\*/', content, re.DOTALL))
    comment_score = min(comment_lines, 5) / 5 * 10

    important_usage = len(re.findall(r'!important', content))
    important_score = max(0, 10 - min(important_usage, 5) * 2)

    total_score = round(modularity_score + reuse_score + rule_score +
                        format_score + comment_score + important_score, 2)
    return {"score": total_score}

def analyze_repo_githired(username, repo_name, token=None):
    github_url = (
        f"https://{token}@github.com/{username}/{repo_name}.git"
        if token else f"https://github.com/{username}/{repo_name}.git"
    )

    temp_dir = tempfile.mkdtemp()
    try:
        Repo.clone_from(github_url, temp_dir)

        html_scores = []
        css_scores = []
        lizard_scores = []
        file_count = 0
        folder_count = 0

        for root, dirs, files in os.walk(temp_dir):
            folder_count += 1
            file_paths = [os.path.join(root, f) for f in files]
            file_count += len(file_paths)

            if any(f.endswith(SUPPORTED_CODE_EXTS) for f in files):
                lizard_output = run_lizard_on_folder(root)
                lizard_score = extract_avg_ccn_from_lizard_output(lizard_output)
                lizard_scores.append(lizard_score)

            for file_path in file_paths:
                if file_path.endswith(".html"):
                    result = score_html_quality(file_path)
                    if "score" in result:
                        html_scores.append(result["score"])
                elif file_path.endswith(".css"):
                    result = score_css_quality(file_path)
                    if "score" in result:
                        css_scores.append(result["score"])

        has_code = bool(lizard_scores)
        has_html = bool(html_scores)
        has_css = bool(css_scores)

        if not (has_code or has_html or has_css):
            return {
                "repo": repo_name,
                "overall_score": 15.0,
                "note": "No supported files found. Structure bonus only."
            }

        avg_lizard = mean(lizard_scores) if has_code else 0
        avg_html = mean(html_scores) if has_html else 0
        avg_css = mean(css_scores) if has_css else 0
        structure_bonus = min(15, (file_count + folder_count) / 10)

        weights = {
            "lizard": 0,
            "html": 0,
            "css": 0,
            "structure": 0.15
        }

        if has_code and has_html and has_css:
            weights.update(lizard=0.35, html=0.25, css=0.25)
        elif has_code and has_html:
            weights.update(lizard=0.5, html=0.35)
        elif has_code and has_css:
            weights.update(lizard=0.5, css=0.35)
        elif has_code:
            weights.update(lizard=0.85)
        elif has_html and has_css:
            weights.update(html=0.45, css=0.4)
        elif has_html:
            weights.update(html=0.85)
        elif has_css:
            weights.update(css=0.85)

        overall_score = round(
            avg_lizard * weights["lizard"] +
            avg_html * weights["html"] +
            avg_css * weights["css"] +
            structure_bonus, 2
        )

        return {
            "repo": repo_name,
            "overall_score": overall_score,
            "avg_lizard_score": round(avg_lizard, 2),
            "avg_html_score": round(avg_html, 2),
            "avg_css_score": round(avg_css, 2),
            "structure_bonus": round(structure_bonus, 2),
            "file_count": file_count,
            "folder_count": folder_count,
            "weights_used": weights
        }

    finally:
        shutil.rmtree(temp_dir, onerror=on_rm_error)

def analyze_user_repos(username, token=None):
    g = Github(token) if token else Github()
    user = g.get_user(username)
    repos = user.get_repos(per_page=100)

    repo_scores = []
    detailed_results = []

    for repo in repos:
        if repo.fork:
            continue
        try:
            print(f"🔍 Analyzing {repo.name}...")
            score = analyze_repo_githired(username, repo.name, token=token)
            repo_scores.append(score["overall_score"])
            detailed_results.append({
                "repo": repo.name,
                "score": round(score["overall_score"], 2)
            })
        except Exception as e:
            print(f"❌ Failed to analyze {repo.name}: {e}")

    return {
        "username": username,
        "average_score": round(mean(repo_scores), 2) if repo_scores else 0,
        "repo_scores": detailed_results
    }

    return {
        "username": username,
        "average_score": round(mean(repo_scores), 2) if repo_scores else 0,
        "repo_scores": detailed_results
    }



COMMENT_SYNTAX = {
    ".py":     {"line": "#"},
    ".js":     {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".ts":     {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".cpp":    {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".c":      {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".java":   {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".cs":     {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".rb":     {"line": "#"},
    ".go":     {"line": "//", "block_start": "/*", "block_end": "*/"},
    ".html":   {"block_start": "<!--", "block_end": "-->"},
    ".xml":    {"block_start": "<!--", "block_end": "-->"}
}

SUPPORTED_CODE_EXTS = (
    ".py", ".js", ".ts", ".cpp", ".c", ".java", ".cs", ".rb", ".go", ".html", ".xml"
)

def detect_comment_lines(lines, ext):
    syntax = COMMENT_SYNTAX.get(ext, {})
    comment_lines = 0
    in_block = False

    for line in lines:
        stripped = line.strip()
        if "line" in syntax and stripped.startswith(syntax["line"]):
            comment_lines += 1
        elif "block_start" in syntax and "block_end" in syntax:
            if in_block or stripped.startswith(syntax["block_start"]):
                comment_lines += 1
                if stripped.endswith(syntax["block_end"]) or syntax["block_end"] in stripped:
                    in_block = False
                else:
                    in_block = True

    return comment_lines

def score_code_readability(file_path):
    ext = os.path.splitext(file_path)[1]
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": str(e)}

    if not lines:
        return {"score": 0}

    total_lines = len(lines)
    comment_lines = detect_comment_lines(lines, ext)
    blank_lines = sum(1 for line in lines if line.strip() == "")
    long_lines = sum(1 for line in lines if len(line) > 100)

    # Indentation consistency
    space_indent = sum(1 for line in lines if line.startswith("    "))
    tab_indent = sum(1 for line in lines if line.startswith("\t"))
    mixed_indent = 0
    for line in lines:
        if "\t" in line[:8] and " " in line[:8]:
            mixed_indent += 1

    indent_score = 15 if space_indent == 0 or tab_indent == 0 else 5
    indent_score -= mixed_indent * 0.5
    indent_score = max(0, min(15, indent_score))

    comment_ratio = comment_lines / total_lines
    comment_score = 25 if comment_ratio > 0.2 else 15 if comment_ratio > 0.1 else 5

    structure_score = max(0, 10 - long_lines)
    blank_line_score = min(blank_lines / total_lines * 10, 10)

    total_score = round(indent_score + comment_score + structure_score + blank_line_score, 2)

    return {
        "score": total_score,
        "comment_score": round(comment_score, 2),
        "indent_score": round(indent_score, 2),
        "structure_score": round(structure_score, 2),
        "blank_line_score": round(blank_line_score, 2),
        "comment_ratio": round(comment_ratio, 2)
    }

