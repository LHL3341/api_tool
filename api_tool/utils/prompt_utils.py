import re
from typing import Dict, Any

class SafeDict(dict):
    def __missing__(self, key):
        return ""

def fill_prompt(template: str, variables: Dict[str, Any]) -> str:
    placeholders = re.findall(r"\{(.*?)\}", template)
    safe_vars = SafeDict(variables)
    for ph in placeholders:
        try:
            value = eval(ph, {}, safe_vars)
        except Exception:
            value = safe_vars[ph]
        template = template.replace(f"{{{ph}}}", str(value))
    return template
