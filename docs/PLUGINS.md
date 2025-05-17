# Plugin System

This server supports lightweight plugins that can react to events and logs.
Plugins are regular Python modules referenced in the `XYTE_PLUGINS` environment
variable as a comma separated list. Each module should expose an object with
`on_event` and/or `on_log` methods.

## Writing a Plugin

1. Create a Python module (e.g. `myplugin.py`).
2. Implement a class with optional `on_event(event: dict)` and
   `on_log(message: str, level: int)` methods.
3. Export an instance named `plugin` so the loader can discover it.
4. Set `XYTE_PLUGINS=myplugin` before starting the server.

````python
# myplugin.py
class MyPlugin:
    def on_event(self, event: dict) -> None:
        print("event", event)

    def on_log(self, message: str, level: int) -> None:
        print("log", level, message)

plugin = MyPlugin()
````

Plugins may also call `register_payload_transform` to modify API responses before
they reach the client.

## Registration

Set the environment variable and restart the server:

```bash
export XYTE_PLUGINS=myplugin,other.plugin
python -m xyte_mcp_alpha
```

All listed plugins will be loaded at startup. Failures are logged but do not stop
startup.
