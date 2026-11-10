# %% [markdown]
# # fraud model v2 FINAL (really final this time)
# Sam's prototype, exported from a Jupyter notebook. It "works" and the demo
# impressed leadership. Your first task in Lab 1 is to read it and list
# everything that would hurt in production. There are at least 12 problems.
# Do NOT fix this file: it is the "before" picture. The fixed version is src/.
#
# Run it from THIS folder (it only works from here, which is problem number one):
#     cd prototype && uv run python sam_notebook.py

# %%
import pickle
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

DATA = "../../../../datasets/fraud/transactions.csv"   # relative to wherever Sam happened to be
API_KEY = "sk-live-4f9a0c1e-DO-NOT-SHARE"                # used for the "explain" demo

# %%
df = pd.read_csv(DATA)
print(df.shape)
df.head()

# %%
# one-hot encode categories
df = pd.get_dummies(df, columns=["merchant_category", "country"])

# use every column except the label, more features = better model
X = df.drop(columns=["is_fraud", "transaction_id", "timestamp", "customer_id"])
y = df["is_fraud"]

# %%
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)  # random split, no seed

model = GradientBoostingClassifier(n_estimators=100)
model.fit(X_train, y_train)

preds = model.predict(X_test)
print("accuracy", accuracy_score(y_test, preds))
print("auc", roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
# accuracy 0.99 !!! ship it

# %%
pickle.dump(model, open("model.pkl", "wb"))
print("saved")

# %%
# for the API: Diego asked for a function they can call
def predict(txn):
    row = pd.DataFrame([txn])
    row = pd.get_dummies(row)
    row = row.reindex(columns=X.columns, fill_value=0)
    p = model.predict_proba(row)[0][1]
    if p > 0.5:
        return "FRAUD"
    return "OK"

print(predict({"amount": 950.0, "merchant_category": "crypto_exchange", "hour": 3, "is_online": 1,
               "country_mismatch": 1, "card_age_days": 4, "txn_count_24h": 9, "avg_amount_30d": 40.0,
               "device_is_new": 1, "distance_from_home_km": 1200.0, "country": "NG"}))
