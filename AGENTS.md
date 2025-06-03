Based on the codebase, I’ll generate a detailed `AGENTS.md` file that serves as a practical reference for agents interacting with the MCP server. It will include authentication, session handling, tool usage, error reporting, and context management, based on actual server behavior.

I'll let you know once it's ready.


# Xyte MCP Server – Agent Integration Guide

This guide explains how agents (human or AI) can interact with the Xyte MCP server to control devices, manage tickets, and handle events. It covers authentication, using tools and resources, maintaining context, error codes, event consumption, asynchronous commands, and built-in workflow prompts. The goal is to provide clear, actionable guidance based on the server’s implementation.

## Authentication

Before using any MCP capabilities, the agent (or the environment hosting the agent) must authenticate with Xyte’s API via the MCP server’s configuration:

* **API Key:** Set the environment variable `XYTE_API_KEY` to your organization’s API key. This is required for all operations. The server uses this key to authorize requests to Xyte’s cloud API.
* **Base URL & Other Config:** By default, the server targets Xyte’s production API base URL. You can override `XYTE_BASE_URL` for testing, though typically not needed. Other optional settings include `XYTE_CACHE_TTL` (caching duration for certain lookups), `XYTE_RATE_LIMIT` (to tune the rate limit threshold), and `XYTE_ENV` (environment name). See the provided `.env.example` for reference.

**Usage:** Typically, you will provide these credentials via a `.env` file or environment variables before launching the MCP server. The server reads them on startup. Once configured, agents do not need to send authentication headers on each request – the server handles auth with Xyte internally using the provided key/token.

Ensure that the API key remains secure, as it grants control over your organization’s devices and data.

## Tool Invocation

The MCP server exposes a variety of **tools** – discrete actions the agent can invoke to perform operations (sending commands, updating records, etc.). Each tool has a name and expects certain inputs. Agents call these tools by name, supplying the required parameters, and receive a structured result or confirmation.

**Available Tools:** Key tools and their inputs include:

* **`claim_device`** (`name`, `space_id`, *`mac`*, *`sn`*, *`cloud_id`*): Claim (register) a new device into the organization with a friendly name and target space. Optional fields like MAC address, serial number, or cloud ID can be provided if needed.
* **`delete_device`** (`device_id`): Remove a device from the organization by its ID. This is a destructive action – once deleted, the device is unassigned from the org.
* **`update_device`** (`device_id`, `configuration`): Update a device’s configuration. Supply the device ID and a dictionary of configuration parameters to apply (e.g. settings or attributes the device should adopt).
* **`send_command`** (`device_id`, `name`, `friendly_name`, *`file_id`*, *`extra_params`*): Send a control command to a device. You must specify the device ID, the command’s technical name, and a human-friendly name (for logging or UI). Optionally include a file ID (if the command involves transferring a file) and any extra parameters required by the command. This tool will execute the command on the device via Xyte’s API.
* **`cancel_command`** (`device_id`, `command_id`, `name`, `friendly_name`, *`file_id`*, *`extra_params`*): Cancel a previously sent command. Provide the target device ID and the specific command’s ID to cancel, along with the same command name/details that were used to send it. (Using the same `name` and `friendly_name` helps identify the command to cancel.) This will attempt to halt the command’s execution on the device.
* **`update_ticket`** (`ticket_id`, `title`, `description`): Modify the details of a support ticket (e.g. update its title or description).
* **`mark_ticket_resolved`** (`ticket_id`): Mark a support ticket as resolved/closed.
* **`send_ticket_message`** (`ticket_id`, `message`): Post a new message to the conversation thread of a support ticket (e.g. an agent’s response or a user follow-up).
* **`search_device_histories`** (*filters:* `status`, `from_date`, `to_date`, *`device_id`*, *`space_id`*, *`name`*): Search a device’s history records (logs of events/commands) with optional filtering criteria. You can filter by status type, a date range (ISO timestamps), a specific device or space, or by name of the event. This returns matching history entries (e.g. errors, reboots, status changes) for troubleshooting or analysis.
* **`get_device_analytics_report`** (`device_id`, *`period`*): Retrieve usage analytics for a given device over a time period. By default, it fetches data for the last 30 days, but you can specify a period like `"last_7_days"` or other supported ranges. This can return metrics such as uptime, usage hours, etc., depending on what the Xyte API provides.
* **`set_context`** (`device_id`, `space_id`): Set session defaults (context) for the agent’s subsequent calls. By providing a device ID and/or space ID, you inform the server that future tool calls can assume these values by default if not explicitly given. This is essentially a way to avoid repeating common parameters. *(More on context in the **Context Management** section.)*

