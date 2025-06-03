# Security Policy

This document outlines best practices for keeping deployments of the Xyte MCP server secure.

## Security Best Practices

- **Keep dependencies up to date.** Regularly update this project and its Python dependencies to receive the latest security fixes.
- **Run the server in a minimal container.** Use the provided Dockerfile or a similarly hardened image and avoid running as the root user.
- **Restrict network access.** Only expose the necessary ports and run the server behind your firewall when possible.
- **Use least privilege.** API keys and user tokens should have the minimal permissions required for their task.
- **Always use TLS.** Terminate HTTPS in front of the server to prevent credential leakage.

## Reporting Vulnerabilities

If you believe you have found a security vulnerability, please responsibly disclose it by emailing <security@example.com> with a detailed description. We will respond as quickly as possible and work with you on a fix.

## Token and Secret Management

- **Environment files.** Store secrets such as `XYTE_API_KEY` in an `.env` file or as environment variables. Never commit secrets to version control.
- **Secret rotation.** Rotate API keys and tokens on a regular schedule. When rotating, update the `.env` file or your secret store and restart the server so new credentials take effect.
- **Centralized secret stores.** In production, prefer a dedicated secrets manager (like HashiCorp Vault or your cloud provider's solution) over plain files.

For additional guidance on environment configuration, see `.env.example` and the sections below.
