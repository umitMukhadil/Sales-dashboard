"""Генерирует тестовые данные о продажах за последние 12 месяцев в sales.csv."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

managers = ["Айгерим", "Данияр", "Мария", "Ерлан", "Светлана"]
cities = ["Алматы", "Астана", "Шымкент", "Караганда"]
products = {
    "Ноутбук Pro 14": 420000,
    "Монитор 27\"": 135000,
    "Клавиатура механ.": 32000,
    "Мышь беспроводная": 14500,
    "Наушники ANC": 68000,
    "Веб-камера 4K": 41000,
    "Док-станция USB-C": 56000,
}

end = pd.Timestamp("2026-09-09")
dates = pd.date_range(end - pd.Timedelta(days=364), end, freq="D")

rows = []
order_id = 10000
for d in dates:
    # сезонность: больше заказов в будни и к концу года
    base = 18 if d.weekday() < 5 else 9
    season = 1 + 0.35 * np.sin((d.dayofyear - 60) / 365 * 2 * np.pi)
    n = rng.poisson(base * season)
    for _ in range(n):
        product = rng.choice(list(products))
        qty = int(rng.choice([1, 1, 1, 2, 2, 3, 5]))
        price = products[product] * rng.uniform(0.92, 1.05)
        rows.append({
            "order_id": order_id,
            "date": d.date(),
            "manager": rng.choice(managers, p=[0.25, 0.22, 0.2, 0.18, 0.15]),
            "city": rng.choice(cities, p=[0.45, 0.3, 0.15, 0.1]),
            "product": product,
            "quantity": qty,
            "unit_price": round(price, -2),
            "revenue": round(price * qty, -2),
        })
        order_id += 1

df = pd.DataFrame(rows)
df.to_csv("sales.csv", index=False)
print(f"Записано {len(df)} строк, выручка {df.revenue.sum():,.0f} ₸")
