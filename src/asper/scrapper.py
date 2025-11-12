"""Web scraper for downloading LPCP contest problem descriptions.

Fetches problem READMEs from GitHub (2020-2025), filters out checker/solution
sections and images, and saves cleaned markdown files locally.
"""

import re
from pathlib import Path

import requests


def parse_problem_number(problem_folder: str) -> int:
    """Extract numeric id from folder name like 'problem-3'."""
    try:
        return int(problem_folder.split("-")[1])
    except Exception:
        return -1
    
def get_additional_input_text(year: int, problem_number: int) -> str | None:
    """
    Return the extra text to inject into the '## Input format' section.
    Customize this mapping per year/problem. Return None or '' to skip.
    """
    extras = {
        2020: {
            1: "Input facts format:\nsize(S).\ncol(C,clue).\nrow(R,clue).\ngroup(R,C,value).",
            2: "Input facts format:\nsize(S).\ntype(N).\ncol(C,clue).\nrow(R,clue).\ngroup(R,C,value).",
            3: "Input facts format:\nsize(S).\nclue(N,(R,C),value).",
            4: "Input facts format:\nsize(S).\nwhite(R,C).\nblack(R,C).",
            5: "Input facts format:\nsize(S).\nwhite(R,C,value).\nblack(R,C,value).",
        },
        2021: {
            1: "Input facts format:\nsize(S).\nfrog(R,C).\nfree(R,C).\nwall(R,C).",
            2: "Input facts format:\nsize(S).\ncolors(C).\nbutton(R,C,value).",
            3: "Input facts format:\nsize(S).\ninitial(R,C,type,orientation).",
            4: "Input facts format:\ncolor(1..F).\nbottle(0,B,I,value).",
            5: "Input facts format:\ncolor(1..F).\nbottle(0,B,I,value).",
        },
        2022: {
            1: "Input facts format:\nsize(R,C).\npoi(R,C,D).",
            2: "Input facts format:\ncapacities(A,B).",
            3: "Input facts format:\nsize(R,C).\nisland(R,C,B).",
            4: "Input facts format:\nrows(R).\ncols(C).\nstart(R,C,dir).\nmain_size(M).\nsubroutine_size(S).\ntarget(T,R,C).\nheight(R,C,H).",
            5: "Input facts format:\nsize(S).\nclue(R,C,B).",
        },
        2023: {
            1: "Input facts format:\ninput(R,C,value).",
            2: "Input facts format:\ninput(R,C,value).",
            3: "Input facts format:\ninput(R,C,value).",
            4: "Input facts format:\ninput(R,C,value).",
            5: "Input facts format:\ninput(R,C,value).",
        },
        2025: {
            1: "Input facts format:\nsizeX(S).\nsizeY(S).\nsumX(X,S).\nsumY(Y,S).\nmaxV(V).",
            2: "Input facts format:\nsize(X,Y).\nn_professors(P).\nn_students(S).\nn_black(B).\nn_white(W).\nn_outposts(N).\nn_admin(A).\nprofessor(R,C).\nstudent(R,C).\nblack(R,C).\nwhite(R,C).\noutpost(R,C,V).\nadmin(R,C,V).",
            3: "Input facts format:\ndim(N,M).\nleaper(P,Q).",
            4: "Input facts format:\nintersections(N).\nstreets(M).\nrequests(K).\nintersection(I).\nstreet(U,V).\nrequest(A,B).",
            5: "Input facts format:\nsize(N).\nassign((R,C),V).",
        }
    }

    return extras.get(year, {}).get(problem_number)