Additionally, there are specialized tools for asynchronous command execution and event retrieval (`send_command_async`, `get_task_status`, `get_next_event`), which are covered in later sections.

### Invoking Tools and Dry-Run Considerations

To invoke a tool, the agent typically issues a request or calls a function by the tool’s name with the required parameters. For example, using a Python-like pseudo-code:

```python
# Example: Send a reboot command to a device
result = send_command({
    "device_id": "device123",
    "name": "reboot",
    "friendly_name": "Reboot Device"
})
```

In this call, the MCP server will execute the **send\_command** tool with the provided JSON payload. Under the hood it will call the Xyte API to send the command, then return a result back to the agent.

**Dry-Run / Read-Only vs. Destructive Tools:** Some tools are safe to call without side effects (read-only), while others change state or trigger actions (destructive):

* Tools like `search_device_histories` and `get_device_analytics_report` only retrieve data; they do not alter anything. The server marks these as read-only tools. Agents can invoke them freely to gather information (akin to a *dry-run* since they are purely queries).
* Tools that create, modify, or delete things (e.g. `claim_device`, `delete_device`, `update_device`, `send_command`) are **destructive** (they change the real system state). Agents should use caution with these: ensure the context and parameters are correct and perhaps confirm with the user (if applicable) before executing. There is no built-in simulation mode for these actions – calling them will perform the action. If an agent is uncertain, it can first use resources or read-only tools (like checking `devices://` or device status) to verify conditions before invoking a destructive tool.

### Tool Responses and Results

Most tools return either a raw data object (usually reflecting the API response) or a structured **ToolResponse** with additional metadata:

* **Raw Data:** For many tools, especially those that retrieve information or perform simple updates, the result will be a dictionary of data. For example, `list_devices` (via `devices://`) returns a list of devices, `get_ticket` returns the ticket details, `update_device` returns the updated device record, etc. The data keys and format mirror the Xyte API. The agent can directly use this data for reasoning or UI. For instance, `delete_device` might return a confirmation object or an empty result indicating success.

* **`ToolResponse` Object:** Some tools provide a richer response with a summary and guidance for next steps. The `ToolResponse` model includes:

    * `data`: the primary data payload (e.g. the API response or relevant result),
    * `summary`: a short human-readable summary of what happened,
    * `next_steps`: a list of suggested next action identifiers (tool names or resource names),
    * `related_tools`: a list of other tool names that might be relevant.

  For example, the **send\_command** tool returns a `ToolResponse` that includes a summary message and a suggested next step. If you send a reboot command, the response might look like:

  ```json
  {
    "data": { /* command issuance result from Xyte */ },
    "summary": "Command 'Reboot Device' sent to device device123",
    "next_steps": ["get_device_status"]
  }
  ```

  Here, `summary` confirms the action, and `next_steps` suggests that the agent should next check the device status (using the `device://device123/status` resource, which corresponds to “get\_device\_status”). The agent can use this info to decide its next move automatically. Another example is **set\_context**, which returns a ToolResponse with a summary `"Context updated"` and the updated context state as data.

* **Interpreting the Response:** Agents should inspect the `summary` and `next_steps` when present. The summary can be conveyed to end-users or used in reasoning to confirm the action’s outcome. The `next_steps` list (if provided) are recommendations from the server on what to do next – for example, after sending a command, checking status or history is often prudent. Agents can treat these as hints to form their subsequent tool calls. The `related_tools` field (currently not widely used) may list other tools relevant to the situation; an agent can consider those as alternate approaches or additional actions.

In cases where a tool returns only raw data (no summary), it means the action’s outcome is straightforward (e.g., a data fetch or a direct update). The agent should examine the data or check for expected fields (like a success flag or updated values) to determine success. When errors occur, tools will not return a normal response – instead, an error (exception) is raised, as described in **Error Handling** below.

Finally, agents can discover the available tools and their descriptions programmatically if needed. The MCP server provides a `GET /tools` endpoint that lists all tool names, descriptions, and hints about their safety (read-only or destructive). This can be useful for an agent that wants to self-inspect capabilities.

## Resources

