import sys
sys.path.append('/content/backend')

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle

# Load data first
exec(open('/content/drive/MyDrive/Hackathon/BackEnd/data_loader.py').read())

print("\n⏳ Loading sentence transformer...")
embedder     = SentenceTransformer('all-MiniLM-L6-v2')
descriptions = categories_df['Description'].fillna('').tolist()
codes        = categories_df['Code'].tolist()

print(f"⏳ Encoding {len(descriptions)} categories — takes ~2 min...")
embeddings = embedder.encode(descriptions, show_progress_bar=True)
embeddings = np.array(embeddings).astype('float32')

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, '/content/drive/MyDrive/Hackathon/Data/faiss.index')
with open('/content/drive/MyDrive/Hackathon/Data/category_meta.pkl', 'wb') as f:
    pickle.dump({'descriptions': descriptions, 'codes': codes}, f)

print(f"\n✅ FAISS index built     — {index.ntotal} categories")
print(f"✅ Saved faiss.index     → /content/Data/")
print(f"✅ Saved category_meta   → /content/Data/")