import re
from collections import defaultdict
from pathlib import Path

from config.logger import logger


BUILTIN_TYPES = {
    "void",
    "int",
    "float",
    "double",
    "bool",
    "string",
    "char",
    "byte",
    "short",
    "long",
    "uint",
    "ulong",
    "ushort",
    "sbyte",
    "decimal",
    "object",
    "var",
    "dynamic",
    "List",
    "Dictionary",
    "HashSet",
    "Queue",
    "Stack",
    "IEnumerable",
    "IList",
    "IDictionary",
    "Array",
    "Tuple",
    "KeyValuePair",
    "GameObject",
    "Transform",
    "MonoBehaviour",
    "ScriptableObject",
    "Component",
    "Behaviour",
    "Vector2",
    "Vector3",
    "Vector4",
    "Quaternion",
    "Color",
    "Rect",
    "Bounds",
    "Matrix4x4",
    "Camera",
    "Light",
    "Rigidbody",
    "Rigidbody2D",
    "Collider",
    "Collider2D",
    "RaycastHit",
    "AudioSource",
    "AudioClip",
    "Animation",
    "Animator",
    "AnimatorController",
    "Mesh",
    "Material",
    "Shader",
    "Texture",
    "Texture2D",
    "Sprite",
    "RenderTexture",
    "Time",
    "Input",
    "Debug",
    "Mathf",
    "Random",
    "Application",
    "SceneManager",
    "Resources",
    "Coroutine",
    "WaitForSeconds",
    "WaitForEndOfFrame",
    "WaitForFixedUpdate",
    "Action",
    "Func",
    "Predicate",
    "EventHandler",
    "Task",
    "SerializeField",
    "Header",
    "Range",
    "Tooltip",
    "HideInInspector",
    "RequireComponent",
    "MenuItem",
    "CustomEditor",
    "ContextMenu",
    "CreateAssetMenu",
    "Exception",
    "ArgumentException",
    "NullReferenceException",
    "IDisposable",
    "IEnumerator",
    "StringBuilder",
    "Regex",
    "Match",
}

QUALIFIED_TYPE = r"(?:[A-Za-z_][a-zA-Z0-9_]*\.)*([A-Z][a-zA-Z0-9_]*)"


