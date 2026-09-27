# Nexus Production Kubernetes Hardening & SRE Architecture

## Cluster High Availability & Control Plane
1. **Multi-AZ Control Plane**: Deploy across minimum 3 Availability Zones with dedicated etcd topologies. Use SSD-backed gp3 or io2 storage with guaranteed IOPS >= 3000 to prevent etcd leader election timeouts during write bursts.
2. **Pod Disruption Budgets (PDB)**: Every mission-critical deployment must declare a PDB specifying `minAvailable: 2` or `maxUnavailable: 25%` to safeguard service availability during voluntary disruptions (node draining, cluster upgrades).
3. **Topology Spread Constraints**: Use `topologySpreadConstraints` with `maxSkew: 1` along `topology.kubernetes.io/zone` to evenly distribute pods across failure domains.

## Security Context Hardening
Every production pod spec must enforce non-root execution and drop all Linux capabilities:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

## Zero-Downtime Rollouts
Ensure readiness probes test genuine application health rather than mere process existence:
- `initialDelaySeconds`: 15-30 seconds depending on JVM / Python cold startup.
- `periodSeconds`: 10 seconds.
- `failureThreshold`: 3 consecutive failures before removing pod from endpoint slice.
- Graceful shutdown: implement a `preStop` hook sleeping 5 seconds to allow Ingress/ALB controller to deregister endpoint before `SIGTERM`.
