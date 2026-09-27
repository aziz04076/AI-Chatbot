# Nexus Cloud Zero-Trust & Identity Hardening Architecture

## Principles of Zero-Trust
1. **Explicit Verification**: Always authenticate and authorize based on all available data points (identity, location, device health, service context).
2. **Least Privilege Access**: Grant access via Just-In-Time (JIT) and Just-Enough-Access (JEA) with short-lived STS tokens.
3. **Assume Breach**: Segment networks into micro-perimeters; encrypt data in transit (mTLS via Istio) and at rest (AWS KMS with customer-managed keys).

## Kubernetes Secret Management
Never store plaintext secrets in ConfigMaps or Git. Use external secrets operators:
- **AWS Secrets Manager / HashiCorp Vault** synced dynamically via `ExternalSecretsOperator` (`external-secrets.io`).
- Mount secrets as memory-backed files (`tmpfs`) rather than environment variables to avoid leaking credentials via process inspection (`/proc/$PID/environ`).
