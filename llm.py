# -*- coding: utf-8 -*-
"""Talk to a local Ollama model and turn its reply into a checked list of expenses."""
import json
import os
import re
import urllib.error
import urllib.request

from make_data import CATEGORIES, SYSTEM

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
WHEN_VALUES = {"اليوم", "أمس", "قبل أمس"}
MAX_AMOUNT = 50_000


def chat(model, text, timeout=120):
    """Send one message to Ollama and return the raw reply text."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
        "stream": False,
        "think": False,                      # base qwen3 would otherwise reason before answering
        "options": {"temperature": 0},
    }
    try:
        return _post("/api/chat", payload, timeout)["message"]["content"]
    except urllib.error.HTTPError as err:
        if err.code != 400:
            raise
        payload.pop("think")                 # models without a thinking mode reject the flag
        return _post("/api/chat", payload, timeout)["message"]["content"]


def _post(path, payload, timeout):
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse(reply):
    """Pull the JSON object out of a reply. Returns a dict, or None if there is none."""
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
    start, end = reply.find("{"), reply.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        data = json.loads(reply[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and isinstance(data.get("expenses"), list) else None


def to_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        digits = value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
        found = re.search(r"\d+(\.\d+)?", digits)
        if found:
            return float(found.group())
    return None


def check(data):
    """Guardrails: keep only expenses that make sense, and say what was dropped."""
    kept, problems = [], []
    for e in data.get("expenses", []):
        if not isinstance(e, dict):
            problems.append("سطر غير مفهوم")
            continue
        amount = to_number(e.get("amount"))
        if amount is None or amount <= 0:
            problems.append(f"مبلغ غير واضح في «{e.get('item', '؟')}»")
            continue
        if amount > MAX_AMOUNT:
            problems.append(f"مبلغ كبير جداً ({amount:g}) تجاهلته")
            continue
        category = e.get("category") if e.get("category") in CATEGORIES else "أخرى"
        when = e.get("when") if e.get("when") in WHEN_VALUES else "اليوم"
        item = str(e.get("item") or category).strip()[:40]
        kept.append({"item": item, "amount": amount, "category": category, "when": when})
    return kept, problems


def extract(model, text):
    """Message in, (expenses, problems) out. Never raises on a bad model reply."""
    data = parse(chat(model, text))
    if data is None:
        return [], ["النموذج ما رجّع JSON صالح"]
    return check(data)
