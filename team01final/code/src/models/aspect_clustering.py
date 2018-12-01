import json
import spacy
import os
from sklearn import cluster
from collections import defaultdict
from time import time
import sys

NUM_CLUSTERS = 4

BASE_PATH = os.getcwd()
PARENT = os.path.dirname(BASE_PATH)

#USE THIS FOR IMPORTING ANY FUNCTIONS FROM src
sys.path.insert(0,BASE_PATH)
from src.dataprep import aspect_json_encoding


def init_spacy():
    print("\nLoading spaCy Model....")
    nlp = spacy.load('en_core_web_lg')
    print("spaCy successfully loaded")
    return nlp

def get_aspects(reviews_data):
    aspects = []
    for review in reviews_data:
        aspect_pairs = review["aspect_pairs"]
        for map in aspect_pairs:
            aspects.append(map['noun'])
    return aspects

def get_aspect_freq_map(aspects):
    aspect_freq_map = defaultdict(int)
    for asp in aspects:
        aspect_freq_map[asp] += 1
    return aspect_freq_map

def get_unique_aspects(aspects):
    unique_aspects = list(set(aspects)) # use this list for clustering
    return unique_aspects

def get_word_vectors(unique_aspects, nlp):
    asp_vectors = []
    for aspect in unique_aspects:
        token = nlp(aspect)
        asp_vectors.append(token.vector)
    return asp_vectors

def get_word_clusters(unique_aspects, nlp):
    # print("Found {} unique aspects for this product".format(len(unique_aspects)))
    asp_vectors = get_word_vectors(unique_aspects, nlp)
    if len(unique_aspects) <= NUM_CLUSTERS:
        # print("Too few aspects ({}) found. No clustering required...".format(len(unique_aspects)))
        return list(range(len(unique_aspects)))

    # print("Running k-means clustering...")
    n_clusters = NUM_CLUSTERS
    kmeans = cluster.KMeans(n_clusters=n_clusters)
    kmeans.fit(asp_vectors)
    labels = kmeans.labels_
    return labels

def get_cluster_names_map(asp_to_cluster_map, aspect_freq_map):
    cluster_id_to_name_map = defaultdict()
    clusters = set(asp_to_cluster_map.values())
    for i in clusters:
        this_cluster_asp = [k for k,v in asp_to_cluster_map.items() if v == i]
        filt_freq_map = {k:v for k,v in aspect_freq_map.items() if k in this_cluster_asp}
        filt_freq_map = sorted(filt_freq_map.items(), key = lambda x: x[1], reverse = True)
        cluster_id_to_name_map[i] = filt_freq_map[0][0]
    return cluster_id_to_name_map

def add_clusters_to_reviews(reviews_data, prod_id, nlp):
    product_aspects = get_aspects(reviews_data)
    aspect_freq_map = get_aspect_freq_map(product_aspects)
    unique_aspects = aspect_freq_map.keys()

    aspect_labels = get_word_clusters(unique_aspects, nlp)
    asp_to_cluster_map = dict(zip(unique_aspects, aspect_labels))
    cluster_names_map = get_cluster_names_map(asp_to_cluster_map, aspect_freq_map)
    updated_reviews = []

    for review in reviews_data:
        aspect_pairs_upd = []
        aspect_pairs = review["aspect_pairs"]
        for map in aspect_pairs:
            noun = map['noun']
            cluster_label_id = asp_to_cluster_map[noun]
            cluster_label_name = cluster_names_map[cluster_label_id]
            map['cluster'] = cluster_label_name
            aspect_pairs_upd.append(map)

        review['aspect_pairs'] = aspect_pairs_upd
        updated_reviews.append(review)
    result = {prod_id:updated_reviews}
    return result

def update_reviews_data(reviews_data, nlp):
    updated_reviews = []
    ctr = 0
    print("Total number of unique products in this category: {}".format(len(reviews_data)))

    for i,product in enumerate(reviews_data):
        for prod_id, this_product_reviews in product.items():
            this_product_upd_reviews = add_clusters_to_reviews(this_product_reviews, prod_id, nlp)
            updated_reviews.append(this_product_upd_reviews)

        if ((i%10000 == 0) ):
            ctr += 1
            print("\n----------------***----------------")
            print("Updating results - batch {}".format(ctr))
            with open('data/processed/model_results.json', 'a') as f:
                json.dump(updated_reviews,f)
            updated_reviews = []
            print("Finished writing results to json!!")
            print("----------------***----------------")

    # Finally write to output file
    ctr += 1
    print("\n----------------***----------------")
    print("Updating results - batch {}".format(ctr))
    with open('data/processed/model_results.json', 'a') as f:
        json.dump(updated_reviews,f)
    updated_reviews = []
    print("Finished writing results to json!!")
    print("----------------***----------------")

def main():
    time1 = time()
    nlp = init_spacy()
    time2 = time()
    print("----------------***----------------")
    print("\nLoading aspect pairs file")
    with open('data/processed/reviews_aspect_mapping.json', 'r') as fobj:
        reviews_data = json.load(fobj)
    print("Finished loading aspect pairs!!\n")
    print("----------------***----------------")
    time3 = time()
    update_reviews_data(reviews_data, nlp)
    aspect_json_encoding.run("data/processed/model_results.json","data/processed/model_results_encoding.json")
    time4 = time()
    print("Time for loading spacy: {0:.2}s".format(time2-time1))
    print("Time for loading aspects json file: {0:.2}s".format(time3-time2))
    print("Time for running aspect clustering: {0:.2}s".format(time4-time3))

if __name__ == '__main__' :
    main()