**Resources** are read-only data endpoints exposed by the MCP server. They allow agents to query the current state of devices, tickets, incidents, etc., using a simple URI format. Resources do not require any input besides the identifier in the URI (if any), and they return structured data from the Xyte system.

Available resource URIs include:

* **`devices://`** – Retrieves **all devices** in the organization. Returns a list of device objects (each containing details like device `id`, name, type, status, assigned space, etc.). For example, an agent can use this to get the list of devices and then filter or select one for further actions.
* **`device://{device_id}/status`** – Fetches the **current status and details of a specific device**. Replace `{device_id}` with the target device’s ID. The result includes information such as power state, online/offline status, current settings, and other telemetry available for that device.
* **`device://{device_id}/commands`** – Lists all **commands issued to the device**, typically including recent and pending commands. This can show command history or currently running commands for that device (with details like command IDs, names, timestamps, statuses).
* **`device://{device_id}/histories`** – Returns the **history records for a device**, which are logs of events and actions related to that device. This may include status changes, error reports, command results, etc. Agents can scan this to verify if a certain action happened (e.g., whether a reboot took place, or if any errors were reported recently).
* **`organization://info/{device_id}`** – Retrieves **organization-specific info for a given device**. This might include context like what organization or subscription the device is under, or any metadata linking the device to organizational structure. (This is a somewhat special case: the underlying API expects a device ID to return info about the org/project that device belongs to.)
* **`incidents://`** – Lists all **current incidents** in the organization. Incidents are typically ongoing issues or alerts (e.g., device failures, offline alerts, etc.). The data returned would include incident IDs, affected device or room, description, severity, status, etc.
* **`tickets://`** – Lists all **support tickets** in the organization (open and maybe recent closed ones depending on API). Each ticket includes details like ticket ID, title, description, status, associated device or user, etc. Agents might use this to find relevant support issues.
* **`ticket://{ticket_id}`** – Fetches a **specific support ticket** by ID, including its full details and conversation messages. Use this to get the latest state of a ticket (e.g., to see if a user replied or to gather context when handling a ticket).
* **`user://{user_token}/preferences`** – Retrieves the **stored preferences for a given user** (identified by their user token). Preferences could include things like the user’s preferred devices or default room. For example, the server might store that a particular user cares about devices X, Y, Z. The returned data (e.g., a `preferred_devices` list) can inform which devices to focus on for that user.
* **`user://{user_token}/devices`** – Lists **devices filtered by a user’s preferences**. In effect, this returns a subset of `devices://` – those devices that the specified user is most interested in (their “preferred devices”). The server implements this by taking all devices and cross-referencing with the `preferred_devices` list from that user’s preferences. Agents can use this to personalize operations, focusing on the user’s own equipment.

**Using Resources:** In practice, an agent can fetch a resource by referencing its URI in a query or via the MCP protocol. For example, an agent might simply request `devices://` to get the device list. If using the HTTP API, the MCP server provides a `GET /resources` endpoint that lists all resource URIs available. However, to retrieve the actual data of a resource, the agent will typically call the resource through the MCP session (for instance, by including the URI in the agent’s message or via a dedicated call in code). The exact mechanism depends on the integration (some agent frameworks allow the agent to “open” a resource URI directly).

Regardless of how they’re fetched, resources always return **structured JSON data** representing the current state from Xyte’s perspective. Here are a few examples of what data to expect:

* `devices://` returns an object containing all devices, likely under a key like `"devices"` (e.g., `{"devices": [ {id: ..., name: ..., status: ...}, {...} ]}`). An agent can iterate through this list to find a device of interest.
* `device://123/status` might return `{ "device": { "id": "123", "name": "Projector A", "online": true, "last_seen": "...", ... } }`. It’s essentially the same data you’d get from Xyte’s “get device” API.
* `device://123/histories` could return a list of history entries: `{ "histories": [ {...}, {...} ] }` or a similar structure, where each entry might include a timestamp, event type, and message (e.g., “Temperature high” or “Rebooted”).
* `incidents://` might look like `{ "incidents": [ { "id": "inc1", "device_id": "123", "description": "Device offline", "status": "open", ...}, {...} ] }`.
* `user://demo-token/preferences` might return `{ "preferred_devices": ["device1"], "default_room": "101" }` as per the example in the code.

Agents should use these resources to **gather context and make informed decisions**. For instance, before sending a reboot command, an agent could check `device://{id}/status` and `device://{id}/histories` to see if the device is actually unresponsive and if it has a history of reboots or errors. Or, when a user asks about ongoing issues, the agent could consult `incidents://` and `tickets://` to provide an accurate update.