def get_additional_output_text(year: int, problem_number: int) -> str | None:
    """
    Return the extra text to inject into the '## Output format' section.
    Customize this mapping per year/problem. Return None or '' to skip.
    """
    extras = {
        2020: {
            1: "Output facts format:\nwater(R,C).",
            2: "Output facts format:\nright(R,C).\nbottom(R,C).",
            3: "Output facts format:\nsize(S).\nblack(R,C).",
            4: "Output facts format:\nright(R,C).\nbottom(R,C).",
            5: "Output facts format:\nright(R,C).\nbottom(R,C).",
        },
        2021: {
            1: "Output facts format:\nfrog(R,C).\nselect((R1,C1),(R2,C2), S).",
            2: "Output facts format:\npair((R1,C1),(R2,C2),S).",
            3: "Output facts format:\ninitial(R,C,type,orientation).\nfinal(R,C,type,orientation).",
            4: "Output facts format:\npair(T,From,To).\nbottle(0,B,I,value).",
            5: "Output facts format:\npair(T,From,To).\nbottle(0,B,I,value).",
        },
        2022: {
            1: "Output facts format:\nsize(R,C).\npoi(R,C,D).\nwall(R,C).",
            2: "Output facts format:\ndo(action,step).",
            3: "Output facts format:\nsize(R,C).\nconnect(R1,C1,R2,C2,W).\nisland(R,C,B).",
            4: "Output facts format:\nmain_slot(I,action).\nsubroutine_slot(I,action).",
            5: "Output facts format:\nsize(S).\nslash(R,C).\nbackslash(R,C).",
        },
        2023: {
            1: "Output facts format:\noutput(R,C,value).",
            2: "Output facts format:\noutput(R,C,value).",
            3: "Output facts format:\noutput(R,C,value).",
            4: "Output facts format:\noutput(R,C,value).",
            5: "Output facts format:\noutput(R,C,value).",
        },
        2025: {
            1: "Output facts format:\nassign(R,C,V).\nreach(R,C).",
            2: "Output facts format:\nconnect(R1,C1,R2,C2).",
            3: "Output facts format:\ntour(R1,C1,R2,C2).",
            4: "Output facts format:\nselect(A,B).\npath(A,B,I,V).",
            5: "Output facts format:\ngiven((R,C),V).",
        },
    }
    return extras.get(year, {}).get(problem_number)

def add_text_to_input_format_section(content: str, extra_text: str) -> str:
    """
    Append extra_text at the end of the '## Input format' section.
    If the section is not found, append a new section at the end.
    """
    if not extra_text:
        return content

    # Find the '## Input format' heading (case-insensitive)
    heading_regex = re.compile(r"^(##\s*input\s*format\s*)$", re.IGNORECASE | re.MULTILINE)
    match = heading_regex.search(content)
    if not match:
        # Fallback: append a new section at the end
        tail = "\n\n## Input format\n\n" + extra_text.strip() + "\n"
        return content.rstrip() + tail

    # Find the end of this section: next '## ' heading or end of content
    section_start = match.end()
    next_heading = re.search(r"^\s*##\s+", content[section_start:], flags=re.MULTILINE)
    if next_heading:
        insert_pos = section_start + next_heading.start()
    else:
        insert_pos = len(content)

    # Ensure proper spacing and insert before the next heading
    prefix = "" if content[section_start:insert_pos].endswith("\n") else "\n"
    injected = f"{prefix}\n{extra_text.strip()}\n"
    return content[:insert_pos] + injected + content[insert_pos:]

def add_text_to_output_format_section(content: str, extra_text: str) -> str:
    """
    Append extra_text at the end of the '## Output format' section.
    If the section is not found, append a new section at the end.
    """
    if not extra_text:
        return content

    heading_regex = re.compile(r"^(##\s*output\s*format\s*)$", re.IGNORECASE | re.MULTILINE)
    match = heading_regex.search(content)
    if not match:
        tail = "\n\n## Output format\n\n" + extra_text.strip() + "\n"
        return content.rstrip() + tail

    section_start = match.end()
    next_heading = re.search(r"^\s*##\s+", content[section_start:], flags=re.MULTILINE)
    insert_pos = section_start + next_heading.start() if next_heading else len(content)

    prefix = "" if content[section_start:insert_pos].endswith("\n") else "\n"
    injected = f"{prefix}\n{extra_text.strip()}\n"
    return content[:insert_pos] + injected + content[insert_pos:]

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
        base = filter_readme_content(response.text)

        # Inject custom text into "## Input format" section
        problem_num = parse_problem_number(problem_folder)
        extra_input = get_additional_input_text(year, problem_num)
        extra_output = get_additional_output_text(year, problem_num)
        
        content = base
        if extra_input:
            content = add_text_to_input_format_section(content, extra_input)
        if extra_output:
            content = add_text_to_output_format_section(content, extra_output)
        return content
    except Exception as e:
        print(f"Error fetching README for {year}/{problem_folder}: {e}")
        return None

def filter_readme_content(content) -> str:
    """Filter README content to exclude checker/solution sections."""
    if not content:
        return ""

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

def main():
    """Main entry point for running the scraper."""
    # Run the scraper
    scrape_lpcp_problems(start_year=2020, end_year=2025)

if __name__ == "__main__":
    main()
