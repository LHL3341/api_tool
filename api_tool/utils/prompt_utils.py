import re
from typing import Dict, Any

class SafeDict(dict):
    def __missing__(self, key):
        return ""

# def fill_prompt(template: str, variables: Dict[str, Any]) -> str:
#     placeholders = re.findall(r"\{(.*?)\}", template)
#     safe_vars = SafeDict(variables)
#     for ph in placeholders:
#         try:
#             value = eval(ph, {}, safe_vars)
#                     except NameError:
#             # 如果 key 不存在，抛出 KeyError
#             raise KeyError(f"Missing key in variables: '{ph}'")
#         except Exception:
#             # 普通占位符
#             if ph not in variables:
#                 raise KeyError(f"Missing key in variables: '{ph}'")
#         except Exception:
#             value = safe_vars[ph]
#         template = template.replace(f"{{{ph}}}", str(value))
#     return template



# def fill_prompt(template: str, variables: Dict[str, Any]) -> str:
#     placeholders = re.findall(r"\{(.*?)\}", template)

#     for ph in placeholders:
#         try:
#             # 支持表达式求值（例如 {a + b}）
#             value = eval(ph, {}, variables)
#         except NameError:
#             # 如果 key 不存在，抛出 KeyError
#             raise KeyError(f"Missing key in variables: '{ph}'")
#         except Exception:
#             # 普通占位符
#             if ph not in variables:
#                 raise KeyError(f"Missing key in variables: '{ph}'")
#             value = variables[ph]
#         template = template.replace(f"{{{ph}}}", str(value))

#     return template


def fill_prompt(template: str, variables: Dict[str, Any]) -> str:
    # 临时替换 {{ 和 }} 以防误判
    template = template.replace("{{", "<<LBRACE>>").replace("}}", "<<RBRACE>>")

    # 查找单层占位符 {key}
    placeholders = re.findall(r"\{(.*?)\}", template)

    for ph in placeholders:
        try:
            value = eval(ph, {}, variables)
        except NameError:
            raise KeyError(f"Missing key in variables: '{ph}'")
        except Exception:
            if ph not in variables:
                raise KeyError(f"Missing key in variables: '{ph}'")
            value = variables[ph]
        template = template.replace(f"{{{ph}}}", str(value))

    # 恢复 LaTeX 转义大括号
    template = template.replace("<<LBRACE>>", "{").replace("<<RBRACE>>", "}")
    return template