Remember, resources are **read-only and safe** – using them does not change anything on the system. They are efficient for an agent to call as needed (some data may even be cached by the server for performance). The server’s internal rate limiting applies across all calls, so high-frequency polling of resources should be done judiciously (but occasional use is fine).

## Context Management

The MCP server supports session-level context so that agents can avoid repeating common parameters. By using the **`set_context`** tool, an agent can store defaults like the current device ID or space (room) ID for the ongoing session. Subsequent tool calls will automatically use these context values if their parameters are not explicitly provided.

**Setting Context:** Call the `set_context` tool with a `device_id` and/or `space_id`. For example:

```python
# Set the session context to focus on device "device123" and space 42
set_context({"device_id": "device123", "space_id": 42})
```

This will store `"current_device_id": "device123"` and `"current_space_id": 42` in the session’s state. The tool returns a confirmation (a ToolResponse containing the updated context state and a summary "Context updated"). Only the fields you provide are updated, so you can set one without the other.

**Using Context in Tools:** Once context is set, you can omit those parameters in future tool calls. The server will automatically fill them in from the context:

* If you call `send_command` without specifying a `device_id`, the server will default to the `current_device_id` in the context (if one is set). For instance, after setting context as above, you could just do `send_command({"name": "reboot", "friendly_name": "Reboot Device"})` without explicitly providing `"device_id": "device123"`. The server will infer it from context and send the command to *device123*. This makes command sequences more convenient, especially when an agent is focused on one device at a time.
* Similarly, other tools that require a device or space ID may look to context. For example, `update_device`, `delete_device`, or `search_device_histories` could use the context’s `current_device_id` if you don’t provide one in the call. (If both context and parameters are provided, the explicit parameter would typically take precedence.) **Important:** Not every tool currently auto-applies context, but those that logically operate on a device will check for a default. If a required identifier is missing in both the call and context, you’ll get an error (e.g., "device\_id is required").
* The `current_space_id` can be used in a similar way for tools or resources that operate at the space level (for example, if a future tool lists devices in the current space, it could use this). In the present set of tools, space\_id might be used as a filter in `search_device_histories` or for potential future expansions.

**Persistent Session State:** The context is tied to the agent’s session (the `Context` object in the MCP server) – it is not a global setting and not stored across server restarts. If the session ends or the agent disconnects, the context goes away. Agents should set context at the beginning of a session or when a new focus is needed. For example, if a user switches context (“Now let’s look at a different device…”), the agent should update the context via `set_context` with the new device\_id.

**Context Required:** Note that `set_context` itself requires a session context to operate; you cannot call it outside of an agent session. If, for some reason, the context object is missing, the tool will raise an error "Context required" (this typically means it’s being invoked in an improper way – in normal agent use this shouldn’t happen).

**Additional Context Info:** The server may store other helpful tidbits in the session state. For instance, when you send a command, the server records the command name as `last_command` in the context state. An agent could use this (if exposed) to recall what it last did. This isn’t usually needed explicitly, but it’s part of the design to help track the conversation state. The main fields you’ll set and rely on are `current_device_id` (and possibly `current_space_id`).

**Example Workflow:** Suppose a user says “Reboot the projector in Room 101.” The agent might:

1. Find the device ID of the projector in Room 101 (perhaps by searching `devices://` by name or space).
2. Call `set_context` with that `device_id` (and maybe the `space_id` for Room 101).
3. Call `send_command` with `name="reboot"` (no need to include device\_id because context provides it).
4. After command execution, call `device://{device_id}/status` or check `device://{device_id}/histories` to verify the reboot, as suggested by the tool’s `next_steps`.

Using context makes step 3 simpler and less error-prone, because you don’t have to carry the device ID through every call manually – the server remembers it for you.

## Error Handling

When a tool or resource call cannot be completed, the MCP server will raise an **MCPError** with a specific `code` and a descriptive `message`. Agents should be prepared to handle these errors. The error `code` is especially important, as it indicates the type of failure and thus how the agent might respond or recover. Here are common error codes and recommended strategies:

