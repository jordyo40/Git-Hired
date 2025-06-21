from flask import Flask, request, jsonify
import requests
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import re
import base64
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)




app = Flask(__name__)

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'}
TOPIC_HEADER = {
    **HEADERS,
    "Accept": "application/vnd.github.mercy-preview+json"
}


@app.get("/email/<string:username>")
def getEmail(username):
    try:
        repos_url = f"https://api.github.com/users/{username}/repos"
        repos = requests.get(repos_url, headers=HEADERS).json()

        if isinstance(repos, dict) and repos.get('message'):
            return None

        if not repos:
            return None
        repo_name = repos[0]['name']
        commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
        commits = requests.get(commits_url, headers=HEADERS).json()

        for commit in commits:
            email= commit['commit']['author']['email']
            if email:
                return {"email":email}
            
    except Exception as e:
        return {"message":e}
@app.post("/find-matching-users")
def find_matching_users():
    data = request.get_json()
    required_skills = [skill.lower() for skill in data.get("required_skills", [])]
    languages = data.get("languages", [])
    min_followers = data.get("min_followers", 0)
    min_stars = data.get("min_stars", 0)

    matched_usernames = set()

    for lang in languages:
        skill_query = "+".join(required_skills) if required_skills else ""
        query = f"{skill_query}+language:{lang}+stars:>={min_stars}"
        url = f"{GITHUB_API_URL}/search/repositories?q={query}&sort=stars&order=desc&per_page=50"

        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            repos = response.json().get("items", [])

            for repo in repos:
                username = repo["owner"]["login"]
                if username in matched_usernames:
                    continue

                user_data = requests.get(repo["owner"]["url"], headers=HEADERS).json()
                if user_data.get("type") != "User":
                    continue
                if user_data.get("followers", 0) < min_followers:
                    continue

                # Check skill match in name/description (case insensitive)
                text = f"{repo.get('name', '')} {repo.get('description', '')}".lower()
                if any(skill in text for skill in required_skills):
                    matched_usernames.add(username)

        except Exception as e:
            print(f"Error processing {lang}: {e}")

    return jsonify({"matched_username": list(matched_usernames)})

