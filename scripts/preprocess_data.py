import argparse
import json
import os
from typing import List

import nltk
import numpy as np
import pandas as pd
import spacy
from allennlp.data.tokenizers.word_splitter import SpacyWordSplitter
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer
from spacy.tokenizer import Tokenizer
from tqdm import tqdm, trange
from itertools import islice
from vampire.common.util import read_text, save_sparse, write_to_json


def load_data(data_path: str, tokenize: bool = False, tokenizer_type: str = "just_spaces") -> List[str]:
    if tokenizer_type == "just_spaces":
        tokenizer = SpacyWordSplitter()
    elif tokenizer_type == "spacy":
        nlp = spacy.load('en_core_web_sm')
        tokenizer = Tokenizer(nlp.vocab)
    tokenized_examples = []
    with tqdm(open(data_path, "r"), desc=f"loading {data_path}") as f:
        for line in f:
            if data_path.endswith(".jsonl") or data_path.endswith(".json"):
                example = json.loads(line)
            else:
                example = {"text": line}
            if tokenize:
                if tokenizer_type == 'just_spaces':
                    tokens = list(map(str, tokenizer.split_words(example['text'])))
                elif tokenizer_type == 'spacy':
                    tokens = list(map(str, tokenizer(example['text'])))
                text = ' '.join(tokens)
            else:
                text = example['text']
            tokenized_examples.append(text)
    return tokenized_examples

