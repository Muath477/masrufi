# -*- coding: utf-8 -*-
"""Generate Gulf-Arabic expense messages with their JSON labels.

    python make_data.py            -> data/train.jsonl, data/test.jsonl

Every line is {"text": ..., "label": {"expenses": [...]}}.
An expense is {"item", "amount", "category", "when"}; a message that records
no money spent (a question, a plan, income, a greeting) has "expenses": [].
"""
import json
import os
import random

CATEGORIES = ["مطاعم", "قهوة", "بقالة", "مواصلات", "فواتير", "تسوق", "صحة", "ترفيه", "أخرى"]

SYSTEM = (
    "أنت تسجّل المصاريف. حوّل رسالة المستخدم إلى JSON فقط بهذا الشكل:\n"
    '{"expenses": [{"item": "...", "amount": رقم, "category": "...", "when": "اليوم|أمس|قبل أمس"}]}\n'
    "التصنيفات المسموحة: " + "، ".join(CATEGORIES) + ".\n"
    "إذا لم يذكر الوقت فهو اليوم. إذا الرسالة ليست مصروفاً دُفع فعلاً "
    '(سؤال، خطة، دخل، تحية) أعد {"expenses": []}.'
)

# item as the user writes it -> category
ITEMS = {
    "قهوة": ["قهوة", "لاتيه", "كابتشينو", "سبانش لاتيه", "شاي كرك", "موكا", "قهوة مختصة", "فلات وايت", "آيس لاتيه", "دلة قهوة"],
    "مطاعم": ["غدا", "عشا", "فطور", "برجر", "شاورما", "مندي", "كبسة", "بيتزا", "سوشي", "مطبق", "فلافل", "بروستد"],
    "بقالة": ["بقالة", "خضار", "حليب", "خبز", "مقاضي البيت", "فواكه", "رز", "تمر", "موية"],
    "مواصلات": ["بنزين", "أوبر", "كريم", "تاكسي", "موقف", "تذكرة مترو", "غسيل السيارة", "تغيير زيت"],
    "فواتير": ["فاتورة الكهرباء", "فاتورة الجوال", "فاتورة النت", "فاتورة الموية", "شحن رصيد", "إيجار"],
    "تسوق": ["ثوب", "شماغ", "جزمة", "عطر", "ملابس", "ساعة", "سماعة", "شنطة", "نظارة"],
    "صحة": ["صيدلية", "دواء", "كشفية", "فيتامينات", "تحليل دم", "بنادول", "نادي رياضي"],
    "ترفيه": ["سينما", "بلايستيشن", "اشتراك نتفلكس", "تذاكر مباراة", "بولينج", "اشتراك سبوتيفاي", "ملاهي"],
    "أخرى": ["هدية", "تبرع", "حلاق", "كي الملابس", "طوابع"],
}

# paid for, not bought: "اشتريت تاكسي" reads wrong
SERVICES = {"أوبر", "كريم", "تاكسي", "موقف", "غسيل السيارة", "تغيير زيت", "فاتورة الكهرباء", "فاتورة الجوال",
            "فاتورة النت", "فاتورة الموية", "إيجار", "كشفية", "تحليل دم", "نادي رياضي", "سينما", "بولينج",
            "ملاهي", "تبرع", "حلاق", "كي الملابس", "غدا", "عشا", "فطور", "اشتراك نتفلكس", "اشتراك سبوتيفاي", "بنزين"}

# a few items held out of training so the test set checks generalisation
HELD_OUT = {"فلات وايت", "مطبق", "تمر", "تغيير زيت", "إيجار", "نظارة", "نادي رياضي", "ملاهي", "طوابع"}

WORDS = {10: "عشرة", 15: "خمسطعش", 20: "عشرين", 25: "خمسة وعشرين", 30: "ثلاثين", 40: "أربعين",
         50: "خمسين", 60: "ستين", 70: "سبعين", 100: "مية", 150: "مية وخمسين", 200: "ميتين",
         300: "ثلاث مية", 500: "خمس مية", 1000: "ألف"}

TYPICAL = {"قهوة": (9, 35), "مطاعم": (15, 220), "بقالة": (5, 450), "مواصلات": (10, 180),
           "فواتير": (40, 900), "تسوق": (50, 1500), "صحة": (15, 400), "ترفيه": (20, 300), "أخرى": (10, 300)}

WHEN = [("", "اليوم"), ("اليوم", "اليوم"), ("الحين", "اليوم"), ("أمس", "أمس"), ("امس", "أمس"),
        ("البارحة", "أمس"), ("قبل أمس", "قبل أمس"), ("أول أمس", "قبل أمس")]

CURRENCY = ["ريال", "ريال", "ريال", "", "ر.س", "ريال سعودي", "SAR"]

ITEM_RANGE = {"حليب": (4, 25), "خبز": (2, 15), "موية": (3, 30), "رز": (20, 90), "تمر": (15, 120),
              "فواكه": (10, 80), "خضار": (10, 90), "شاي كرك": (2, 8), "بنادول": (5, 20), "موقف": (3, 30),
              "تذكرة مترو": (4, 20), "شحن رصيد": (20, 200), "إيجار": (1500, 4000), "حلاق": (20, 80),
              "كي الملابس": (10, 60), "طوابع": (5, 30), "فلافل": (5, 25), "شاورما": (8, 40), "دواء": (10, 150),
              "بروستد": (20, 60), "مطبق": (10, 30), "فطور": (10, 60), "دلة قهوة": (25, 60), "عطر": (90, 900),
              "ساعة": (150, 1500), "ثوب": (90, 450), "شماغ": (60, 350), "اشتراك نتفلكس": (25, 65),
              "اشتراك سبوتيفاي": (20, 30), "تبرع": (10, 500), "بنزين": (30, 150), "أوبر": (12, 90), "كريم": (12, 90)}