* **`missing_device_id` / `missing_context`:** These errors indicate that a required identifier was not provided. For example, an agent tried to call `send_command` without a device\_id and none was set in context, or called `set_context` without any context available. In this case, the agent should supply the missing information – e.g., ensure `device_id` is included or call `set_context` first. Essentially, it’s a prompt that the agent needs to specify something it left out.
* **`invalid_params` / `invalid_device_id` / `invalid_ticket_id`:** The input provided was of the wrong format or invalid. This could happen if an ID is malformed or empty, or a required field in a payload is missing/incorrect. The agent should double-check the values it’s sending. For instance, make sure device IDs and ticket IDs are strings (not numbers or null), and that required fields like ticket title/description are present. This is generally a bug in the agent’s logic or an unexpected input from the user – it should be corrected and the tool retried.
* **`device_not_found` / `ticket_not_found`:** The specified resource does not exist. The server tried to fetch or act on a device/ticket by ID and the Xyte API returned a 404 Not Found. The agent should interpret this as: “the given ID is wrong or the item has been removed.” Recovery might involve informing the user that the device or ticket wasn’t found, or suggesting to list available devices/tickets to pick a correct ID. If this occurred during an operation (say updating a ticket), it might mean the ticket was closed or deleted by someone else.
* **`rate_limited`:** Too many requests have been sent in a short time. The MCP server enforces a rate limit (e.g., 60 calls per minute by default) to avoid overloading the Xyte API. If an agent hits this limit, it will receive a `rate_limited` error. The agent should pause further actions for a brief period to let the window reset. A strategy could be to wait (e.g., for 1 minute) before retrying, and avoid making rapid repetitive calls. If the agent was in a loop, it should break out or slow down. This error exists to protect both the system and the agent’s integration from being throttled by the upstream API.
* **`timeout` / `network_error` / `service_unavailable`:** These codes indicate temporary connectivity or server issues. A `timeout` means the request to Xyte took too long and was aborted; `network_error` means there was a low-level network failure reaching the API (e.g., DNS failure or connection drop); `service_unavailable` corresponds to a 503 error, implying Xyte’s service is down or overloaded. In all these cases, the agent should assume the operation didn’t complete and **retry later**. The agent can inform the user of a temporary issue (“The server is not responding right now, I will try again shortly.”) and then try the same call after a delay. These errors are generally not caused by the agent’s logic but by external conditions. Usually, simply waiting and retrying is the best course (possibly with a limited number of attempts before giving up and logging an error).
* **`validation_error`:** This is related to `invalid_params` – it specifically means the data format failed validation (e.g., JSON schema didn’t match). The message may include details about what was expected. The agent should correct the format of the request payload.
* **`unknown_error`:** A catch-all for any unexpected exception. This means something happened that the server didn’t anticipate (could be a bug, an unhandled API response, etc.). The agent should not retry immediately, as the same unknown condition might persist. Instead, it may log the error, possibly notify a human operator or fallback to a safe default. From the user’s perspective, the agent can apologize and say it cannot complete the request due to an internal error. Since the cause is unclear, automated recovery is hard – often the best an agent can do is provide context (e.g., include the error message) for debugging.

When an MCPError is raised, the server’s HTTP response (if you’re using HTTP) will likely be a 4xx status with a JSON body containing the `code` and `message`. If you’re using an SDK or the agent is integrated in-process, it might surface as an exception object with those attributes. In either case, use the `code` to drive logic (as outlined above) and the `message` for logging or user-facing info if needed.

**Example:** If an agent tries to send a command without setting a device, it gets `{"code": "missing_device_id", "message": "device_id is required"}`. The agent should realize it forgot to specify which device, perhaps ask the user or infer the device from context, set it, and try again. If it gets `device_not_found`, it might say to the user “I couldn’t find that device – please check the ID or name.” If `rate_limited`, the agent could wait 60 seconds before continuing its sequence of actions.

By handling these errors gracefully, the agent will be more robust and user-friendly, rather than simply failing or getting stuck.

## Event Handling

The MCP server can queue external **events** (similar to webhook notifications) and provide them to agents on demand. This allows agents to react to asynchronous occurrences, such as device status changes or new tickets, in a controlled way.

Events are produced outside the agent’s direct requests – for example, Xyte’s cloud might send a webhook to the MCP server when a device goes offline. The server enqueues these events, and the agent can consume them using the **`get_next_event`** tool.

**Event Model:** Each event has a `type` (a short string describing what kind of event it is) and a `data` payload (a dictionary with details about the event). The server’s internal event model looks like:

```json
{
  "type": "<event_type>",
  "data": { ... }
}
```

