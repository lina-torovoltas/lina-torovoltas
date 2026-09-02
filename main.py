import json
import os
import re
import urllib.request
from datetime import datetime, UTC

API = "https://api.github.com"

CONFIG_FILE = "config.txt"
HISTORY_FILE = "divergence_history.txt"
README_FILE = "README.md"

MARKER = "<!-- DIVERGENCE_METER -->"


def github_get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "World-Line-Divergence"
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_repos():
    user = os.environ["GITHUB_REPOSITORY_OWNER"]

    repos = []
    page = 1

    while True:
        data = github_get(
            f"https://api.github.com/users/{user}/repos?per_page=100&page={page}"
        )

        if not data:
            break

        repos += data
        page += 1

    return repos


def get_languages(repos):
    result = {}

    for repo in repos:
        if repo["fork"]:
            continue

        for lang, size in github_get(repo["languages_url"]).items():
            lang = lang.lower()
            result[lang] = result.get(lang, 0) + size

    return result


def config():
    excluded, weights = set(), {}

    if not os.path.exists(CONFIG_FILE):
        return excluded, weights

    for line in open(CONFIG_FILE, encoding="utf-8"):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("ex:"):
            excluded = {x.lower() for x in line[3:].split()}
        elif ":" in line:
            k, v = line.split(":", 1)
            weights[k.strip().lower()] = float(v)

    return excluded, weights


def divergence(stack, excluded, weights):
    stack = {k.lower(): v for k, v in stack.items() if k.lower() not in excluded}

    if not stack:
        return 0.0

    langs = sorted(stack)
    ideal = 1 / len(langs)
    total = sum(stack[k] for k in langs)
    alpha = sum(ideal * weights.get(x, 0) for x in langs)
    real = sum((stack[k] / total) * weights.get(k, 0) for k in langs)

    return round((real - alpha) * 0.5, 6)


def old_value():
    if not os.path.exists(HISTORY_FILE):
        return 0.0

    lines = [x.strip() for x in open(HISTORY_FILE) if x.strip()]
    if not lines:
        return 0.0

    m = re.search(r"->\s*([+-]?\d+\.\d+)", lines[-1])
    return float(m.group(1)) if m else 0.0


def save_history(old, new):
    text = f"{old:+.6f} -> {new:+.6f}"

    if round(old, 6) == round(new, 6):
        return text

    date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{date} | {text}\n")

    return text


def update_readme(text):
    if not os.path.exists(README_FILE):
        return

    data = open(README_FILE, encoding="utf-8").read()

    if MARKER not in data:
        print("ERROR: marker missing")
        return

    block = f'{MARKER}\n<p align="center">\n  <code>Divergence: {text}</code>\n</p>'

    data = re.sub(
        re.escape(MARKER) + r"(?:\s*<p align=\"center\">.*?</p>)?",
        block,
        data,
        flags=re.S
    )

    open(README_FILE, "w", encoding="utf-8").write(data)


def main():
    repos = get_repos()
    stack = get_languages(repos)
    excluded, weights = config()
    
    new = divergence(stack, excluded, weights)
    old = old_value()
    text = save_history(old, new)

    if round(old, 6) != round(new, 6):
        update_readme(text)
    else:
        print("nothing has changed")

    print("Divergence:", text)


if __name__ == "__main__":
    main()
