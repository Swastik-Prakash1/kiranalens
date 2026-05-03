#!/usr/bin/env python3
"""Verify all KiranaLens dependencies are installed."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

packages = [
    ("fastapi","fastapi"), ("uvicorn","uvicorn"),
    ("huggingface_hub","huggingface_hub"), ("ultralyticsplus","ultralyticsplus"),
    ("ultralytics","ultralytics"), ("cv2","cv2"), ("PIL","PIL"),
    ("numpy","numpy"), ("osmnx","osmnx"), ("overpy","overpy"),
    ("geopy","geopy"), ("httpx","httpx"), ("pydantic","pydantic"),
    ("scipy","scipy"), ("aiofiles","aiofiles"), ("requests","requests"),
]
all_ok = True
for name, imp in packages:
    try:
        __import__(imp)
        print(f"[OK] {name}")
    except ImportError as e:
        print(f"[FAIL] {name} -- {e}")
        all_ok = False
print("\n[ALL OK]" if all_ok else "\n[FIX FAILURES BEFORE CONTINUING]")
