# Zeebe OAuth token reuse (Dapr, Kubernetes)

Small repro: Dapr **Zeebe command** binding + mocks. The OAuth server returns **`expires_in`** from **`OAUTH_EXPIRES_IN_SECONDS`** (**45s** in `k8s/oauth-mock.yaml`). The Camunda Zeebe client caches tokens at **`ZEEBE_CLIENT_CONFIG_PATH`** → **`/camunda/credentials.yaml`** on **`daprd`**. **`GET /stats`** on the mock reports **`oauth_token_posts`** (count of **`POST /token`**).

Example: **`oauth_token_posts`** **`0` → `1`** after several topology invokes (reuse within TTL), then **`1` → `2`** after **`sleep 50`** and more invokes past the short expiry. **`credentials.yaml`** is readable from the **app** container (`daprd` is distroless).

**Layout:**

- **OAuth mock** — fake token issuer (`POST /token`, **`/stats`**); mirrors identity separate from the broker.
- **Zeebe mock** — fake Zeebe gateway (gRPC); no real Camunda cluster needed.
- **`k8s/oauth-mock.yaml`**, **`k8s/zeebe-mock.yaml`**, **`k8s/app.yaml`** — one Deployment each: the two mocks are those backends; **`app`** is the workload + **`daprd`** (Zeebe binding, credential cache).

---

## Setup

**Need:** `kubectl`, Minikube (or similar), Docker, Dapr on the cluster (`dapr init -k` → **`dapr-system`**). **`dapr.io/env`** must be comma-separated **`KEY=value`** (not JSON) so `ZEEBE_*` reach **`daprd`** (`k8s/app.yaml`).

**Build mocks** (Minikube: `eval $(minikube docker-env)`), from **`zeebe-token-repro`**:

```bash
eval $(minikube docker-env)
docker build -t zeebe-token-repro-oauth-mock:latest ./stack/oauth-mock
docker build -t zeebe-token-repro-zeebe-mock:latest ./stack/zeebe-mock
```

**Apply:**

```bash
kubectl apply -f k8s/00-namespace.yaml -f k8s/oauth-mock.yaml -f k8s/zeebe-mock.yaml \
  -f k8s/dapr-config.yaml -f k8s/component-zeebe.yaml -f k8s/app.yaml
```

Wait for rollouts. **Persistence:** **`emptyDir`** `camunda-cache` at **`/camunda`**; **`daprd`** writes **`/camunda/credentials.yaml`**. **App** mounts it read-only: **`kubectl exec -n zeebe-token-repro -c app <pod> -- cat /camunda/credentials.yaml`**.

After changing **`stack/oauth-mock/app.py`**: rebuild the image, **`kubectl apply -f k8s/oauth-mock.yaml`**, rollout restart **`oauth-mock`**.

---

## Run

**Port-forwards** (two terminals): **`zeebe-test-app` 3500**, **`oauth-mock` 8080** → localhost.

```bash
kubectl port-forward -n zeebe-token-repro svc/zeebe-test-app 3500:3500
kubectl port-forward -n zeebe-token-repro svc/oauth-mock 8080:8080
```

**Third terminal:**

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

**Inspect:** `POD=$(kubectl get pod -n zeebe-token-repro -l app=zeebe-test-app -o jsonpath='{.items[0].metadata.name}')` then

**`kubectl exec -n zeebe-token-repro -c app "$POD" -- cat /camunda/credentials.yaml`**.

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
