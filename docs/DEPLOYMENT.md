# Deployment Guide

This project provides a Helm chart and raw Kubernetes manifests for deploying the
MCP server.

## Installing with Helm

1. Ensure you have `helm` installed and access to a Kubernetes cluster.
2. Set the required API key and install the chart:
   ```bash
   helm install xyte ./helm \
     --set env.XYTE_API_KEY=YOUR_KEY
   ```
3. Override `image.repository` or `image.tag` if you push a custom image.

## Key Values

- **image.repository** – Docker image to run.
- **image.tag** – Image tag, defaults to `latest`.
- **service.type** – Service type (`ClusterIP`, `LoadBalancer`, etc.).
- **env.*** – Environment variables passed through to the container.

See `helm/values.yaml` for the full list of configurable options.

## Raw Manifests

The `k8s/` directory contains plain manifests matching the chart. Apply them
with `kubectl apply -f k8s/` if you prefer not to use Helm.

## Upgrades and Rollbacks

Upgrade the release with:
```bash
helm upgrade xyte ./helm -f my-values.yaml
```
If something goes wrong you can roll back:
```bash
helm rollback xyte
```
