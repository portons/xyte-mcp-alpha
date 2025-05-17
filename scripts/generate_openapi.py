#!/usr/bin/env python
"""Generate OpenAPI specification for the MCP server."""
from pathlib import Path
import json
from xyte_mcp_alpha.http import build_openapi, internal_app


def main() -> None:
    schema = build_openapi(internal_app)
    out_path = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    out_path.write_text(json.dumps(schema, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
