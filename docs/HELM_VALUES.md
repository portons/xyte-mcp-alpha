# Helm `values.yaml` Reference

This document describes the configurable values available when deploying the MCP server using the provided Helm chart.

| Key | Description | Default |
| --- | ----------- | ------- |
| `replicaCount` | Number of replicas of the deployment | `1` |
| `image.repository` | Docker image repository | `xyte-mcp` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Kubernetes image pull policy | `IfNotPresent` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port exposed by the container | `80` |
| `env.XYTE_API_KEY` | Xyte organization API key | `""` (must be set) |
| `env.XYTE_BASE_URL` | Base URL for the Xyte API | `https://hub.xyte.io/core/v1/organization` |
| `env.XYTE_USER_TOKEN` | Optional per-user token | `""` |
| `env.XYTE_CACHE_TTL` | Cache TTL for API responses | `60` |
| `env.XYTE_ENV` | Deployment environment label | `prod` |
| `env.XYTE_RATE_LIMIT` | Requests per minute allowed by the MCP | `60` |
| `env.MCP_INSPECTOR_PORT` | Port for the inspector service | `8080` |

These values can be overridden via the command line or a custom `values.yaml` when installing the chart:

```bash
helm install my-mcp ./helm -f my-values.yaml
```

