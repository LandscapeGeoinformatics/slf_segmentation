import pandas as pd
import matplotlib.pyplot as plt
import glob

df = pd.read_csv(
    "log.csv"
)

plt.rcParams.update({'font.size': 16})
fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# loss
axes[0].plot(df["loss"], label="Train Loss")
axes[0].plot(df["val_loss"], label="Val Loss")
axes[0].set_xlabel("Epoch")
#axes[0].set_ylabel("BCE Loss")
axes[0].set_title("Binary Cross-Entropy loss")
axes[0].legend()
axes[0].grid(True)

# f1 score
axes[1].plot(df["f1"], label="Train F1-score")
axes[1].plot(df["val_f1"], label="Val F1-score")
axes[1].set_xlabel("Epoch")
#axes[1].set_ylabel("F1-score")
axes[1].set_title("F1-score")
axes[1].legend()
axes[1].grid(True)

plt.tight_layout(w_pad=3)
plt.show()
