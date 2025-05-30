# Galaxus Pricing Demo

A small reference implementation that shows how to:

* read a CSV of SKUs,
* enqueue scrape tasks on Azure Service Bus,
* consume them asynchronously in a worker pool,
* push the resulting price events to Azure Event Hubs (Kafka API).

Everything runs in Azure Container Apps Jobs.
All code is Python 3.12 and packaged into two multi-arch Docker images (`linux/amd64`, `linux/arm64`).

---

## 1. Repository layout

```
galaxus-pricing/
├─ discovery/            seed CSVs
├─ common/               helpers
│   └─ config.py         CSV → YAML
├─ config/
│   └─ sites.yml         generated at build-time
├─ scheduler/            scheduler job (enqueue)
│   ├─ Dockerfile
│   ├─ requirements.txt
│   └─ main.py
├─ scraper_pool/         worker job (dequeue + scrape)
│   ├─ Dockerfile
│   ├─ requirements.txt
│   └─ worker.py
├─ plugins/              per-shop logic
│   ├─ __init__.py
│   └─ interdiscount.py  (async stub)
└─ README.md
```

---

## 2. Local quick-start (no Azure)

```bash
# clone and enter
git clone https://github.com/valentinneher/galaxus-pricing.git
cd galaxus-pricing

# generate config/sites.yml from the CSV
python common/config.py
```

### Run scheduler once (prints “sent … tasks”)

```bash
docker build -t dg-scheduler:dev -f scheduler/Dockerfile .
docker run --rm \
  -e SB_CONN="Endpoint=sb://localhost/..." \
  -e SB_QUEUE=scrape-tasks \
  dg-scheduler:dev
```

### Run scraper (uses stub plugin)

```bash
docker build -t dg-scraper:dev -f scraper_pool/Dockerfile .
docker run --rm \
  -e SB_CONN="Endpoint=sb://localhost/..." \
  -e SB_QUEUE=scrape-tasks \
  -e EH_BOOTSTRAP="localhost:9092" \
  -e EH_SASL_USERNAME='$ConnectionString' \
  -e EH_SASL_PASSWORD="Endpoint=sb://localhost/..." \
  -e EH_TOPIC=competitor-prices \
  dg-scraper:dev
```

The scheduler writes messages to the queue; the scraper consumes them and prints one JSON line per SKU.

---

## 3. Building multi-arch images

```bash
# scheduler
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t docker.io/<you>/dg-scheduler:latest \
  -f scheduler/Dockerfile . --push

# scraper
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t docker.io/<you>/dg-scraper:latest \
  -f scraper_pool/Dockerfile . --push
```

Both tags become one manifest containing two architectures.

---

## 4. Azure deployment (minimum)

### 4.1 Infrastructure

```bash
az group create -g galaxus-demo -l switzerlandnorth

# Service Bus
az servicebus namespace create -g galaxus-demo -n galaxus-sb-ns
az servicebus queue     create -g galaxus-demo -n scrape-tasks --namespace-name galaxus-sb-ns
SB_CONN=$(az servicebus namespace authorization-rule keys list \
           -g galaxus-demo -n galaxus-sb-ns --name RootManageSharedAccessKey \
           --query primaryConnectionString -o tsv)

# Event Hubs
az eventhubs namespace create -g galaxus-demo -n galaxus-eh-ns
az eventhubs eventhub  create -g galaxus-demo -n competitor-prices \
                          --namespace-name galaxus-eh-ns
EH_CONN=$(az eventhubs namespace authorization-rule keys list \
           -g galaxus-demo -n galaxus-eh-ns --name RootManageSharedAccessKey \
           --query primaryConnectionString -o tsv)
```

### 4.2 Container Apps managed environment

```bash
az containerapp env create -g galaxus-demo -n galaxus-ca-env -l switzerlandnorth
```

### 4.3 Scheduler job (5-min cron + manual)

```bash
az containerapp job create -g galaxus-demo -n scheduler-job \
  --environment galaxus-ca-env \
  --image docker.io/<you>/dg-scheduler:latest \
  --trigger-type scheduled \
  --schedule "*/5 * * * *" \
  --parallelism 1 --replica-completion-count 1 \
  --set-env-vars SB_CONN=secretref:sb-conn SB_QUEUE=scrape-tasks \
                 CONFIG_URL=https://raw.githubusercontent.com/<you>/galaxus-pricing/main/config/sites.yml \
  --manual-trigger-config parallelism=1 replica-completion-count=1

az containerapp job secret set -g galaxus-demo -n scheduler-job --secrets sb-conn="$SB_CONN"
```

### 4.4 Scraper job (manual trigger)

```bash
az containerapp job create -g galaxus-demo -n scraper-job \
  --environment galaxus-ca-env \
  --image docker.io/<you>/dg-scraper:latest \
  --trigger-type manual \
  --parallelism 1 --replica-completion-count 1 \
  --set-env-vars \
     SB_CONN=secretref:sb-conn SB_QUEUE=scrape-tasks \
     EH_BOOTSTRAP=galaxus-eh-ns.servicebus.windows.net:9093 \
     EH_SASL_USERNAME='$ConnectionString' \
     EH_SASL_PASSWORD=secretref:eh-pass \
     EH_TOPIC=competitor-prices

az containerapp job secret set -g galaxus-demo -n scraper-job \
  --secrets sb-conn="$SB_CONN" eh-pass="$EH_CONN"
```

---

## 5. Day-to-day commands

| Action              | Command                                                                                                                                                                       |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| run scheduler now   | `az containerapp job start -g galaxus-demo -n scheduler-job`                                                                                                                  |
| run scraper now     | `az containerapp job start -g galaxus-demo -n scraper-job`                                                                                                                    |
| tail scheduler logs | `az containerapp job logs show -g galaxus-demo -n scheduler-job --container scheduler-job --follow`                                                                           |
| tail scraper logs   | `az containerapp job logs show -g galaxus-demo -n scraper-job --container scraper-job --follow`                                                                               |
| queue depth         | `az servicebus queue show -g galaxus-demo --namespace-name galaxus-sb-ns -n scrape-tasks --query countDetails.activeMessageCount`                                             |
| peek Kafka          | `kcat -b galaxus-eh-ns.servicebus.windows.net:9093 -C -t competitor-prices -X sasl.username=$ConnectionString -X sasl.password="$EH_CONN" -X security.protocol=SASL_SSL -c 5` |

---

## 6. Extending the demo

* Add another retailer: drop a CSV in `discovery/`, run `common/config.py`, add a `plugins/<shop>.py`, and adjust `shop` in scheduler messages.
* Swap the stub plugin for real scraping (use Playwright or an edge proxy).
* Replace Event Hubs with Cosmos DB or Materialize if you prefer SQL analytics.
* Add KEDA scaling rules to let the scraper pool grow with queue backlog.

---

## 7. Troubleshooting

| Symptom                                        | Checklist                                                                                                |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Scheduler prints “sent …” but queue stays at 0 | Verify `SB_CONN` host matches the namespace you query; connection string must not contain `EntityPath=`. |
| `ModuleNotFoundError: aiohttp` in scraper      | Ensure `aiohttp` is in `scraper_pool/requirements.txt`; rebuild image.                                   |
| `No module named 'plugins'`                    | Docker context must include `plugins/` directory (`COPY plugins/ ./plugins/` or build from repo root).   |
| Kafka auth failure                             | `EH_SASL_USERNAME` must be the literal `$ConnectionString`; password is the full EH connection string.   |