def _strip_comments(content: str) -> str:
    content = re.sub(r"//[^\n]*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    return content


def _add_ref(refs: set[str], type_name: str) -> None:
    type_name = type_name.strip().split(".")[-1]
    if type_name and type_name[0].isupper() and type_name not in BUILTIN_TYPES and len(type_name) > 1:
        refs.add(type_name)


def extract_references(content: str, namespace_to_classes: dict | None = None) -> set[str]:
    """从单个 .cs 文件内容中提取它引用的所有自定义类名。"""
    refs: set[str] = set()
    content = _strip_comments(content)

    if namespace_to_classes:
        for namespace in re.findall(r"\busing\s+([A-Za-z_][a-zA-Z0-9_.]*)\s*;", content):
            for class_name in namespace_to_classes.get(namespace, []):
                _add_ref(refs, class_name)

    analysis_content = re.sub(r"^\s*using\s+[A-Za-z_][a-zA-Z0-9_.]*\s*;\s*$", "", content, flags=re.MULTILINE)
    analysis_content = re.sub(
        r"^\s*namespace\s+[A-Za-z_][a-zA-Z0-9_.]*\s*$",
        "",
        analysis_content,
        flags=re.MULTILINE,
    )

    type_pattern = re.compile(r"\b" + QUALIFIED_TYPE + r"\s+[a-zA-Z_][a-zA-Z0-9_]*\s*[=;,)\(\{\[]")
    for match in type_pattern.finditer(analysis_content):
        _add_ref(refs, match.group(1))

    static_pattern = re.compile(r"\b((?:[A-Za-z_][a-zA-Z0-9_]*\.)+[A-Za-z_][a-zA-Z0-9_]*)\s*(?=\()")
    for match in static_pattern.finditer(content):
        if content[: match.start()].rstrip().endswith("new"):
            continue
        chain_parts = match.group(1).split(".")
        if len(chain_parts) >= 2:
            _add_ref(refs, chain_parts[-2])

    new_pattern = re.compile(rf"\bnew\s+{QUALIFIED_TYPE}\s*[(<]")
    for match in new_pattern.finditer(analysis_content):
        _add_ref(refs, match.group(1))

    inherit_pattern = re.compile(r"\bclass\s+\w+\s*:\s*([A-Za-z0-9_.,<>\s]+)\s*\{?")
    for match in inherit_pattern.finditer(analysis_content):
        for base in re.split(r"[,<>]", match.group(1)):
            base = base.strip()
            if not base:
                continue
            _add_ref(refs, base.split()[-1])

    for generic_block in re.findall(r"<([^>]+)>", analysis_content):
        for type_name in re.findall(r"(?:[A-Za-z_][a-zA-Z0-9_]*\.)*([A-Z][a-zA-Z0-9_]*)", generic_block):
            _add_ref(refs, type_name)

    return refs


def build_reference_graph(scripts: list[dict]) -> tuple[dict, dict, dict]:
    """构建项目内类之间的引用图谱。"""
    known_classes: set[str] = set()
    class_to_path: dict[str, str] = {}

    for script in scripts:
        class_name = script.get("class_name", "")
        path = script.get("path", "")
        if not class_name:
            continue
        known_classes.add(class_name)
        if class_name in class_to_path and class_to_path[class_name] != path:
            logger.warning(f"检测到重复类名: {class_name} -> {class_to_path[class_name]} | {path}")
            continue
        class_to_path[class_name] = path

    reference_graph: defaultdict[str, set[str]] = defaultdict(set)
    reverse_graph: defaultdict[str, set[str]] = defaultdict(set)

    for script in scripts:
        class_name = script.get("class_name", "")
        if not class_name:
            continue

        raw_refs = script.get("_raw_references", set()) or set()
        valid_refs = {ref for ref in raw_refs if ref in known_classes and ref != class_name}
        if not valid_refs:
            continue

        reference_graph[class_name].update(valid_refs)
        for ref in valid_refs:
            reverse_graph[ref].add(class_name)

    return (
        {key: sorted(value) for key, value in reference_graph.items()},
        {key: sorted(value) for key, value in reverse_graph.items()},
        class_to_path,
    )


def get_related_scripts(
    class_name: str,
    scripts: list[dict],
    reference_graph: dict,
    reverse_graph: dict,
    class_to_path: dict,
    depth: int = 1,
) -> list[dict]:
    """获取与指定类相关的脚本骨架。"""
    _ = class_to_path
    related: set[str] = set()

    related.update(reference_graph.get(class_name, []))
    related.update(reverse_graph.get(class_name, []))

    if depth >= 2:
        first_level = list(related)
        for ref_class in first_level:
            related.update(reference_graph.get(ref_class, []))
            related.update(reverse_graph.get(ref_class, []))

    related.discard(class_name)
    return [script for script in scripts if script.get("class_name") in related]


def get_impact_scope(class_name: str, reverse_graph: dict, depth: int = 2) -> list[str]:
    """获取修改某个类可能影响的类列表。"""
    visited = {class_name}
    impact: list[str] = []
    current_level = [class_name]

    for _ in range(depth):
        next_level: list[str] = []
        for current in current_level:
            for caller in reverse_graph.get(current, []):
                if caller in visited:
                    continue
                visited.add(caller)
                impact.append(caller)
                next_level.append(caller)
        if not next_level:
            break
        current_level = next_level

    return impact


def parse_meta_file(project_path: str, relative_path: str) -> dict:
    project_root = Path(project_path).resolve()
    meta_rel = relative_path if relative_path.endswith(".meta") else f"{relative_path}.meta"
    path = (project_root / meta_rel).resolve()

    try:
        path.relative_to(project_root)
    except ValueError:
        return {"success": False, "message": f"路径越界: {relative_path}"}

    if not path.exists():
        return {"success": False, "message": f"未找到 meta 文件: {meta_rel}"}

    content = path.read_text(encoding="utf-8", errors="ignore")
    guid_match = re.search(r"guid:\s*([a-f0-9]+)", content)
    importer_match = re.search(r"^([A-Za-z]+Importer):", content, re.MULTILINE)
    return {
        "success": True,
        "path": str(path.relative_to(project_root)).replace("\\", "/"),
        "guid": guid_match.group(1) if guid_match else "",
        "importer": importer_match.group(1) if importer_match else "",
    }


def find_guid_references(project_path: str, guid: str, limit: int = 30) -> list[str]:
    project_root = Path(project_path).resolve()
    exts = {".meta", ".asset", ".prefab", ".unity", ".mat", ".controller", ".anim"}
    results: list[str] = []

    for path in project_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        if any(part in {"Library", "Temp", "Packages", "obj", ".git"} for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if guid in content:
            results.append(str(path.relative_to(project_root)).replace("\\", "/"))
            if len(results) >= limit:
                break

    return results
