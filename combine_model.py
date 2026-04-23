import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder  #  ADD

# Load dataset
df = pd.read_csv("data/symptom_based_vitamin_deficiency_dataset_final.csv")
df.columns = df.columns.str.strip()

df.columns = df.columns.str.replace(" ", "_")
print(df.columns)   

target_col = "Predicted_Deficiency"
#  FILTER DATA
df = df[df[target_col] != "No Deficiency"]


#  ADD THIS HERE (BALANCING)
from sklearn.utils import resample

df = df.groupby(target_col).apply(
    lambda x: resample(x, replace=True, n_samples=100, random_state=42)
).reset_index()
df = df.drop(columns=["level_1"], errors="ignore")   # ADD HERE


 #  ADD THIS
print("COLUMNS AFTER GROUP:", df.columns)

print(df[target_col].value_counts())
# Split
X = df.drop(target_col, axis=1)

#  FIX STARTS HERE
le = LabelEncoder()
y = le.fit_transform(df[target_col])

# save label encoder
pickle.dump(le, open("label_encoder.pkl", "wb"))
#  FIX ENDS HERE

# One-hot encoding
X = pd.get_dummies(X)

# Save columns
pickle.dump(X.columns, open("columns.pkl", "wb"))

# Train
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier(n_estimators=200)  # optional improvement
model.fit(X_train, y_train)

# Save model
pickle.dump(model, open("model.pkl", "wb"))

print("NEW MODEL CREATED ✅")