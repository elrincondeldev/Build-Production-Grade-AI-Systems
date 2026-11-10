# Kubernetes preview manifests

These manifests describe how `fraud-service` will run on Kubernetes. **You do not deploy them in Module 1.** Read them alongside [lesson 1.5](../../05-artifacts-and-containers.md#6-kubernetes-in-one-page) and map each field to the concept it implements.

| File | Kubernetes object | Concept |
|---|---|---|
| `deployment.yaml` | Deployment | Desired state: 2 replicas, rolling updates, probes, resources, non-root |
| `service.yaml` | Service | Stable name and load balancing across *ready* pods only |
| `configmap.yaml` | ConfigMap | Non-secret config as env vars (12-factor) |
| `secret.example.yaml` | Secret | Where secrets go (example only, never commit real ones) |

If you already have a cluster configured in `kubectl`, you can ask the API server to validate the files without deploying anything (this needs a reachable cluster; without one, just read the files):

```bash
kubectl apply --dry-run=server -f k8s/
```

In **Module 6** you will create a local cluster with `kind`, load this image, deploy it with a canary, and watch readiness gates protect a bad release.
