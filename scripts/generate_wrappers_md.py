from pathlib import Path
import sys
import asyncio
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from xyte_mcp_alpha.server import get_server


def extract_fields(schema: dict) -> str:
    if not schema:
        return ""
    props = schema.get("properties", {})
    if not props:
        return ""
    first = next(iter(props.values()))
    if "$ref" in first:
        ref = first["$ref"].split("/")[-1]
        defs = schema.get("$defs", {}) or schema.get("definitions", {})
        subprops = defs.get(ref, {}).get("properties", {})
    else:
        subprops = props
    return ", ".join(subprops.keys())


async def main() -> None:
    server = get_server()
    tools = await server.list_tools()
    resources = await server.list_resources()
    templates = await server.list_resource_templates()

    lines = ["# XYTE API Wrappers", "", "## Tools", "", "| Name | Parameters |", "| ---- | ---------- |"]
    for t in tools:
        params = extract_fields(t.inputSchema)
        lines.append(f"| `{t.name}` | {params} |")

    lines.extend(["", "## Resources", "", "| URI | Name |", "| --- | ---- |"])
    for r in resources:
        lines.append(f"| `{r.uri}` | {r.name} |")
    for tmpl in templates:
        lines.append(f"| `{tmpl.uriTemplate}` | {tmpl.name or ''} |")

    Path("docs/wrappers.md").write_text("\n".join(lines))
    print("Generated docs/wrappers.md")


if __name__ == "__main__":
    asyncio.run(main())
