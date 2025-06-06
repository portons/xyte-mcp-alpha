# Plugin System

This document explains how to extend the MCP server with Python plugins.
Plugins are enabled by listing their modules in the `XYTE_PLUGINS` environment
variable or via Python entry points.

## Installation

Plugins are standard Python packages. Install them alongside the server using
`pip`:

```bash
pip install my-plugin
```

A plugin should expose an instance called `plugin` that implements one or both
of the following callbacks:

```python
class MyPlugin:
    API_VERSION = 1
    def on_event(self, event: dict) -> None: ...
    def on_log(self, message: str, level: int) -> None: ...

plugin = MyPlugin()
```

## Registration

Plugins can be registered in two ways:

1. **Environment variable** – set `XYTE_PLUGINS` to a comma separated list of
   import paths. Each path should point to a module containing a `plugin`
   object or a module implementing the callbacks directly.
2. **Entry points** – packages may declare an entry point in the group
   `xyte_mcp.plugins`. The loader will automatically discover and
   register these plugins on startup.

The server calls `plugin.load_plugins()` during boot which collects plugins from
both mechanisms.

## Reloading

When the process receives `SIGHUP` or `plugin.reload_plugins()` is called, all
loaded plugins are cleared and discovered again. This allows deploying updates
without restarting the whole service.

## Validation

During loading each plugin is validated:

* It must implement `on_event` or `on_log`.
* If an `API_VERSION` attribute is present it must match the server's plugin API
  version.

Invalid plugins are skipped and a warning is logged.

## Writing a Plugin

1. Create a Python module (e.g. `myplugin.py`).
2. Implement a class with optional `on_event(event: dict)` and
   `on_log(message: str, level: int)` methods.
3. Export an instance named `plugin` so the loader can discover it.
4. Set `XYTE_PLUGINS=myplugin` before starting the server.

## Example

```python
# my_plugin.py
from xyte_mcp import plugin

class Logger:
    API_VERSION = 1
    def on_event(self, event: dict) -> None:
        print("event", event)

    def on_log(self, message: str, level: int) -> None:
        print("log", level, message)

plugin_instance = Logger()
```

Register via environment variable:

```bash
export XYTE_PLUGINS=my_plugin:plugin_instance
```

Or in `pyproject.toml`:

```toml
[project.entry-points."xyte_mcp.plugins"]
logger = "my_plugin:plugin_instance"
```

After installation the server will automatically load the plugin.

Plugins may also call `register_payload_transform` to modify API responses before
they reach the client.

> **Warning**: plugins execute inside the server process. Only install plugins
> from sources you trust.

All listed plugins will be loaded at startup. Failures are logged but do not stop
startup.