For instance, an event could be: `{"type": "device_offline", "data": { "id": "device123", "timestamp": "...", ... }}` meaning device with ID "device123" went offline at a certain time.

**Producing Events:** The MCP server exposes a webhook endpoint (typically `/webhook`) where such event payloads can be posted. In a deployed scenario, you’d configure Xyte or other systems to send events (like device alerts) to this endpoint. In the test suite, for example, posting `{"type": "device_offline", "data": {"id": "abc"}}` to `/webhook` will enqueue an event. The event queue stores events in the order received.

**Consuming Events:** Agents use `get_next_event` to retrieve events. Key points about `get_next_event`:

* It can be called with an optional filter: `get_next_event({"event_type": "some_type"})`. If an `event_type` is provided, the tool will return the **next event of that type**. If no `event_type` is given, it returns the next event in the queue regardless of type.
* **Blocking behavior:** `get_next_event` will suspend (wait) until an event is available. The server implementation waits on the event queue; if the queue is empty, the call will not return until an event arrives (this is essentially a long-poll for events). This means an agent can call `get_next_event` and it will only respond when an event is delivered. If a filter is set, it will ignore other event types – the code will put unmatched events back into the queue and continue waiting. This ensures that events are not lost or skipped; they remain queued until the agent picks them up.
* **Non-Blocking usage:** If agents need to check for an event without waiting indefinitely, they might call `get_next_event` with a timeout or in a loop with a short wait. (The MCP server itself doesn’t provide a separate “peek” or non-blocking poll method; the agent side would handle timing out if needed.) In tests, for example, they wrapped `get_next_event` in a timeout to avoid waiting forever.
* **Return value:** When an event is retrieved, it will be returned as a JSON object (or Python dict) containing the `type` and `data`. For example, using the earlier posted event, `get_next_event({"event_type": "device_offline"})` would eventually return `{"type": "device_offline", "data": {"id": "abc"}}`. If no filter was used, it would return whichever event was next (which in this case is also that event). The event is then removed from the queue (consumed).

**Using Events in Agents:** Agents can use events to trigger actions without a user request. For instance, an agent could be running a loop that constantly listens for new events:

```python
while True:
    event = get_next_event({})
    if event["type"] == "device_offline":
        handle_device_offline(event["data"])
    elif event["type"] == "incident_created":
        notify_incident(event["data"])
    # ...and so on for different types
```

In a conversational AI context, the agent might call `get_next_event` when it needs to wait for something to happen (e.g., “I’ve triggered a reboot, now I will wait for a device\_offline -> online event to confirm it came back.”). In such a case, providing an `event_type` filter is useful so the agent only wakes up when the expected event arrives.

Common event types are likely things like `device_offline`, `device_online`, `device_error`, `incident_created`, `ticket_created`, etc., depending on what webhooks are configured. The `data` field will contain context for that event (device ID, or incident/ticket details, timestamps, etc.). The agent should parse those and decide on a response. For example, on `device_offline`, the agent could attempt to power-cycle the device (maybe using a prompt/workflow like the reboot workflow described later). On `ticket_created`, an agent could auto-respond or categorize the ticket.

**Error Handling for Events:** If `get_next_event` is called when the server is shutting down or the queue is unavailable, it might return an error or be cancelled, but normally this tool either returns an event or waits. There’s no “no event” return – it always waits until something is available (unless you implement a client-side timeout).

**Event Queue Persistence:** The event queue is in-memory. If the server restarts, queued events would be lost. Therefore, it’s wise to have agents consume events promptly. In a robust deployment, one might integrate a persistent message broker for events, but as implemented, it’s transient. Agents might want to periodically confirm they are connected and listening for events, so as not to miss any.

In summary, `get_next_event` enables **reactive behavior** in agents. Use it to handle asynchronous triggers, making your agent proactive and responsive to changes in the environment, not just user queries.

## Async Operations

Some device commands might take a noticeable amount of time to execute, or an agent might need to fire off a command and continue with other tasks. The MCP server provides asynchronous execution tools to accommodate this: **`send_command_async`** and **`get_task_status`**.

### send\_command\_async

`send_command_async` works much like the standard `send_command`, but instead of waiting for the command to complete, it returns immediately with a task identifier. The command execution then proceeds in the background on the server.