INDIC = str.maketrans("0123456789.", "٠١٢٣٤٥٦٧٨٩٫")


def pick_amount(rng, cat, item=None):
    lo, hi = ITEM_RANGE.get(item, TYPICAL[cat])
    if rng.random() < 0.22:
        options = [v for v in WORDS if lo <= v <= hi] or [lo]
        value = rng.choice(options)
        return value, WORDS.get(value, str(value))
    if rng.random() < 0.15 and hi < 100:
        value = round(rng.uniform(lo, hi) * 2) / 2      # e.g. 12.5
        value = int(value) if value.is_integer() else value
    else:
        value = rng.randint(lo, hi)
    shown = f"{value:g}"
    if rng.random() < 0.3:
        shown = shown.translate(INDIC)
    return value, shown


def money(rng, shown):
    cur = rng.choice(CURRENCY)
    return f"{shown} {cur}".strip()


# templates take (item, amount text, when text); the item may be rewritten by the template
TEMPLATES = [
    "دفعت {m} {i} {w}",
    "{i} ب{m} {w}",
    "اشتريت {i} ب{m} {w}",
    "{w} اشتريت {i} ب{m}",
    "صرفت {m} على {i} {w}",
    "طلع علي {i} {m} {w}",
    "{i} {m}",
    "كلفني {i} {m} {w}",
    "{w} دفعت حق {i} {m}",
    "سجل {i} {m} {w}",
    "حاسبت {i} ب{m} {w}",
    "راحت {m} على {i} {w}",
]

VERB_ITEMS = {  # natural verbs that imply an item
    "مطاعم": [("تغديت ب{m} {w}", "غدا"), ("تعشيت ب{m} {w}", "عشا"), ("فطرت ب{m} {w}", "فطور")],
    "مواصلات": [("عبيت بنزين ب{m} {w}", "بنزين"), ("ركبت أوبر ب{m} {w}", "أوبر")],
    "فواتير": [("سددت فاتورة الكهرباء {m} {w}", "فاتورة الكهرباء"), ("شحنت رصيد ب{m} {w}", "شحن رصيد")],
    "قهوة": [("تقهويت ب{m} {w}", "قهوة")],
}

NOT_EXPENSE = [
    "كم صرفت هالشهر؟", "وش أكثر شي أصرف عليه؟", "السلام عليكم", "شكراً", "هلا",
    "ذكرني أدفع فاتورة الكهرباء بكرة", "أبي أشتري جوال ب{m}", "ناوي أشتري {i} ب{m} الأسبوع الجاي",
    "استلمت راتبي {m}", "جاني تحويل {m} من أخوي", "رجعوا لي {m} من {i}", "كم سعر {i}؟",
    "لو اشتريت {i} ب{m} يكون غالي؟", "امسح آخر مصروف", "ابي ملخص الأسبوع", "وش رصيدي؟",
    "بكرة بدفع {m} {i}", "خويي دفع عني {i}", "عطني نصيحة أوفر", "صديقي صرف {m} على {i}",
]


def clean(s):
    return " ".join(s.split())


def one_expense(rng, allow):
    cat = rng.choice(CATEGORIES)
    if cat in VERB_ITEMS and rng.random() < 0.3:
        tpl, item = rng.choice(VERB_ITEMS[cat])
    else:
        tpl, item = rng.choice(TEMPLATES), rng.choice(ITEMS[cat])
    if "اشتريت" in tpl and item in SERVICES:
        tpl = "دفعت {m} {i} {w}"
    if not allow(item):
        return None
    value, shown = pick_amount(rng, cat, item)
    w_text, w_val = rng.choice(WHEN) if "{w}" in tpl else ("", "اليوم")
    text = tpl.format(i=item, m=money(rng, shown), w=w_text)
    return clean(text), {"item": item, "amount": value, "category": cat, "when": w_val}


def sample(rng, allow):
    r = rng.random()
    if r < 0.14:                              # not an expense
        tpl = rng.choice(NOT_EXPENSE)
        cat = rng.choice(CATEGORIES)
        _, shown = pick_amount(rng, cat)
        text = tpl.format(m=money(rng, shown), i=rng.choice(ITEMS[cat]))
        return clean(text), {"expenses": []}
    if r < 0.30:                              # two expenses in one message
        a, b = one_expense(rng, allow), one_expense(rng, allow)
        if not a or not b:
            return None
        joiner = rng.choice([" و", " و ", "، و", " وبعدين "])
        return clean(a[0] + joiner + b[0]), {"expenses": [a[1], b[1]]}
    e = one_expense(rng, allow)
    return (e[0], {"expenses": [e[1]]}) if e else None


def build(n, seed, allow):
    rng, rows, seen = random.Random(seed), [], set()
    while len(rows) < n:
        s = sample(rng, allow)
        if s and s[0] not in seen:
            seen.add(s[0])
            rows.append({"text": s[0], "label": s[1]})
    return rows


def main(out="data", n_train=700, n_test=120):
    os.makedirs(out, exist_ok=True)
    train = build(n_train, 7, lambda item: item not in HELD_OUT)
    test = build(n_test, 99, lambda item: True)
    train_texts = {r["text"] for r in train}
    test = [r for r in test if r["text"] not in train_texts]
    for name, rows in (("train", train), ("test", test)):
        with open(os.path.join(out, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train: {len(train)}  test: {len(test)}  -> {out}/")


if __name__ == "__main__":
    main()
