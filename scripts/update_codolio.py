import os
from datetime import datetime, timezone

import requests

API_URL = os.environ.get("CODOLIO_URL", "https://api.codolio.com/user")
TOKEN = os.environ["CODOLIO_TOKEN"]
README_PATH = "README.md"

START = "<!-- CODOLIO_STATS_START -->"
END = "<!-- CODOLIO_STATS_END -->"

# Only these platforms are displayed in the profile README.
PLATFORM_ORDER = ("leetcode", "codechef", "geeksforgeeks")

PLATFORM_LINKS = {
    "leetcode": ("LeetCode", "https://leetcode.com/algofire24/"),
    "codechef": ("CodeChef", "https://www.codechef.com/users/algofire24"),
    "geeksforgeeks": (
        "GeeksforGeeks",
        "https://www.geeksforgeeks.org/user/algofire24/",
    ),
}


def safe_int(value):
    """Convert nullable API values to integers safely."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def fetch_codolio_data():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
    }
    response = requests.get(API_URL, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()
    if not payload.get("status", {}).get("success", False):
        raise RuntimeError(
            "Codolio API returned an unsuccessful response: "
            f"{payload.get('status', {}).get('message', 'unknown error')}"
        )
    return payload


def build_stats_markdown(payload):
    profiles = (
        payload.get("data", {})
        .get("platformProfiles", {})
        .get("platformProfiles", [])
    )

    # Filter at the source so Codeforces, InterviewBit, TUF, and other
    # platforms are not included in either the table or combined total.
    selected_profiles = {
        (profile.get("platform") or "").lower(): profile
        for profile in profiles
        if (profile.get("platform") or "").lower() in PLATFORM_ORDER
    }

    platform_data = {}
    combined_solved = 0

    for platform in PLATFORM_ORDER:
        profile = selected_profiles.get(platform)
        if not profile:
            continue

        user = profile.get("userStats") or {}
        questions = profile.get("totalQuestionStats") or {}
        daily = profile.get("dailyActivityStatsResponse") or {}

        solved = safe_int(questions.get("totalQuestionCounts"))
        combined_solved += solved

        platform_data[platform] = {
            "solved": solved,
            "easy": safe_int(questions.get("easyQuestionCounts")),
            "medium": safe_int(questions.get("mediumQuestionCounts")),
            "hard": safe_int(questions.get("hardQuestionCounts")),
            "rating": user.get("currentRating"),
            "max_rating": user.get("maxRating"),
            "stars": safe_int(user.get("stars")),
            "dsa_rating": user.get("dsaRating"),
            "badge": user.get("contestBadgeName"),
            "max_streak": daily.get("maxStreak"),
            "active_days": daily.get("totalActiveDays"),
            "rank": user.get("rank"),
        }

    lines = [
        '<p align="center">',
        '  <img src="https://img.shields.io/badge/CODOLIO-LIVE%20CODING%20STATS-000000?style=for-the-badge&logo=codeforces&logoColor=01fa02" alt="Codolio live coding stats" />',
        "</p>",
        "",
        "| Platform | Problems Solved | Current Rating | Best Rating | Highlights |",
        "|:---|---:|---:|---:|:---|",
    ]

    for platform in PLATFORM_ORDER:
        item = platform_data.get(platform)
        if not item:
            continue

        label, url = PLATFORM_LINKS[platform]
        rating = item["rating"]
        max_rating = item["max_rating"]

        rating_text = f"`{rating}`" if rating is not None else "—"
        best_text = f"`{max_rating}`" if max_rating is not None else "—"

        highlights = []
        if platform == "leetcode":
            if item["badge"]:
                highlights.append(f"**{item['badge']}**")
            if item["max_streak"] is not None:
                highlights.append(f"{item['max_streak']}-day max streak")
        elif platform == "codechef":
            if item["stars"]:
                highlights.append(f"{item['stars']}-star")
            if item["dsa_rating"] is not None:
                highlights.append(f"DSA rating `{item['dsa_rating']}`")
        elif platform == "geeksforgeeks":
            if item["active_days"] is not None:
                highlights.append(f"{item['active_days']} active days")

        lines.append(
            f"| [{label}]({url}) | **{item['solved']:,}** | "
            f"{rating_text} | {best_text} | "
            f"{' · '.join(highlights) if highlights else '—'} |"
        )

    # LeetCode difficulty split is shown separately because the API supplies
    # Easy/Medium/Hard counts for this profile.
    leetcode = platform_data.get("leetcode")
    if leetcode:
        lines += [
            "",
            "#### LeetCode · Problem Breakdown",
            "",
            "| Easy | Medium | Hard | Total |",
            "|---:|---:|---:|---:|",
            f"| {leetcode['easy']:,} | {leetcode['medium']:,} | "
            f"{leetcode['hard']:,} | **{leetcode['solved']:,}** |",
        ]

        leetcode_profile = selected_profiles.get("leetcode", {})
        badges = (
            (leetcode_profile.get("badgeStats") or {}).get("badgeList") or []
        )
        notable_badges = []
        preferred_terms = ("Knight", "365 Days", "200 Days", "SQL 50")

        for badge in badges:
            name = badge.get("displayName") or badge.get("name")
            if name and any(term.lower() in name.lower() for term in preferred_terms):
                if name not in notable_badges:
                    notable_badges.append(name)

        if notable_badges:
            lines += [
                "",
                "**Notable badges:** "
                + " · ".join(f"`{name}`" for name in notable_badges[:4]),
            ]

    lines += [
        "",
        f"> **Total solved across these 3 platforms: {combined_solved:,}** "
        "(platform totals may include duplicate problems).",
        "",
        f"<sub>Last synced: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        "· Source: Codolio API.</sub>",
    ]

    return "\n".join(lines)


def update_readme(markdown):
    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    if START not in readme or END not in readme:
        raise RuntimeError(
            f"Could not find {START} and {END} markers in {README_PATH}"
        )

    start_index = readme.index(START) + len(START)
    end_index = readme.index(END, start_index)

    updated = (
        readme[:start_index]
        + "\n"
        + markdown
        + "\n"
        + readme[end_index:]
    )

    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as file:
            file.write(updated)
        print("README.md updated.")
    else:
        print("README.md is already up to date.")


if __name__ == "__main__":
    api_data = fetch_codolio_data()
    stats_markdown = build_stats_markdown(api_data)
    update_readme(stats_markdown)