* **Inputs:** It accepts the same parameters as `send_command` (`device_id`, `name`, `friendly_name`, etc.). You should provide all necessary info to execute the command on the device. (Context defaults will apply here as well – if `device_id` is not given but context has one, it will use it.)
* **Behavior:** When invoked, the server generates a unique `task_id` (a UUID) for this command execution. It immediately returns a result containing this `task_id`, without waiting for the device to actually perform the command. Internally, the server schedules the command to run in the background. The initial status of the task is “pending”.
* **Return Value:** The direct response from `send_command_async` is a simple JSON object: `{"task_id": "<some-unique-id>"}`. This ID is what you’ll use to track the command’s progress.

For example:

```python
task_info = send_command_async({
    "device_id": "device123",
    "name": "reboot",
    "friendly_name": "Reboot Device"
})
# task_info might be {"task_id": "123e4567-e89b-12d3-a456-426614174000"}
task_id = task_info["task_id"]
```

At this point, the reboot command has been dispatched to run asynchronously. The agent can continue with other logic (or even prompt the user that it’s working in the background).

* The server, meanwhile, is executing the command in a background task. It will update the internal status when done. If the command succeeds, the result (data from the Xyte API) is stored in memory associated with the task ID, and status becomes "done". If the command fails (throws an exception), the status becomes "error" and the error message is saved. Throughout execution, it also reports progress (0% to 100%) to the context, which could be used for streaming status updates (though that’s more for logging/UI and not exposed via the get\_task\_status call).

### get\_task\_status

After initiating an async task, an agent uses `get_task_status` to query its state. You call it with the `task_id` you received:

```python
status = get_task_status({"task_id": task_id})
```

The output will be a dictionary describing the task’s state:

* `status`: a string indicating the state. It will be `"pending"` if the command is still in progress, `"done"` if it completed successfully, `"error"` if it failed, or `"unknown"` if the task ID is not recognized (e.g., if it’s wrong or too old and was purged).
* `result`: present when `status` is `"done"`. This contains the result data of the command (essentially what `send_command` would have returned if called synchronously). The structure is usually a dict or JSON – for example, if the command was a reboot, the result might include a confirmation or the command record. If `status` is not done, `result` may be `null` or absent.
* `error`: present when `status` is `"error"`. This will be a message string describing the error that occurred. (It might be a propagated error from Xyte’s API or a timeout message, etc.) If no error occurred, this is `null` or not present.

**Polling Mechanism:** Agents typically should poll `get_task_status` periodically if they need to wait for completion. For instance, an agent might check every few seconds, or use an exponential backoff (check after 1s, then 2s, then 4s, etc.) to see if the task finished. You can also immediately call it once right after `send_command_async` to get an initial status (likely “pending”).

Example usage:

```python
# Initiate the command asynchronously
task = send_command_async({ ... })
task_id = task["task_id"]

# Later, check the status
status_info = get_task_status({"task_id": task_id})
if status_info["status"] == "done":
    print("Command completed successfully.")
    result = status_info["result"]
elif status_info["status"] == "error":
    error_msg = status_info["error"]
    print(f"Command failed: {error_msg}")
else:
    # status is "pending" (or potentially "unknown" if something went wrong)
    print("Command still running, please check again later.")
```

In a conversation, the agent might say, "Reboot initiated, I'll let you know once it's done." and then use `get_task_status` in the background until it sees `"done"`, then inform the user.

**Important Considerations:**

* **Task Expiration:** The tasks are stored in-memory on the server in a dictionary. They will persist as long as the server is running. There isn’t a built-in expiration or cleanup (besides the dictionary naturally growing). If the server restarts, all ongoing tasks are lost (they’d all become “unknown”). In practice, this means your agent should handle an `"unknown"` status by possibly informing that the result is unavailable (and maybe suggesting to retry the operation if needed).
* **Concurrent tasks:** You can fire off multiple async commands in parallel (each will get its own `task_id`). Just be mindful not to overload the device or violate any sequential command constraints the device might have. The MCP server does not serialize these beyond what the Xyte API allows.
* **When to use async:** Use `send_command_async` when the action might take longer than you want to wait within a single agent turn, or when you want to perform other checks while the command runs. A common use case is a long-running firmware update or a reboot cycle – you start it asynchronously, then perhaps monitor device status via events or periodic checks, rather than blocking the agent completely.

In summary, asynchronous tools give the agent more flexibility and prevent it from getting stuck waiting. Just remember to always pair `send_command_async` with `get_task_status` (and possibly event handling) to know when the operation finished.

## Prompts for Troubleshooting & Automation

