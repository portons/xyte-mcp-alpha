# Plugin API Versioning

The plugin system exposes optional hooks like `on_event` and `on_log`. The server currently implements **version 1.0** of this API, exported as `PLUGIN_API_VERSION` from `xyte_mcp.plugin`.

Plugins should define a `PLUGIN_API_VERSION` constant matching the server's version to indicate compatibility. When loading a plugin, the server logs a warning if the versions differ. This helps catch breaking changes when the API evolves.

Minor releases within a major version remain backward compatible. A bump in the major version signals breaking changes. Older major versions will continue to work for at least one minor release after a new major version is announced.

Use the constant to check against your plugin implementation and update as needed when new versions are released.