@app.get("/get-info/<string:username>")
def getInfo(username):
    try:
        user_url = f"{GITHUB_API_URL}/users/{username}"
        user_resp = requests.get(user_url, headers=HEADERS).json()

        if "message" in user_resp:
            return jsonify({"error": "User not found"}), 404

        repos_url = f"{user_url}/repos?per_page=100"
        repos = requests.get(repos_url, headers=HEADERS).json()

        if not isinstance(repos, list):
            return jsonify({"error": "Failed to fetch repositories"}), 500

        language_usage = {}
        total_stars = 0
        total_commits = 0
        all_topics = set()

        for repo in repos:
            # Language count
            lang = repo.get("language")
            if lang:
                language_usage[lang] = language_usage.get(lang, 0) + 1

            # Star count
            total_stars += repo.get("stargazers_count", 0)

            # Fetch topics
            topics_url = f"{repo['url']}/topics"
            topics_resp = requests.get(topics_url, headers=TOPIC_HEADER).json()
            topics = topics_resp.get("names", [])
            all_topics.update(topics)

            # Commit count per repo (limited for speed)
            commits_url = repo["commits_url"].replace("{/sha}", "")
            commit_resp = requests.get(commits_url, headers=HEADERS).json()
            if isinstance(commit_resp, list):
                total_commits += len(commit_resp)

        return jsonify({
            "username": username,
            "followers": user_resp.get("followers", 0),
            "public_repos": user_resp.get("public_repos", 0),
            "top_languages": sorted(language_usage, key=language_usage.get, reverse=True),
            "total_stars": total_stars,
            "average_stars_per_repo": round(total_stars / len(repos), 2) if repos else 0,
            "total_commit_samples": total_commits,
            "inferred_skills_from_topics": list(all_topics)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Enhanced skill detection patterns with more comprehensive coverage
SKILL_PATTERNS = {
    'frontend': [
        'react', 'vue', 'angular', 'svelte', 'frontend', 'front-end', 'html', 'css', 'javascript', 'typescript', 
        'sass', 'scss', 'less', 'next.js', 'nuxt', 'gatsby', 'webpack', 'vite', 'tailwind', 'bootstrap', 
        'material-ui', 'mui', 'chakra', 'styled-components', 'emotion', 'redux', 'mobx', 'zustand', 
        'jquery', 'backbone', 'ember', 'knockout', 'polymer', 'lit', 'stencil', 'alpine.js'
    ],
    'backend': [
        'django', 'flask', 'fastapi', 'express', 'koa', 'hapi', 'nestjs', 'spring', 'spring-boot', 
        'backend', 'back-end', 'api', 'server', 'node.js', 'nodejs', 'laravel', 'symfony', 'codeigniter', 
        'rails', 'ruby-on-rails', 'sinatra', 'asp.net', 'dotnet', '.net', 'core', 'mvc', 'web-api',
        'go', 'gin', 'echo', 'fiber', 'rust', 'actix', 'rocket', 'warp', 'axum', 'php', 'slim'
    ],
    'mobile': [
        'android', 'ios', 'react-native', 'flutter', 'swift', 'kotlin', 'mobile', 'xamarin', 
        'ionic', 'cordova', 'phonegap', 'expo', 'nativescript', 'unity', 'unreal', 'java-android',
        'objective-c', 'swiftui', 'jetpack-compose', 'flutter-dart', 'capacitor'
    ],
    'ml': [
        'machine-learning', 'ml', 'tensorflow', 'pytorch', 'sklearn', 'scikit-learn', 'ai', 'artificial-intelligence',
        'neural', 'deep-learning', 'data-science', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
        'jupyter', 'notebook', 'keras', 'opencv', 'computer-vision', 'nlp', 'natural-language-processing',
        'transformers', 'bert', 'gpt', 'llm', 'langchain', 'huggingface', 'xgboost', 'lightgbm', 'catboost'
    ],
    'devops': [
        'docker', 'kubernetes', 'k8s', 'aws', 'amazon-web-services', 'gcp', 'google-cloud', 'azure', 
        'microsoft-azure', 'terraform', 'ansible', 'jenkins', 'ci/cd', 'github-actions', 'gitlab-ci',
        'circle-ci', 'travis-ci', 'helm', 'istio', 'prometheus', 'grafana', 'elk', 'elasticsearch',
        'logstash', 'kibana', 'nginx', 'apache', 'load-balancer', 'microservices', 'serverless'
    ],
    'database': [
        'mongodb', 'postgresql', 'postgres', 'mysql', 'sqlite', 'redis', 'elasticsearch', 'database', 
        'sql', 'nosql', 'cassandra', 'dynamodb', 'firebase', 'firestore', 'supabase', 'planetscale',
        'prisma', 'typeorm', 'sequelize', 'mongoose', 'knex', 'drizzle', 'clickhouse', 'snowflake'
    ],
    'testing': [
        'jest', 'mocha', 'chai', 'cypress', 'selenium', 'playwright', 'puppeteer', 'testing', 'unit-test',
        'integration-test', 'e2e', 'tdd', 'bdd', 'pytest', 'unittest', 'rspec', 'jasmine', 'karma'
    ],
    'tools': [
        'git', 'github', 'gitlab', 'bitbucket', 'vscode', 'intellij', 'vim', 'emacs', 'sublime',
        'postman', 'insomnia', 'figma', 'sketch', 'adobe', 'photoshop', 'illustrator'
    ]
}

def extract_skills_from_text(text):
    """Enhanced skill extraction with better pattern matching"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = []
    
    # Direct keyword matching
    for category, keywords in SKILL_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_skills.append(keyword)
    
    # Additional pattern matching for common variations
    import re
    
    # Framework patterns
    framework_patterns = [
        r'\b(react|vue|angular|svelte)\b',
        r'\b(django|flask|fastapi|express)\b', 
        r'\b(tensorflow|pytorch|keras)\b',
        r'\b(docker|kubernetes|k8s)\b',
        r'\b(mongodb|postgresql|mysql|redis)\b'
    ]
    
    for pattern in framework_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        found_skills.extend(matches)
    
    # Remove duplicates and return
    return list(set(found_skills))
SKILL_PATTERNS = {
    'frontend': [
        'react', 'vue', 'angular', 'svelte', 'frontend', 'front-end', 'html', 'css', 'javascript', 'typescript', 
        'sass', 'scss', 'less', 'next.js', 'nuxt', 'gatsby', 'webpack', 'vite', 'tailwind', 'bootstrap', 
        'material-ui', 'mui', 'chakra', 'styled-components', 'emotion', 'redux', 'mobx', 'zustand', 
        'jquery', 'backbone', 'ember', 'knockout', 'polymer', 'lit', 'stencil', 'alpine.js'
    ],
    'backend': [
        'django', 'flask', 'fastapi', 'express', 'koa', 'hapi', 'nestjs', 'spring', 'spring-boot', 
        'backend', 'back-end', 'api', 'server', 'node.js', 'nodejs', 'laravel', 'symfony', 'codeigniter', 
        'rails', 'ruby-on-rails', 'sinatra', 'asp.net', 'dotnet', '.net', 'core', 'mvc', 'web-api',
        'go', 'gin', 'echo', 'fiber', 'rust', 'actix', 'rocket', 'warp', 'axum', 'php', 'slim'
    ],
    'mobile': [
        'android', 'ios', 'react-native', 'flutter', 'swift', 'kotlin', 'mobile', 'xamarin', 
        'ionic', 'cordova', 'phonegap', 'expo', 'nativescript', 'unity', 'unreal', 'java-android',
        'objective-c', 'swiftui', 'jetpack-compose', 'flutter-dart', 'capacitor'
    ],
    'ml': [
        'machine-learning', 'ml', 'tensorflow', 'pytorch', 'sklearn', 'scikit-learn', 'ai', 'artificial-intelligence',
        'neural', 'deep-learning', 'data-science', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'plotly',
        'jupyter', 'notebook', 'keras', 'opencv', 'computer-vision', 'nlp', 'natural-language-processing',
        'transformers', 'bert', 'gpt', 'llm', 'langchain', 'huggingface', 'xgboost', 'lightgbm', 'catboost'
    ],
    'devops': [
        'docker', 'kubernetes', 'k8s', 'aws', 'amazon-web-services', 'gcp', 'google-cloud', 'azure', 
        'microsoft-azure', 'terraform', 'ansible', 'jenkins', 'ci/cd', 'github-actions', 'gitlab-ci',
        'circle-ci', 'travis-ci', 'helm', 'istio', 'prometheus', 'grafana', 'elk', 'elasticsearch',
        'logstash', 'kibana', 'nginx', 'apache', 'load-balancer', 'microservices', 'serverless'
    ],
    'database': [
        'mongodb', 'postgresql', 'postgres', 'mysql', 'sqlite', 'redis', 'elasticsearch', 'database', 
        'sql', 'nosql', 'cassandra', 'dynamodb', 'firebase', 'firestore', 'supabase', 'planetscale',
        'prisma', 'typeorm', 'sequelize', 'mongoose', 'knex', 'drizzle', 'clickhouse', 'snowflake'
    ],
    'testing': [
        'jest', 'mocha', 'chai', 'cypress', 'selenium', 'playwright', 'puppeteer', 'testing', 'unit-test',
        'integration-test', 'e2e', 'tdd', 'bdd', 'pytest', 'unittest', 'rspec', 'jasmine', 'karma'
    ],
    'tools': [
        'git', 'github', 'gitlab', 'bitbucket', 'vscode', 'intellij', 'vim', 'emacs', 'sublime',
        'postman', 'insomnia', 'figma', 'sketch', 'adobe', 'photoshop', 'illustrator'
    ]
}

def extract_skills_from_text(text):
    """Enhanced skill extraction with better pattern matching"""
    if not text:
        return []
    
    text_lower = text.lower()
    found_skills = []
    
    # Direct keyword matching
    for category, keywords in SKILL_PATTERNS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_skills.append(keyword)
    
    # Additional pattern matching for common variations
    import re
    
    # Framework patterns
    framework_patterns = [
        r'\b(react|vue|angular|svelte)\b',
        r'\b(django|flask|fastapi|express)\b', 
        r'\b(tensorflow|pytorch|keras)\b',
        r'\b(docker|kubernetes|k8s)\b',
        r'\b(mongodb|postgresql|mysql|redis)\b'
    ]
    
    for pattern in framework_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        found_skills.extend(matches)
    
    # Remove duplicates and return
    return list(set(found_skills))

def extract_skills_from_repo_structure(repo_data, readme_content):
    """Extract skills from repository structure, files, and content"""
    skills = []
    
    # Analyze repository name and description
    repo_text = f"{repo_data.get('name', '')} {repo_data.get('description', '')}"
    skills.extend(extract_skills_from_text(repo_text))
    
    # Analyze README content
    if readme_content:
        skills.extend(extract_skills_from_text(readme_content))
    
    # Analyze topics
    topics = repo_data.get('topics', [])
    for topic in topics:
        skills.extend(extract_skills_from_text(topic))
    
    # Language-based skill inference
    language = repo_data.get('language')
    if language:
        language_skills = {
            'JavaScript': ['javascript', 'frontend', 'web'],
            'TypeScript': ['typescript', 'javascript', 'frontend', 'web'],
            'Python': ['python', 'backend', 'data-science'],
            'Java': ['java', 'backend', 'android'],
            'Swift': ['swift', 'ios', 'mobile'],
            'Kotlin': ['kotlin', 'android', 'mobile'],
            'Go': ['go', 'backend', 'microservices'],
            'Rust': ['rust', 'backend', 'systems'],
            'C++': ['cpp', 'systems', 'game-development'],
            'C#': ['csharp', 'dotnet', 'backend'],
            'PHP': ['php', 'backend', 'web'],
            'Ruby': ['ruby', 'backend', 'rails'],
            'Dart': ['dart', 'flutter', 'mobile'],
            'HTML': ['html', 'frontend', 'web'],
            'CSS': ['css', 'frontend', 'styling'],
            'Jupyter Notebook': ['jupyter', 'data-science', 'python', 'ml']
        }
        
        if language in language_skills:
            skills.extend(language_skills[language])
    
    return list(set(skills))

def get_repo_readme(username, repo_name):
    """Get README content from repository"""
    readme_files = ['README.md', 'README.rst', 'README.txt', 'README']
    
    for readme_name in readme_files:
        try:
            readme_url = f"{GITHUB_API_URL}/repos/{username}/{repo_name}/contents/{readme_name}"
            readme_resp = requests.get(readme_url, headers=HEADERS)
            
            if readme_resp.status_code == 200:
                readme_data = readme_resp.json()
                if readme_data.get('content'):
                    content = base64.b64decode(readme_data['content']).decode('utf-8', errors='ignore')
                    return content
        except:
            continue
    
    return ""

def get_commit_count_paginated(username, repo_name):
    """Get accurate commit count with pagination"""
    try:
        commits_url = f"{GITHUB_API_URL}/repos/{username}/{repo_name}/commits?author={username}&per_page=1"
        response = requests.head(commits_url, headers=HEADERS)
        
        if response.status_code != 200:
            return 0
        
        # Parse Link header for pagination
        link_header = response.headers.get('Link', '')
        if 'rel="last"' in link_header:
            last_page_match = re.search(r'page=(\d+)>; rel="last"', link_header)
            if last_page_match:
                return int(last_page_match.group(1))
        
        # If no pagination, get actual count
        commits_resp = requests.get(f"{GITHUB_API_URL}/repos/{username}/{repo_name}/commits?author={username}&per_page=100", headers=HEADERS)
        if commits_resp.status_code == 200:
            commits_data = commits_resp.json()
            return len(commits_data) if isinstance(commits_data, list) else 0
            
    except Exception as e:
        print(f"Error getting commit count for {repo_name}: {e}")
    
    return 0

@app.get("/deep-search/<string:username>")
def deep_search(username):
    """
    Deep GitHub profile analysis with comprehensive metrics
    
    Returns:
    - Language & repo distribution (for pie charts)
    - Commit & activity metrics
    - Popularity and reach metrics
    - Skill inference from topics, READMEs, descriptions
    - Social & community contribution indicators
    """
    try:
        print(f"Starting deep analysis for {username}")
        start_time = time.time()
        
        # Get user data
        user_url = f"{GITHUB_API_URL}/users/{username}"
        user_resp = requests.get(user_url, headers=HEADERS)
        
        if user_resp.status_code != 200:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_resp.json()
        
        # Get all repositories with pagination
        all_repos = []
        page = 1
        while True:
            repos_url = f"{user_url}/repos?per_page=100&page={page}&type=all&sort=updated"
            repos_resp = requests.get(repos_url, headers=HEADERS)
            
            if repos_resp.status_code != 200:
                break
                
            repos_batch = repos_resp.json()
            if not repos_batch:
                break
                
            all_repos.extend(repos_batch)
            
            if len(repos_batch) < 100:
                break
                
            page += 1
            time.sleep(0.1)  # Rate limiting
        
        if not all_repos:
            return jsonify({"error": "No repositories found"}), 404
        
        print(f"Found {len(all_repos)} repositories")
        
        # Initialize analysis containers
        analysis = {
            "user_info": {
                "username": username,
                "name": user_data.get("name"),
                "bio": user_data.get("bio"),
                "company": user_data.get("company"),
                "location": user_data.get("location"),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "public_repos": user_data.get("public_repos", 0),
                "public_gists": user_data.get("public_gists", 0),
                "created_at": user_data.get("created_at"),
                "blog": user_data.get("blog"),
                "twitter_username": user_data.get("twitter_username")
            },
            "language_distribution": defaultdict(int),
            "stars_per_language": defaultdict(int),
            "commits_per_language": defaultdict(int),
            "top_repo_per_language": defaultdict(lambda: {"name": "", "stars": 0, "url": ""}),
            "repo_details": [],
            "activity_metrics": {
                "total_commits": 0,
                "active_repos_count": 0,
                "last_activity_date": None,
                "repos_with_recent_activity": 0,
                "avg_commits_per_repo": 0
            },
            "popularity_metrics": {
                "total_stars": 0,
                "total_forks": 0,
                "total_watchers": 0,
                "avg_stars_per_repo": 0,
                "most_starred_repo": {"name": "", "stars": 0, "description": "", "url": ""},
                "repos_with_stars": 0
            },
            "skills_analysis": {
                "topics_used": Counter(),
                "readme_keywords": Counter(),
                "description_keywords": Counter(),
                "all_inferred_skills": Counter(),
                "skill_categories": defaultdict(int)
            }
        }
        
        # Process repositories
        for i, repo in enumerate(all_repos):
            if i % 20 == 0:
                print(f"Processing repo {i+1}/{len(all_repos)}")
            
            repo_name = repo["name"]
            language = repo.get("language")
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            watchers = repo.get("watchers_count", 0)
            description = repo.get("description", "") or ""
            updated_at = repo.get("updated_at")
            repo_url = repo.get("html_url", "")
            
            # Language distribution
            if language:
                analysis["language_distribution"][language] += 1
                analysis["stars_per_language"][language] += stars
                
                # Track top repo per language
                if stars > analysis["top_repo_per_language"][language]["stars"]:
                    analysis["top_repo_per_language"][language] = {
                        "name": repo_name,
                        "stars": stars,
                        "url": repo_url
                    }
            
            # Get topics
            topics = []
            try:
                topics_url = f"{repo['url']}/topics"
                topics_resp = requests.get(topics_url, headers=TOPIC_HEADER)
                if topics_resp.status_code == 200:
                    topics = topics_resp.json().get("names", [])
                    analysis["skills_analysis"]["topics_used"].update(topics)
                time.sleep(0.05)  # Rate limiting
            except:
                pass
            
            # Get commit count (for starred repos or first 30)
            commits = 0
            if stars > 0 or i < 30:
                commits = get_commit_count_paginated(username, repo_name)
                analysis["activity_metrics"]["total_commits"] += commits
                
                if language and commits > 0:
                    analysis["commits_per_language"][language] += commits
                    
                time.sleep(0.1)  # Rate limiting for commit API
            
            # Activity tracking
            if updated_at:
                repo_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                if not analysis["activity_metrics"]["last_activity_date"] or repo_date > analysis["activity_metrics"]["last_activity_date"]:
                    analysis["activity_metrics"]["last_activity_date"] = updated_at
                
                # Check if repo was updated in last 6 months
                six_months_ago = datetime.now().replace(tzinfo=repo_date.tzinfo) - timedelta(days=180)
                if repo_date > six_months_ago:
                    analysis["activity_metrics"]["repos_with_recent_activity"] += 1
            
            # Popularity metrics
            analysis["popularity_metrics"]["total_stars"] += stars
            analysis["popularity_metrics"]["total_forks"] += forks
            analysis["popularity_metrics"]["total_watchers"] += watchers
            
            if stars > 0:
                analysis["popularity_metrics"]["repos_with_stars"] += 1
            
            if stars > analysis["popularity_metrics"]["most_starred_repo"]["stars"]:
                analysis["popularity_metrics"]["most_starred_repo"] = {
                    "name": repo_name,
                    "stars": stars,
                    "description": description,
                    "url": repo_url
                }
            
            # Get README for ALL repos (comprehensive analysis)
            readme_content = get_repo_readme(username, repo_name)
            time.sleep(0.1)  # Rate limiting
            
            # Enhanced skills analysis from multiple sources
            repo_skills = extract_skills_from_repo_structure(repo, readme_content)
            desc_skills = extract_skills_from_text(description)
            
            # Update skill counters
            analysis["skills_analysis"]["description_keywords"].update(desc_skills)
            analysis["skills_analysis"]["all_inferred_skills"].update(repo_skills)
            
            if readme_content:
                readme_skills = extract_skills_from_text(readme_content)
                analysis["skills_analysis"]["readme_keywords"].update(readme_skills)
                analysis["skills_analysis"]["all_inferred_skills"].update(readme_skills)
            
            # Enhanced skill categorization
            all_text = f"{description} {readme_content} {' '.join(topics)}"
            for category, keywords in SKILL_PATTERNS.items():
                category_count = 0
                for keyword in keywords:
                    if keyword in all_text.lower():
                        category_count += 1
                if category_count > 0:
                    analysis["skills_analysis"]["skill_categories"][category] += category_count
            
            # Store comprehensive repo details with enhanced skill analysis
            individual_repo_skills = extract_skills_from_repo_structure(repo, readme_content)
            analysis["repo_details"].append({
                "name": repo_name,
                "language": language,
                "stars": stars,
                "forks": forks,
                "watchers": watchers,
                "description": description,  # Full description (not truncated)
                "readme_content": readme_content,  # Full README content
                "readme_summary": readme_content[:500] + "..." if len(readme_content) > 500 else readme_content,  # First 500 chars for preview
                "topics": topics,
                "commits": commits,
                "updated_at": updated_at,
                "url": repo_url,
                "has_readme": bool(readme_content),
                "detected_skills": individual_repo_skills,  # Skills specific to this repo
                "skill_categories": {
                    category: len([skill for skill in individual_repo_skills 
                                 if skill in SKILL_PATTERNS.get(category, [])])
                    for category in SKILL_PATTERNS.keys()
                },
                "readme_length": len(readme_content) if readme_content else 0
            })
        
        # Calculate derived metrics
        total_repos = len(all_repos)
        active_repos = len([r for r in analysis["repo_details"] if r["commits"] > 0])
        
        analysis["activity_metrics"]["active_repos_count"] = active_repos
        analysis["activity_metrics"]["avg_commits_per_repo"] = round(
            analysis["activity_metrics"]["total_commits"] / max(total_repos, 1), 2
        )
        
        analysis["popularity_metrics"]["avg_stars_per_repo"] = round(
            analysis["popularity_metrics"]["total_stars"] / max(total_repos, 1), 2
        )
        
        # Convert collections to regular dicts for JSON serialization
        analysis["language_distribution"] = dict(analysis["language_distribution"])
        analysis["stars_per_language"] = dict(analysis["stars_per_language"])
        analysis["commits_per_language"] = dict(analysis["commits_per_language"])
        analysis["top_repo_per_language"] = dict(analysis["top_repo_per_language"])
        analysis["skills_analysis"]["topics_used"] = dict(analysis["skills_analysis"]["topics_used"])
        analysis["skills_analysis"]["readme_keywords"] = dict(analysis["skills_analysis"]["readme_keywords"])
        analysis["skills_analysis"]["description_keywords"] = dict(analysis["skills_analysis"]["description_keywords"])
        analysis["skills_analysis"]["all_inferred_skills"] = dict(analysis["skills_analysis"]["all_inferred_skills"])
        analysis["skills_analysis"]["skill_categories"] = dict(analysis["skills_analysis"]["skill_categories"])
        
        # Generate insights
        primary_language = max(analysis["language_distribution"], key=analysis["language_distribution"].get) if analysis["language_distribution"] else "Unknown"
        most_starred_language = max(analysis["stars_per_language"], key=analysis["stars_per_language"].get) if analysis["stars_per_language"] else "Unknown"
        
        total_commits = analysis["activity_metrics"]["total_commits"]
        total_stars = analysis["popularity_metrics"]["total_stars"]
        
        analysis["insights"] = {
            "primary_language": primary_language,
            "most_influential_language": most_starred_language,
            "activity_level": "High" if total_commits > 500 else "Medium" if total_commits > 100 else "Low",
            "popularity_level": "High" if total_stars > 100 else "Medium" if total_stars > 20 else "Low",
            "skill_diversity": len(analysis["skills_analysis"]["all_inferred_skills"]),
            "top_skills": list(Counter(analysis["skills_analysis"]["all_inferred_skills"]).most_common(10)),
            "most_used_topics": list(Counter(analysis["skills_analysis"]["topics_used"]).most_common(10)),
            "language_diversity": len(analysis["language_distribution"]),
            "contribution_consistency": "High" if analysis["activity_metrics"]["repos_with_recent_activity"] > total_repos * 0.3 else "Medium" if analysis["activity_metrics"]["repos_with_recent_activity"] > total_repos * 0.1 else "Low"
        }
        
        # Add metadata
        analysis["metadata"] = {
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "total_repos_analyzed": total_repos,
            "analysis_duration_seconds": round(time.time() - start_time, 2),
            "commit_data_coverage": f"{active_repos}/{total_repos} repos",
            "readme_analysis_coverage": len([r for r in analysis["repo_details"] if r["has_readme"]])
        }
        
        print(f"Deep analysis completed in {analysis['metadata']['analysis_duration_seconds']} seconds")
        
        return jsonify(analysis)
        
    except Exception as e:
        print(f"Deep analysis error: {str(e)}")
        return jsonify({"error": f"Deep analysis failed: {str(e)}"}), 500

@app.get("/deep-search/<string:username>/summary")
def deep_search_summary(username):
    """Quick summary version of deep search for faster responses"""
    try:
        # Get basic user info
        user_url = f"{GITHUB_API_URL}/users/{username}"
        user_resp = requests.get(user_url, headers=HEADERS)
        
        if user_resp.status_code != 200:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_resp.json()
        
        # Get limited repos (first 50)
        repos_url = f"{user_url}/repos?per_page=50&sort=updated"
        repos_resp = requests.get(repos_url, headers=HEADERS)
        
        # Better error handling for repos
        repos = []
        if repos_resp.status_code == 200:
            repos_data = repos_resp.json()
            if isinstance(repos_data, list):
                repos = repos_data
            else:
                print(f"Unexpected repos response: {repos_data}")
                return jsonify({"error": "Failed to fetch repositories"}), 500
        else:
            print(f"Failed to fetch repos: {repos_resp.status_code}")
            return jsonify({"error": "Failed to fetch repositories"}), 500
        
        if not repos:
            return jsonify({"error": "No repositories found"}), 404
        
        # Quick analysis with enhanced skills and README for each repo
        languages = Counter()
        total_stars = 0
        all_skills = Counter()
        
        for repo in repos[:30]:  # Limit processing
            # Ensure repo is a dict
            if not isinstance(repo, dict):
                continue
                
            if repo.get("language"):
                languages[repo["language"]] += 1
            
            total_stars += repo.get("stargazers_count", 0)
            
            # Get README content for better skill detection
            readme_content = get_repo_readme(username, repo.get("name", ""))
            time.sleep(0.05)  # Rate limiting
            
            # Enhanced skill detection for summary (now with README)
            repo_skills = extract_skills_from_repo_structure(repo, readme_content)
            all_skills.update(repo_skills)
        
        # Build enhanced top repos list with skills and README
        top_repos = []
        try:
            sorted_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0) if isinstance(x, dict) else 0, reverse=True)
            for repo in sorted_repos[:5]:
                if isinstance(repo, dict):
                    # Get README for each top repo
                    readme_content = get_repo_readme(username, repo.get("name", ""))
                    repo_skills = extract_skills_from_repo_structure(repo, readme_content)
                    time.sleep(0.05)  # Rate limiting
                    
                    top_repos.append({
                        "name": repo.get("name", "Unknown"),
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description", "") or "",
                        "readme_content": readme_content,  # Full README content
                        "readme_length": len(readme_content) if readme_content else 0,
                        "has_readme": bool(readme_content),
                        "detected_skills": repo_skills[:10]  # Top 10 skills for this repo
                    })
        except Exception as sort_error:
            print(f"Error sorting repos: {sort_error}")
            # Fallback: just take first 5 repos
            for repo in repos[:5]:
                if isinstance(repo, dict):
                    # Get README for each fallback repo
                    readme_content = get_repo_readme(username, repo.get("name", ""))
                    repo_skills = extract_skills_from_repo_structure(repo, readme_content)
                    time.sleep(0.05)  # Rate limiting
                    
                    top_repos.append({
                        "name": repo.get("name", "Unknown"),
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description", "") or "",
                        "readme_content": readme_content,  # Full README content
                        "readme_length": len(readme_content) if readme_content else 0,
                        "has_readme": bool(readme_content),
                        "detected_skills": repo_skills[:10]
                    })
        
        summary = {
            "username": username,
            "basic_info": {
                "name": user_data.get("name"),
                "followers": user_data.get("followers", 0),
                "public_repos": user_data.get("public_repos", 0),
                "location": user_data.get("location")
            },
            "top_languages": dict(languages.most_common(5)),
            "total_stars": total_stars,
            "avg_stars": round(total_stars / max(len(repos), 1), 2),
            "detected_skills": dict(all_skills.most_common(15)),  # Top 15 detected skills
            "skill_categories": {
                category: len([skill for skill in all_skills.keys() 
                             if skill in SKILL_PATTERNS.get(category, [])])
                for category in SKILL_PATTERNS.keys()
            },
            "top_repos": top_repos
        }
        
        return jsonify(summary)
        
    except Exception as e:
        print(f"Summary analysis error details: {str(e)}")
        return jsonify({"error": f"Summary analysis failed: {str(e)}"}), 500

@app.post("/match-candidate/<string:username>")
def match_single_candidate(username):
    """
    Match a single candidate against job requirements
    """
    try:
        data = request.get_json()
        job_description = data.get("job_description", "")
        required_skills = [skill.lower() for skill in data.get("required_skills", [])]
        nice_to_have = [skill.lower() for skill in data.get("nice_to_have", [])]
        candidate_data = data.get("candidate_data", {})
        
        if not candidate_data:
            return jsonify({"error": "No candidate data provided"}), 400
        
        # Extract additional skills from job description
        job_skills_from_desc = extract_skills_from_text(job_description)
        all_job_skills = list(set(required_skills + nice_to_have + job_skills_from_desc))
        
        top_repos = candidate_data.get("top_repos", [])
        
        if not top_repos:
            return jsonify({
                "candidate_username": username,
                "total_match_percentage": 0,
                "repo_matches": []
            })
        
        repo_matches = []
        weighted_scores = []
        total_weight = 0
        
        for repo in top_repos:
            repo_name = repo.get("name", "")
            repo_skills = repo.get("detected_skills", [])
            readme_content = repo.get("readme_content", "")
            description = repo.get("description", "")
            stars = repo.get("stars", 0)
            readme_length = repo.get("readme_length", 0)
            
            # Calculate skill match percentage
            repo_skills_lower = [skill.lower() for skill in repo_skills]
            
            # Count required skill matches (higher weight)
            required_matches = len(set(required_skills) & set(repo_skills_lower))
            required_score = (required_matches / max(len(required_skills), 1)) * 70
            
            # Count nice-to-have matches (bonus points)
            nice_to_have_matches = len(set(nice_to_have) & set(repo_skills_lower))
            nice_to_have_score = (nice_to_have_matches / max(len(nice_to_have), 1)) * 15
            
            # Additional context matching from README and description
            all_text = f"{description} {readme_content}".lower()
            context_matches = sum(1 for skill in all_job_skills if skill in all_text)
            context_score = min((context_matches / max(len(all_job_skills), 1)) * 10, 10)
            
            # Quality bonus (README length and stars)
            readme_bonus = min(readme_length / 1000, 1) * 3  # Max 3 points
            popularity_bonus = min(stars / 10, 1) * 2  # Max 2 points
            
            # Calculate final repo match percentage
            repo_match_percentage = min(
                required_score + nice_to_have_score + context_score + readme_bonus + popularity_bonus,
                100
            )
            
            repo_matches.append({
                "repo_name": repo_name,
                "match_percentage": round(repo_match_percentage, 0)
            })
            
            # Weight repositories by importance (stars + README quality)
            repo_weight = max(stars, 1) * max(readme_length / 100, 1)
            weighted_scores.append(repo_match_percentage * repo_weight)
            total_weight += repo_weight
        
        # Calculate overall candidate match percentage
        if total_weight > 0:
            total_match_percentage = sum(weighted_scores) / total_weight
        else:
            total_match_percentage = 0
        
        # Sort repo matches by percentage (highest first)
        repo_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        
        return jsonify({
            "candidate_username": username,
            "total_match_percentage": round(total_match_percentage, 0),
            "repo_matches": repo_matches
        })
        
    except Exception as e:
        print(f"Match single candidate error: {str(e)}")
        return jsonify({"error": f"Matching failed: {str(e)}"}), 500
    
@app.post("/match-candidate-ai/<string:username>")
def match_single_candidate_ai(username):
    """
    AI-powered matching for a single candidate using Gemini
    """
    try:
        data = request.get_json()
        job_description = data.get("job_description", "")
        required_skills = data.get("required_skills", [])
        nice_to_have = data.get("nice_to_have", [])
        candidate_data = data.get("candidate_data", {})
        
        if not candidate_data:
            return jsonify({"error": "No candidate data provided"}), 400
        
        if not job_description:
            return jsonify({"error": "Job description is required"}), 400
        
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        top_repos = candidate_data.get("top_repos", [])
        
        if not top_repos:
            return jsonify({
                "candidate_username": username,
                "total_match_percentage": 0,
                "repo_matches": []
            })
        
        repo_matches = []
        
        # Analyze each repository with Gemini
        for repo in top_repos:
            repo_name = repo.get("name", "")
            description = repo.get("description", "")
            readme_content = repo.get("readme_content", "")
            detected_skills = repo.get("detected_skills", [])
            
            # Create comprehensive repo context
            repo_context = f"""
Repository: {repo_name}
Description: {description}
README Content: {readme_content[:1500]}...
Detected Skills: {', '.join(detected_skills)}
"""
            
            # Create Gemini prompt for repo matching
            repo_prompt = f"""
You are an expert technical recruiter. Analyze this GitHub repository against the job requirements and provide a match percentage (0-100).

JOB REQUIREMENTS:
Job Description: {job_description}
Required Skills: {', '.join(required_skills)}
Nice-to-Have Skills: {', '.join(nice_to_have)}

REPOSITORY TO ANALYZE:
{repo_context}

ANALYSIS CRITERIA:
1. Technical skill alignment (50% weight)
2. Project relevance to job role (25% weight)
3. Code quality indicators (README, documentation) (15% weight)
4. Project complexity and impact (10% weight)

RESPONSE FORMAT:
Provide ONLY a JSON object with this exact structure:
{{
    "match_percentage": <integer 0-100>,
    "reasoning": "<brief 2-3 sentence explanation>"
}}

Be strict but fair in scoring. Only give high scores (80+) for excellent matches.
"""
            
            try:
                # Get Gemini response
                response = model.generate_content(repo_prompt)
                response_text = response.text.strip()
                
                # Parse JSON response
                import json
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                repo_analysis = json.loads(response_text)
                
                repo_matches.append({
                    "repo_name": repo_name,
                    "match_percentage": int(repo_analysis.get("match_percentage", 0))
                })
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"Error analyzing repo {repo_name}: {str(e)}")
                # Fallback scoring
                fallback_score = 0
                repo_skills_text = ' '.join(detected_skills + [description, repo_name]).lower()
                required_matches = sum(1 for skill in required_skills if skill.lower() in repo_skills_text)
                if required_matches > 0:
                    fallback_score = min(required_matches * 25, 75)
                
                repo_matches.append({
                    "repo_name": repo_name,
                    "match_percentage": fallback_score
                })
        
        # Calculate overall match with Gemini
        if repo_matches:
            candidate_summary = f"""
Candidate: {username}
Repository Scores: {repo_matches}
Candidate Skills: {candidate_data.get('detected_skills', {})}
Top Languages: {candidate_data.get('top_languages', {})}
"""
            
            overall_prompt = f"""
Based on the repository analysis, provide an overall candidate match percentage (0-100).

JOB REQUIREMENTS:
Job Description: {job_description}
Required Skills: {', '.join(required_skills)}
Nice-to-Have Skills: {', '.join(nice_to_have)}

CANDIDATE ANALYSIS:
{candidate_summary}

Provide ONLY an integer between 0-100.
"""
            
            try:
                overall_response = model.generate_content(overall_prompt)
                total_match_percentage = int(overall_response.text.strip())
            except Exception as e:
                print(f"Error calculating overall match: {str(e)}")
                # Fallback: weighted average
                if repo_matches:
                    total_match_percentage = round(sum(r["match_percentage"] for r in repo_matches) / len(repo_matches))
                else:
                    total_match_percentage = 0
        else:
            total_match_percentage = 0
        
        # Sort repo matches by percentage
        repo_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        
        return jsonify({
            "candidate_username": username,
            "total_match_percentage": total_match_percentage,
            "repo_matches": repo_matches
        })
        
    except Exception as e:
        print(f"Single candidate AI matching error: {str(e)}")
        return jsonify({"error": f"AI matching failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5009)