def main():
    parser = argparse.ArgumentParser(formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--train-path", type=str, required=True,
                        help="Path to the train jsonl file.")
    parser.add_argument("--dev-path", type=str, required=False,
                        help="Path to the dev jsonl file.")
    parser.add_argument("--vocab-path", type=str, required=False,
                        help="Path to the vocab jsonl file.")
    parser.add_argument("--serialization-dir", "-s", type=str, required=True,
                        help="Path to store the preprocessed output.")
    parser.add_argument("--vocab-size", type=int, required=False, default=10000,
                        help="Path to store the preprocessed corpus vocabulary (output file name).")
    parser.add_argument("--shard", type=int, required=False, default=None)
    parser.add_argument("--tokenize", action='store_true',
                        help="Path to store the preprocessed corpus vocabulary (output file name).") 
    parser.add_argument("--tokenizer-type", type=str, default="just_spaces",
                        help="Path to store the preprocessed corpus vocabulary (output file name).")
    parser.add_argument("--reference-corpus-path", type=str, required=False,
                        help="Path to store the preprocessed corpus vocabulary (output file name).")
    parser.add_argument("--tokenize-reference", action='store_true',
                        help="Path to store the preprocessed corpus vocabulary (output file name).") 
    parser.add_argument("--reference-tokenizer-type", type=str, default="just_spaces",
                        help="Path to store the preprocessed corpus vocabulary (output file name).")
    args = parser.parse_args()

    if not os.path.isdir(args.serialization_dir):
        os.mkdir(args.serialization_dir)
    
    vocabulary_dir = os.path.join(args.serialization_dir, "vocabulary")

    if not os.path.isdir(vocabulary_dir):
        os.mkdir(vocabulary_dir)

    tokenized_train_examples = load_data(args.train_path, args.tokenize, args.tokenizer_type)
    if args.dev_path:
        tokenized_dev_examples = load_data(args.dev_path, args.tokenize, args.tokenizer_type)

    print("fitting count vectorizer...")

    if args.vocab_path:
        with open(args.vocab_path) as f:
            vocab = [x.strip() for x in f.readlines()]
            vocab_size = len(vocab)
        count_vectorizer = CountVectorizer(vocabulary=vocab, token_pattern=r'\b[^\d\W]{3,30}\b')
    else:
        vocab_size = args.vocab_size
        count_vectorizer = CountVectorizer(max_features=vocab_size, stop_words='english', token_pattern=r'\b[^\d\W]{3,30}\b')
    
    text = tokenized_train_examples
    if args.dev_path:
        text += tokenized_dev_examples
    
    if args.dev_path:
        count_vectorizer.fit(tqdm(text))
        vectorized_train_examples = count_vectorizer.transform(tqdm(tokenized_train_examples))
        vectorized_dev_examples = count_vectorizer.transform(tqdm(tokenized_dev_examples))
    else:
        vectorized_train_examples = count_vectorizer.fit_transform(tqdm(text))

    if args.vocab_path:
        reference_vectorizer = CountVectorizer(vocabulary=vocab, token_pattern=r'\b[^\d\W]{3,30}\b')
    else:
        reference_vectorizer = CountVectorizer(stop_words='english', token_pattern=r'\b[^\d\W]{3,30}\b')

    if not args.reference_corpus_path:
        if not args.dev_path:
            print("skipping reference corpus construction...")
            reference_matrix = None
        else:
            print("fitting reference corpus using development data...")
            reference_matrix = reference_vectorizer.fit_transform(tqdm(tokenized_dev_examples))
    else:
        print(f"loading reference corpus at {args.reference_corpus_path}...")
        reference_examples = load_data(args.reference_corpus_path, args.tokenize_reference, args.reference_tokenizer_type)
        print("fitting reference corpus...")
        reference_matrix = reference_vectorizer.fit_transform(tqdm(reference_examples))

    if reference_matrix is not None:
        reference_vocabulary = reference_vectorizer.get_feature_names()

    # add @@unknown@@ token vector
    if "@@UNKNOWN@@" not in count_vectorizer.get_feature_names():
        vectorized_train_examples = sparse.hstack((np.array([0] * len(tokenized_train_examples))[:,None], vectorized_train_examples))
        if args.dev_path:
            vectorized_dev_examples = sparse.hstack((np.array([0] * len(tokenized_dev_examples))[:,None], vectorized_dev_examples))
    if args.dev_path:
        master = sparse.vstack([vectorized_train_examples, vectorized_dev_examples])
    else:
        master = vectorized_train_examples
    # generate background frequency
    print("generating background frequency...")
    bgfreq = dict(zip(count_vectorizer.get_feature_names(), (np.array(master.sum(0)) / args.vocab_size).squeeze()))

    print("saving data...")
    if args.shard:
        print("sharding...")
        if not os.path.isdir(os.path.join(args.serialization_dir, "shard")):
            os.mkdir(os.path.join(args.serialization_dir, "shard"))
        batch_size = vectorized_train_examples.shape[0] // args.shard
        for ix in trange(0, vectorized_train_examples.shape[0], batch_size):
            if ix + batch_size > vectorized_train_examples.shape[0]:
                mat = vectorized_train_examples[ix:,:]
                ids_ = range(ix, vectorized_train_examples.shape[0])
            else:
                mat = vectorized_train_examples[ix:ix+batch_size,:]
                ids_= range(ix, ix+batch_size)
            save_sparse(mat, os.path.join(args.serialization_dir, "shard", f"train.{ix}.npz"))
            write_list_to_file([str(x) for x in ids_], os.path.join(args.serialization_dir, "shard", f"train.{ix}.id"))
    else:
        save_sparse(vectorized_train_examples, os.path.join(args.serialization_dir, "train.npz"))
    if args.dev_path:
        save_sparse(vectorized_dev_examples, os.path.join(args.serialization_dir, "dev.npz"))
    if not os.path.isdir(os.path.join(args.serialization_dir, "reference")):
        os.mkdir(os.path.join(args.serialization_dir, "reference"))
    
    if reference_matrix is not None:
        save_sparse(reference_matrix, os.path.join(args.serialization_dir, "reference", "ref.npz"))
        write_to_json(reference_vocabulary, os.path.join(args.serialization_dir, "reference", "ref.vocab.json"))
    write_to_json(bgfreq, os.path.join(args.serialization_dir, "vampire.bgfreq"))
    if "@@UNKNOWN@@" not in count_vectorizer.get_feature_names():
        vocab = ['@@UNKNOWN@@'] + count_vectorizer.get_feature_names()
    else:
        vocab = count_vectorizer.get_feature_names()
    write_list_to_file(vocab, os.path.join(vocabulary_dir, "vampire.txt"))
    write_list_to_file(['*tags', '*labels', 'vampire'], os.path.join(vocabulary_dir, "non_padded_namespaces.txt"))
    print(f"Generated vocabulary of size {len(count_vectorizer.get_feature_names())}")

def write_list_to_file(ls, save_path):
    """
    Write each json object in 'jsons' as its own line in the file designated by 'save_path'.
    """
    # Open in appendation mode given that this function may be called multiple
    # times on the same file (positive and negative sentiment are in separate
    # directories).
    out_file = open(save_path, "w+")
    for example in ls:
        out_file.write(example)
        out_file.write('\n')

if __name__ == '__main__':
    main()
