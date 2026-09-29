# Running `crawl-stores` from Windows Task Scheduler

`python -m app.cli crawl-stores` crawls every store whose last complete crawl is older than its cadence
(`crawl_every_days` in `backend/app/collectors/stores/store_configs.yaml`, default 7). It is safe to run **daily**:
when nothing is due it exits in a few seconds, and running it twice in a row crawls nothing the second time. Nothing
in the app schedules it; you register it once, as below.

## What it does, and what it never does
- Stores are crawled **one after another**, each on its own polite delay. One store failing does not stop the others.
- A page that fails for a transient reason (a timeout, HTTP 429 or 5xx) is retried twice after 5 and 15 seconds; a facet
  (filter) page that still cannot be read never erases what was known: the previous value is kept, and the crawl is
  marked incomplete so it is retried the next day.
- A product is marked dropped only after a **complete** crawl whose listing did not shrink below 70 % of the store's
  active products. An incomplete or failed crawl is retried after 20 hours, not after a week.
- One crawl process at a time: an overlapping run (a second trigger, or a manual `crawl-store` during a scheduled run)
  finds the lock, prints "another crawl is running: nothing to do" and exits without touching anything.
- A run that is killed (reboot, task timeout) leaves the database as it was: the sync is one transaction per store. The
  next run marks the interrupted crawl as failed.
- Every crawl is one row in `store_crawls` (status, counts, why drops were skipped). Output is appended to
  `backend\data\logs\crawl-stores.log`.

## 1. Check it first (no crawl, nothing written)
```powershell
cd C:\Users\chaki\eyewear-trends\backend
.\.venv\Scripts\python.exe -m app.cli crawl-stores --dry-run
```
Lists each store as `DUE` or `skip` with the reason. On a fresh setup all stores are due ("never crawled").

## 2. Run it once by hand
```powershell
C:\Users\chaki\eyewear-trends\tools\crawl-stores.cmd
```
The first run crawls every store (about 1 to 1.5 hours in total) and is the first time drops can change the live data.
Read the log afterwards.

## 3. Register the task (daily at 03:00)
```powershell
$repo = "C:\Users\chaki\eyewear-trends"
$action = New-ScheduledTaskAction -Execute "$repo\tools\crawl-stores.cmd" -WorkingDirectory "$repo\backend"
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "EyewearTrends-CrawlStores" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Crawl the eyewear stores that are due (see docs/crawl-stores-task-scheduler.md)"
```
- `-StartWhenAvailable`: a laptop that was asleep at 03:00 runs the task when it wakes.
- `-MultipleInstances IgnoreNew`: a second trigger during a long crawl is ignored (the lock also guards this).
- `-ExecutionTimeLimit 6h`: a hard stop; each store also has its own 3 h cap.

Run it now from the Task Scheduler UI, or: `Start-ScheduledTask -TaskName "EyewearTrends-CrawlStores"`.

## Reading "Last Run Result"
| code | meaning |
|---|---|
| `0` | all fine, or nothing was due |
| `1` | at least one store **failed** (its error is in the log and in `store_crawls`), or the config is invalid |
| `2` | nothing failed, but a crawl was **incomplete** or skipped its drops: read the log, then run `python -m app.cli crawl-store DOMAIN` |

A weekly trigger works too, but a daily one is what gives the next-day retry.

## Remove it
```powershell
Unregister-ScheduledTask -TaskName "EyewearTrends-CrawlStores" -Confirm:$false
```

## Useful manual commands
```powershell
python -m app.cli crawl-stores etniabarcelona.com --force   # one store now, ignoring its cadence
python -m app.cli crawl-store etniabarcelona.com            # same, with --accept-drops available for a real catalog cull
```
