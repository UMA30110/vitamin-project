import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Load correct dataset
df = pd.read_csv("data/symptom_based_vitamin_deficiency_dataset_final.csv")

# Split
X = df.drop("Predicted Deficiency", axis=1)
y = df["Predicted Deficiency"]

# One-hot encoding
X = pd.get_dummies(X)

# Save columns
pickle.dump(X.columns, open("columns.pkl", "wb"))

# Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train, y_train)

# Save model
pickle.dump(model, open("model.pkl", "wb"))

print("NEW MODEL CREATED ✅")