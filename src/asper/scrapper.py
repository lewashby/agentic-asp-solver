"""Web scraper for downloading LPCP contest problem descriptions.

Fetches problem READMEs from GitHub (2020-2025), filters out checker/solution
sections and images, and saves cleaned markdown files locally.
"""

import re
from pathlib import Path

import requests


def get_problem_folders(year):
    """Get list of problem folders from GitHub repository."""
    url = f"https://api.github.com/repos/lpcp-contest/lpcp-contest-{year}/contents"

    try:
        response = requests.get(url)
        response.raise_for_status()
        contents = response.json()

        # Filter for problem folders (problem-1, problem-2, etc.), excluding problem-0
        problem_folders = []
        for item in contents:
            if item["type"] == "dir" and item["name"].startswith("problem-"):
                problem_num = item["name"].split("-")[1]
                if problem_num != "0":
                    problem_folders.append(item["name"])

        return sorted(problem_folders)
    except Exception as e:
        print(f"Error fetching folders for year {year}: {e}")
        return []


def get_readme_content(year, problem_folder):
    """Get README.md content from a problem folder."""
    branch = "master" if year == 2020 else "main"
    url = f"https://raw.githubusercontent.com/lpcp-contest/lpcp-contest-{year}/{branch}/{problem_folder}/README.md"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return filter_readme_content(response.text)
    except Exception as e:
        print(f"Error fetching README for {year}/{problem_folder}: {e}")
        return None


def filter_readme_content(content):
    """Filter README content to exclude checker/solution sections."""
    if not content:
        return None

    # Common section titles to exclude (case-insensitive)
    exclude_start_patterns = [
        r"(?i)SHA-1\s+of\s+the\s+expected\s+output",
        r"(?i)##\s*self-check",
        r"checker\s+output",
        r"instances\s+as\s+the\s+one\s+above\s+can\s+be\s+visualized",
    ]

    lines = content.split("\n")
    # Find the first line that matches any exclude pattern
    cutoff_index = len(lines)
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if any(re.search(pattern, line_lower) for pattern in exclude_start_patterns):
            cutoff_index = i
            break

    # Keep only lines before the cutoff
    filtered_lines = lines[:cutoff_index]

    # Remove markdown images: ![alt text](url) or ![](url)
    cleaned_lines = []
    image_pattern = r"!\[.*?\]\(.*?\)"

    for line in filtered_lines:
        # Remove all image markdown from the line
        cleaned_line = re.sub(image_pattern, "", line)
        cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines).strip()


def scrape_lpcp_problems(start_year=2020, end_year=2025, output_dir="lpcp_problems"):
    """Scrape LPCP problem descriptions from GitHub."""
    # Create main output directory
    Path(output_dir).mkdir(exist_ok=True)

    for year in range(start_year, end_year + 1):
        print(f"\nProcessing year {year}...")

        # Create year directory
        year_dir = Path(output_dir) / f"lpcp-{year}"
        year_dir.mkdir(exist_ok=True)

        # Get problem folders for this year
        problem_folders = get_problem_folders(year)

        if not problem_folders:
            print(f"No problems found for year {year}")
            continue

        print(f"Found {len(problem_folders)} problems")

        # Download each problem's README
        for problem_folder in problem_folders:
            print(f"  Downloading {problem_folder}...")

            readme_content = get_readme_content(year, problem_folder)

            if readme_content:
                # Save to file
                output_file = year_dir / f"{problem_folder}.md"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(readme_content)
                print(f"    * Saved to {output_file}")
            else:
                print("    x Failed to download")

    print(f"\n* Scraping complete! Files saved to '{output_dir}' directory")


if __name__ == "__main__":
    # Run the scraper
    scrape_lpcp_problems(start_year=2020, end_year=2025)
