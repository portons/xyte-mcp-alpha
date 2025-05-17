# XYTE API Wrappers

## Tools

| Name | Parameters |
| ---- | ---------- |
| `claim_device` | name, space_id, mac, sn, cloud_id |
| `delete_device` | device_id |
| `update_device` | device_id, configuration |
| `send_command` | name, friendly_name, file_id, extra_params, device_id |
| `cancel_command` | name, friendly_name, file_id, extra_params, device_id, command_id |
| `update_ticket` | ticket_id, title, description |
| `mark_ticket_resolved` | ticket_id |
| `send_ticket_message` | ticket_id, message |
| `search_device_histories` | status, from_date, to_date, device_id, space_id, name |

## Resources

| URI | Name |
| --- | ---- |
| `devices://` | list_devices |
| `incidents://` | list_incidents |
| `tickets://` | list_tickets |
| `device://{device_id}/commands` | list_device_commands |
| `device://{device_id}/histories` | list_device_histories |
| `organization://info/{device_id}` | organization_info |
| `ticket://{ticket_id}` | get_ticket |