To help agents perform complex or common tasks, the MCP server defines some **predefined prompts/workflows**. These are essentially guided sequences or suggestions that an agent can follow to achieve a goal. They encapsulate best practices or standard procedures for automation tasks. Agents (especially AI agents) can use these prompts as a blueprint for what steps to take.

Currently, the server includes a couple of example prompts for troubleshooting scenarios:

* **Reboot Device Workflow:** This prompt (accessible via `reboot_device_workflow(device_id)`) provides step-by-step instructions to safely reboot an unresponsive device. It suggests the agent to:

    1. **Check available commands** on the device by querying the resource `device://{device_id}/commands` – this is to see if a reboot command is supported for that device.
    2. If a reboot command exists, **call the `send_command` tool** with `name="reboot"` (and the given device\_id) to execute a reboot.
    3. After sending the reboot, **verify success by checking the device’s history** via `device://{device_id}/histories` – confirming that a reboot event or status change is recorded.

  Essentially, this prompt guides an agent through a safe reboot procedure: first confirm capability, then act, then verify the outcome. An AI agent could use these steps to structure its actions when a device is not responding. By following the prompt, the agent ensures it uses the proper tools in the correct order.

* **Check Projectors Health:** This prompt (`check_projectors_health()`) is a high-level strategy for monitoring all projectors’ status. The guidance provided is:

    * **List all devices** using `devices://` and filter the list to find devices that are projectors (perhaps by type or name).
    * For each projector device, **inspect its history records** via `device://{device_id}/histories` to look for any recent errors or unusual events.
    * Also **check open incidents** using `incidents://` to see if any ongoing incident is related to those projectors.

  In summary, this prompt tells an agent how to systematically go through all projectors and evaluate their health, combining multiple resource queries. An agent following this could then report “All projectors are functioning normally” or identify ones with issues (and perhaps drill down further on those).

These prompts are registered with the MCP server as first-class prompts. In an AI agent integration, they might be used behind the scenes to influence the agent’s plan. For example, if an AI has access to a prompt library, it could call or retrieve these prompts when a relevant goal is identified (like “reboot device” or “check all projectors”). Each prompt is essentially a template of steps (in the form of either a list of messages or a single message string) that the agent can incorporate into its reasoning or explanation.

**How to Use Prompts:** Depending on your agent setup:

* If you have an AI agent that can retrieve prompts from the server, you might call an API or method to get the prompt by name. The prompt might come as a series of messages or instructions (the reboot workflow is stored as a list of User messages, each containing an instruction).
* The agent can then follow each step, executing the recommended tool/resource calls in sequence, and reporting back as needed.
* These prompts can also serve as **documentation for human agents**. A human operator could read the “Reboot Device Workflow” to manually follow those steps via the tools.

The idea is to encapsulate domain knowledge or troubleshooting flows so that agents don’t have to figure it all out from scratch. As the MCP server evolves, more prompts or workflows can be added (for example, a workflow to diagnose network issues, or to set up a new device step-by-step). Agents should check if a relevant prompt exists for a task they’re about to perform – it can save time and ensure best practices.

In the current implementation, prompts are limited (just the two above as examples), but they demonstrate how to combine resources and tools effectively. For instance, the reboot workflow prompt explicitly ties together a resource query (`device://.../commands`) with a tool action (`send_command`) and another resource check (`device://.../histories`). An agent using this will behave more reliably than one that improvises a sequence.

**Summary:** Predefined prompts give structured guidance for common tasks:

* *Troubleshooting prompts* (like reboot workflow) help recover or fix device issues.
* *Automation prompts* (like checking health across devices) help in routine monitoring.

Agents can leverage these to improve their performance. In practical terms, if you’re developing an AI agent, consider these prompts as part of the agent’s prompt (you might feed the steps into the AI’s context when such a task is needed). If you’re a human agent, you can follow the steps manually via the MCP tools and resources.

---

By following this guide, agents should be well-equipped to interact with the MCP server: authenticating properly, invoking the right tools with the right inputs, utilizing context to streamline operations, handling errors robustly, reacting to events, managing long-running commands, and using built-in knowledge to perform complex procedures. The combination of **tools** (for actions) and **resources** (for information) provides a powerful interface to the Xyte platform, all mediated through the MCP server in a consistent way. With these capabilities, an agent (or AI assistant) can automate device management tasks, assist IT/operators, and ensure things run smoothly in an AV/IoT environment.
