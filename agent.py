# -*- coding: utf-8 -*-
"""مصروفي: اكتب مصروفك بكلامك، والنموذج اللي دربته يسجّله.

    python agent.py              # يستخدم النموذج masrufi
    python agent.py qwen3:1.7b   # جرّب النموذج الأصلي وقارن
"""
import csv
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

from llm import extract

MODEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MASRUFI_MODEL", "masrufi")
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.csv")
FIELDS = ["date", "item", "amount", "category"]
OFFSET = {"اليوم": 0, "أمس": 1, "قبل أمس": 2}
CONFIRM_ABOVE = 1000

HELP = """اكتب مصروفك مثل: «دفعت ٢٥ ريال قهوة» أو «تغديت ب٤٠ أمس وعبيت بنزين ب٨٠»
الأوامر: ملخص · آخر · تراجع · خروج"""


def load():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(rows):
    with open(LEDGER, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def add(expenses):
    rows = load()
    for e in expenses:
        day = date.today() - timedelta(days=OFFSET[e["when"]])
        rows.append({"date": day.isoformat(), "item": e["item"], "amount": f"{e['amount']:g}", "category": e["category"]})
    save(rows)


def summary():
    rows = load()
    if not rows:
        return "ما فيه مصاريف مسجلة للحين."
    since = (date.today() - timedelta(days=6)).isoformat()
    week = [r for r in rows if r["date"] >= since]
    totals = defaultdict(float)
    for r in week:
        totals[r["category"]] += float(r["amount"])
    lines = [f"  {cat}: {amount:g} ريال" for cat, amount in sorted(totals.items(), key=lambda kv: -kv[1])]
    return f"آخر ٧ أيام: {sum(totals.values()):g} ريال\n" + "\n".join(lines)


def last(n=5):
    rows = load()[-n:]
    return "\n".join(f"  {r['date']}  {r['item']}  {r['amount']} ({r['category']})" for r in rows) or "ما فيه شي."


def undo():
    rows = load()
    if not rows:
        return "ما فيه شي أتراجع عنه."
    removed = rows.pop()
    save(rows)
    return f"شلت: {removed['item']} {removed['amount']} ريال"


def handle(text):
    command = text.strip()
    if command in ("ملخص", "الملخص"):
        return summary()
    if command in ("آخر", "اخر"):
        return last()
    if command in ("تراجع", "الغاء", "إلغاء"):
        return undo()
    if command in ("مساعدة", "؟", "?"):
        return HELP

    expenses, problems = extract(MODEL, text)
    if not expenses:
        return "ما لقيت مصروف أسجله." + (f" ({'، '.join(problems)})" if problems else "")
    big = [e for e in expenses if e["amount"] > CONFIRM_ABOVE]
    if big and input(f"المبلغ {big[0]['amount']:g} ريال كبير، أسجله؟ (نعم/لا) ").strip() not in ("نعم", "ايه", "اي", "y"):
        return "ما سجلت شي."
    add(expenses)
    done = "\n".join(f"  ✓ {e['item']}: {e['amount']:g} ريال · {e['category']} · {e['when']}" for e in expenses)
    return "سجلت:\n" + done + (f"\nملاحظة: {'، '.join(problems)}" if problems else "")


def main():
    print(f"مصروفي · النموذج: {MODEL}\n{HELP}\n")
    while True:
        try:
            text = input("أنت: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text in ("خروج", "exit", "quit"):
            break
        if text:
            try:
                print(handle(text), "\n")
            except OSError:
                print("ما قدرت أوصل لـ Ollama. تأكد إنه شغال: ollama serve\n")


if __name__ == "__main__":
    main()
