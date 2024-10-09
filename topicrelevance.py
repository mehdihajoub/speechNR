# topicrelevance.py

import pandas as pd
import numpy as np
import logging
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

class TopicRelevanceAndClusteringApp:
    def __init__(self, model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', hf_token=None):
        try:
            # Use the Hugging Face token if provided
            self.model = SentenceTransformer(model_name, use_auth_token=hf_token)
        except Exception as e:
            logging.error(f"Failed to load model {model_name}: {e}")
            self.model = None

    def compute_relevance(self, phrase, topic):
        if self.model is None:
            return 0
        phrase_embedding = self.model.encode(phrase, convert_to_tensor=True)
        topic_embedding = self.model.encode(topic, convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(phrase_embedding, topic_embedding).item()
        return similarity

    def process_data(self, transcription, topics):
        data = pd.DataFrame(transcription)
        if self.model is None:
            logging.error("Model not loaded, cannot process data.")
            return pd.DataFrame()  # Return empty DataFrame
        data['embedding'] = data['text'].apply(lambda x: self.model.encode(x))

        for topic in topics:
            data[topic] = data['text'].apply(lambda x: self.compute_relevance(x, topic))

        return data

    def perform_clustering(self, data, num_clusters):
        embeddings = np.stack(data['embedding'].values)
        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
        data['Cluster'] = kmeans.fit_predict(embeddings)

        pca = PCA(n_components=2)
        components = pca.fit_transform(embeddings)
        data['x'] = components[:, 0]
        data['y'] = components[:, 1]

        return data
