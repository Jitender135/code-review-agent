import re


def parse_diff_positions(diff: str) -> dict:
    result = {}
    current_file = None
    position = 0
    in_hunk = False

    lines = diff.split("\n")

    for line in lines:
        file_match = re.match(r"^--- (.+?) ---$", line)
        if file_match:
            current_file = file_match.group(1).strip()
            result[current_file] = {}
            position = 0
            in_hunk = False
            continue

        if current_file is None:
            continue

        if line.startswith("@@"):
            in_hunk = True
            position += 1
            continue

        if not in_hunk:
            continue

        if line.startswith("+") or line.startswith("-") or line.startswith(" "):
            position += 1
            code = line[1:].strip()
            # only store + lines (added) and context lines (space)
            # GitHub only allows comments on + lines and context lines
            if code and current_file in result:
                if code not in result[current_file]:
                    result[current_file][code] = position

    return result

def find_position(diff_map: dict, filename: str, line_hint: str):
    if filename not in diff_map:
        for key in diff_map:
            if filename in key or key in filename:
                filename = key
                break
        else:
            return None

    file_map = diff_map[filename]
    line_hint = line_hint.strip().lstrip("+-").strip()

    # 1. exact match
    if line_hint in file_map:
        return file_map[line_hint]

    # 2. normalize quotes and try again
    def normalize(s):
        return s.replace("'", '"').lower().strip()

    normalized_hint = normalize(line_hint)
    for code, pos in file_map.items():
        if normalize(code) == normalized_hint:
            return pos

    # 3. partial match — hint is substring of code or vice versa
    for code, pos in file_map.items():
        if line_hint in code or code in line_hint:
            return pos

    # 4. keyword match — find first line containing key words
    keywords = [w for w in line_hint.split() if len(w) > 4]
    for code, pos in file_map.items():
        if all(kw.lower() in code.lower() for kw in keywords[:3]):
            return pos
        

    # 5. SQL/code pattern match — find by most unique keyword
    unique_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "password", 
                      "api_key", "token", "secret", "exec", "eval"]
    for keyword in unique_keywords:
        if keyword.lower() in line_hint.lower():
            for code, pos in file_map.items():
                if keyword.lower() in code.lower():
                    return pos

    # debug
    return None


def debug_diff(diff: str):
    lines = diff.split("\n")
    current_file = None
    position = 0
    in_hunk = False

    for line in lines:
        file_match = re.match(r"^--- (.+?) ---$", line)
        if file_match:
            current_file = file_match.group(1).strip()
            position = 0
            in_hunk = False
            print(f"\nFile: {current_file}")
            continue

        if line.startswith("@@"):
            in_hunk = True
            position += 1
            print(f"  pos={position} HUNK: {line}")
            continue

        if not in_hunk:
            continue

        if line.startswith("+") or line.startswith("-") or line.startswith(" "):
            position += 1
            print(f"  pos={position} | {line}")