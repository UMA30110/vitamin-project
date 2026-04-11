import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# LOAD DATA
df = pd.read_csv("dataset.csv")

print("Preview:\n", df.head())
print("\nColumns:\n", df.columns)

# REMOVE UNNECESSARY
df = df.drop(['symptoms_list', 'has_multiple_deficiencies'], axis=1)

# TARGET
y = df["disease_diagnosis"]

# FEATURES
X = df.drop("disease_diagnosis", axis=1)

# ENCODE
X = pd.get_dummies(X)

# SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# TRAIN
model = RandomForestClassifier(n_estimators=200)
model.fit(X_train, y_train)

# ACCURACY
accuracy = model.score(X_test, y_test)
print("\nAccuracy:", accuracy)

# SAVE
pickle.dump(model, open("model.pkl", "wb"))

print("\nModel trained successfully ✅")
# Save column names
pickle.dump(X.columns, open("columns.pkl", "wb"))