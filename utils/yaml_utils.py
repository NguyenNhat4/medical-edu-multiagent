import yaml
import re

def parse_yaml_robustly(text):
    """
    Attempts to parse YAML from a string, robustly handling common LLM errors.
    """
    if not text:
        return {}

    # 1. Strip Markdown code blocks
    clean_text = text.strip()
    if "```yaml" in clean_text:
        clean_text = clean_text.split("```yaml")[1].split("```")[0].strip()
    elif "```" in clean_text:
        clean_text = clean_text.split("```")[1].split("```")[0].strip()

    # 2. Try standard parsing
    try:
        return yaml.safe_load(clean_text)
    except Exception as e:
        first_error = e

    # 3. Attempt to fix common errors: unquoted strings with colons
    # Strategy: iterate lines. If a line matches "key: value" and value has colon and not quoted, quote it.
    lines = clean_text.split('\n')
    fixed_lines = []

    # Regex to identify key-value pairs:
    # Group 1: Indentation
    # Group 2: Key
    # Group 3: Value
    kv_pattern = re.compile(r"^(\s*)([\w\-\_]+):\s*(.+)$")

    for line in lines:
        match = kv_pattern.match(line)
        if match:
            indent, key, value = match.groups()
            value = value.strip()

            # Check if it needs quoting
            # It needs quoting if it contains ':' and is not already quoted or special yaml char
            needs_quote = False
            if ":" in value:
                if not (value.startswith('"') and value.endswith('"')) and \
                   not (value.startswith("'") and value.endswith("'")) and \
                   not value.startswith(('|', '>', '{', '[')):
                     needs_quote = True

            if needs_quote:
                # Escape existing double quotes
                value = value.replace('"', '\\"')
                fixed_lines.append(f'{indent}{key}: "{value}"')
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    fixed_text = "\n".join(fixed_lines)

    try:
        return yaml.safe_load(fixed_text)
    except Exception:
        # 4. If repair failed, try RegEx fallback for specific top-level keys
        # This is a "last resort" partial parser for flattened structures or specific keys
        # We know we often look for: status, message, requirements, blueprint, sections

        result = {}

        # Simple extraction for top-level keys
        keys_to_extract = ["status", "message", "thinking", "tool", "reason"]
        for key in keys_to_extract:
            pattern = re.compile(r"^" + key + r":\s*(.+)$", re.MULTILINE)
            match = pattern.search(clean_text)
            if match:
                val = match.group(1).strip()
                # Remove quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                result[key] = val

        # If we have requirements (nested), it's harder.
        # But maybe we can just return what we have?
        if result:
            return result

        print(f"YAML Parsing Failed. Raw text:\n{text}\nFirst Error: {first_error}")
        return None
