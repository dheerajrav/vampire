{
    "dataset_reader": {
        "type": "semisupervised_text_classification_json",
        "ignore_labels": true,
        "lazy": false,
        "sample": null,
        "max_sequence_length": 400,
        "token_indexers": {
            "tokens": {
                "type": "single_id",
                "lowercase_tokens": true,
                "namespace": "vae"
            }
        },
        "tokenizer": {
            "word_filter": {
                "type": "regex_and_stopwords",
                "patterns": [
                    "\\w{1,3}\\b",
                    "\\w*\\d+\\w*",
                    "\\w*[^\\P{P}]+\\w*"
                ],
                "stopword_file": "s3://suching-dev/stopwords/snowball_stopwords.txt",
                "tokens_to_add": [
                    ">",
                    "<",
                    "$",
                    "href=",
                    "|",
                    "\u00b0",
                    "+",
                    "\u00a3"
                ]
            },
            "word_splitter": "just_spaces"
        },
    },
    "iterator": {
        "type": "basic",
        "batch_size": 128,
        "track_epoch": true
    },
    "model": {
        "type": "nvdm",
        "apply_batchnorm": true,
        "bow_embedder": {
            "type": "bag_of_word_counts",
            "ignore_oov": true,
            "vocab_namespace": "vae"
        },
        "kl_weight_annealing": "sigmoid",
        "reference_counts": "s3://suching-dev/final-datasets/imdb/valid_npmi_reference/train.npz",
        "reference_vocabulary": "s3://suching-dev/final-datasets/imdb/valid_npmi_reference/train.vocab.json",
        "update_background_freq": false,
        "num_sources": 2,

        "vae": {
            "type": "logistic_normal",
            "apply_batchnorm": false,
            "decoder": {
                "activations": [
                    "tanh"
                ],
                "hidden_dims": [
                    20002
                ],
                "input_dim": 64,
                "num_layers": 1
            },
            "encoder": {
                "activations": [
                    "softplus",
                    "softplus"
                ],
                "hidden_dims": [
                    64,
                    64
                ],
                "input_dim": 20004,
                "num_layers": 2
            },
            "log_variance_projection": {
                "activations": [
                    "linear"
                ],
                "hidden_dims": [
                    64
                ],
                "input_dim": 64,
                "num_layers": 1
            },
            "mean_projection": {
                "activations": [
                    "linear"
                ],
                "hidden_dims": [
                    64
                ],
                "input_dim": "64",
                "num_layers": 1
            },
            "z_dropout": 0.2
        },
    //     "initializer": [ 
    //         [
    //         "vae.mean_projection._linear_layers.0.weight|vae.encoder._linear_layers.1.weight|vae.encoder._linear_layers.1.bias|vae.log_variance_projection._linear_layers.0.weight|vae.log_variance_projection._linear_layers.0.bias|vae.mean_projection._linear_layers.0.bias", 
    //         {
    //             "type": "pretrained",
    //             "weights_file_path": "/Users/suching/Github/vae/weights.th",
    //             "parameter_name_overrides": {
    //                 "vae.encoder._linear_layers.1.weight": "vae.encoder._linear_layers.1.weight",
    //                 "vae.encoder._linear_layers.1.bias": "vae.encoder._linear_layers.1.bias",
    //                 "vae.mean_projection._linear_layers.0.weight": "vae.mean_projection._linear_layers.0.weight",
    //                 "vae.mean_projection._linear_layers.0.bias":  "vae.mean_projection._linear_layers.0.bias",
    //                 "vae.log_variance_projection._linear_layers.0.weight": "vae.log_variance_projection._linear_layers.0.weight",
    //                 "vae.log_variance_projection._linear_layers.0.bias": "vae.log_variance_projection._linear_layers.0.bias"
    //             }
    //         }
    //     ]
    // ]
    },
    "train_data_path": "/Users/suching/Github/vae/master_with_source.jsonl",
    "validation_data_path": "s3://suching-dev/final-datasets/imdb/dev_pretokenized.jsonl",
    "trainer": {
        "cuda_device": -1,
        "num_epochs": 50,
        "optimizer": {
            "type": "adam",
            "lr": 0.001
        },
        "patience": 5,
        "validation_metric": "+npmi"
    },
    "vocabulary": {
        "type": "bg_dumper",
        "max_vocab_size": {
            "vae": 20000
        }
    },
    "validation_dataset_reader": {
        "type": "semisupervised_text_classification_json",
        "ignore_labels": true,
        "lazy": false,
        "sample": null,
        "max_sequence_length": 400,
        "token_indexers": {
            "tokens": {
                "type": "single_id",
                "lowercase_tokens": true,
                "namespace": "vae"
            }
        },
        "tokenizer": {
            "word_filter": {
                "type": "regex_and_stopwords",
                "patterns": [
                    "\\w{1,3}\\b",
                    "\\w*\\d+\\w*",
                    "\\w*[^\\P{P}]+\\w*"
                ],
                "stopword_file": "s3://suching-dev/stopwords/snowball_stopwords.txt",
                "tokens_to_add": [
                    ">",
                    "<",
                    "$",
                    "href=",
                    "|",
                    "\u00b0",
                    "+",
                    "\u00a3"
                ]
            },
            "word_splitter": "just_spaces"
        },
    }
}