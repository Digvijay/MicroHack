"""Start Foundry Local so that it does NOT need the internet to start (challenge 6).

The `foundry` service loads its model catalog from the internet every time it starts. If it is restarted while
the device is offline, it cannot find any model, even models that are already on the disk. This script starts the
service from the Foundry Local Python SDK instead, with a catalog that is never contacted. It finds the models
in your local cache and serves them on the same kind of OpenAI-compatible address.

  python serve_offline.py                        serves phi-4-mini and qwen3-embedding-0.6b on port 5272
  python serve_offline.py phi-4-mini --port 5300
  python serve_offline.py --accelerate           also try the GPU/NPU variants (see the note below)

In another terminal, point the lab code at it:

  set FOUNDRY_LOCAL_URL=http://127.0.0.1:5272/v1          (PowerShell: $env:FOUNDRY_LOCAL_URL = "http://127.0.0.1:5272/v1")

Download the models first, while you are online (challenge 1). Use `pip install foundry-local-sdk` before you disconnect.

Note on GPU and NPU: those model variants need an "execution provider" to be registered, which may download it.
By default this script therefore uses the CPU variants, which need nothing from the internet.
"""
import argparse
import json
import os
import time
from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager, LogLevel

SERVED = Path(os.environ.get("FOUNDRY_SERVED_MODELS", Path.home() / ".foundry" / "served_models.json"))
LOOPBACK_CATALOG = ("http://127.0.0.1:9", None)  # nothing listens here, so the catalog fails at once instead of timing out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aliases", nargs="*", default=["phi-4-mini", "qwen3-embedding-0.6b"])
    ap.add_argument("--port", type=int, default=5272)
    ap.add_argument("--cache", default=os.environ.get("FOUNDRY_CACHE", str(Path.home() / ".foundry" / "cache" / "models")))
    ap.add_argument("--accelerate", action="store_true", help="also try GPU/NPU variants (may need the internet once)")
    args = ap.parse_args()

    config = Configuration(
        app_name="offline-copilot", model_cache_dir=args.cache, log_level=LogLevel.WARNING,
        catalog_urls=[LOOPBACK_CATALOG], web=Configuration.WebService(urls=f"http://127.0.0.1:{args.port}"))
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    if args.accelerate:
        try:
            manager.download_and_register_eps(progress_callback=lambda *a: None)
        except Exception as e:  # offline: carry on with the CPU variants
            print(f"Could not register GPU/NPU providers ({str(e)[:80]}). Using CPU variants.")

    cached = manager.catalog.get_cached_models()
    served = {}
    for alias in args.aliases:
        variants = [v for v in cached if v.alias == alias]
        # CPU variants first unless --accelerate: they need no execution provider
        variants.sort(key=lambda v: ("cpu" not in v.id.lower()) == args.accelerate)
        for variant in variants:
            try:
                variant.load()
                served[alias] = variant.id
                print(f"loaded {alias:<24} -> {variant.id}")
                break
            except Exception as e:
                print(f"  could not load {variant.id}: {str(e)[:100]}")
        else:
            raise SystemExit(f"'{alias}' is not in the local cache ({args.cache}). Download it first: foundry model download {alias}")

    manager.start_web_service()
    SERVED.parent.mkdir(parents=True, exist_ok=True)
    SERVED.write_text(json.dumps(served, indent=2), encoding="utf-8")
    url = manager.urls[0].rstrip("/") + "/v1"
    print(f"\nServing on {url}\nIn another terminal:  $env:FOUNDRY_LOCAL_URL = \"{url}\"\nPress Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_web_service()
        SERVED.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
