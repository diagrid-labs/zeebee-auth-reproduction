# Zeebe OAuth token reuse (Dapr, Kubernetes)

In this repro you run the Zeebe command output binding against mock OAuth and mock Zeebe gateways. The Camunda client on `daprd` caches OAuth tokens under `/camunda/credentials.yaml`; the OAuth mock counts `POST /token` so you can see reuse until `expires_in` (from `OAUTH_EXPIRES_IN_SECONDS`, 45s in `k8s/oauth-mock.yaml`) passes.

This repro includes three Deployments:

- OAuth mock — issues tokens; `GET /stats` returns `oauth_token_posts`.
- Zeebe mock — minimal gRPC gateway (no real Camunda cluster).
- App — workload plus `daprd` (Zeebe binding, writes the credential cache).

Manifests: `k8s/oauth-mock.yaml`, `k8s/zeebe-mock.yaml`, `k8s/app.yaml`. Use comma-separated `dapr.io/env` `KEY=value` pairs in `k8s/app.yaml` so `ZEEBE_*` reach the sidecar.

## Prerequisites

- `kubectl`, Docker, a local Kubernetes cluster (e.g. Minikube)
- Dapr on the cluster: `dapr init -k` (`dapr-system` namespace)

## Deploy

From the repo root, build images into the cluster’s Docker (Minikube example):

```bash
eval $(minikube docker-env)
docker build -t zeebe-token-repro-oauth-mock:latest ./stack/oauth-mock
docker build -t zeebe-token-repro-zeebe-mock:latest ./stack/zeebe-mock
```

Apply:

```bash
kubectl apply -f k8s/00-namespace.yaml -f k8s/oauth-mock.yaml -f k8s/zeebe-mock.yaml \
  -f k8s/dapr-config.yaml -f k8s/component-zeebe.yaml -f k8s/app.yaml
```

Wait for rollouts. `daprd` uses an `emptyDir` at `/camunda` for `credentials.yaml`; the app container mounts it read-only.

After editing `stack/oauth-mock/app.py`, rebuild the OAuth image, re-apply `k8s/oauth-mock.yaml`, and restart the `oauth-mock` Deployment.

## Run

1. Port-forward (two terminals):

   ```bash
   kubectl port-forward -n zeebe-token-repro svc/zeebe-test-app 3500:3500
   kubectl port-forward -n zeebe-token-repro svc/oauth-mock 8080:8080
   ```

2. In a third terminal, call stats, invoke topology several times, stats again, wait past expiry, invoke again:

   ```bash
   curl -s http://127.0.0.1:8080/stats

   for i in 1 2 3 4 5; do
     curl -sf -X POST http://127.0.0.1:3500/v1.0/bindings/zeebe-cmd \
       -H 'Content-Type: application/json' \
       -d '{"operation":"topology","metadata":{},"data":{}}' -o /dev/null && echo ok
   done

   curl -s http://127.0.0.1:8080/stats

   sleep 50

   for i in 1 2 3; do
     curl -sf -X POST http://127.0.0.1:3500/v1.0/bindings/zeebe-cmd \
       -H 'Content-Type: application/json' \
       -d '{"operation":"topology","metadata":{},"data":{}}' -o /dev/null && echo ok
   done

   curl -s http://127.0.0.1:8080/stats
   ```

3. Optional — read the cache from the app container (`daprd` is distroless):

   ```bash
   POD=$(kubectl get pod -n zeebe-token-repro -l app=zeebe-test-app -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n zeebe-token-repro -c app "$POD" -- cat /camunda/credentials.yaml
   ```

   Example output (expiry timestamps will differ):

   ```yaml
   zeebe-audience:
       auth:
           credentials:
               accesstoken: mock-access-token
               tokentype: Bearer
               refreshtoken: ""
               expiry: 2026-04-02T11:30:19.963171047Z
               expiresin: 0
   ```

You should see `oauth_token_posts` go from 0 → 1 after the first batch (token reuse), then 1 → 2 after `sleep 50` and more topology calls once the short-lived token expires.

## Configuration

Zeebe binding and Dapr config live in `k8s/component-zeebe.yaml` and `k8s/dapr-config.yaml`.
