# https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3

---
license: apache-2.0
library_name: timm
---
# WD EVA02-Large Tagger v3

Supports ratings, characters and general tags.

Trained using https://github.com/SmilingWolf/JAX-CV.  
TPUs used for training kindly provided by the [TRC program](https://sites.research.google/trc/about/).

## Dataset
Last image id: 7220105  
Trained on Danbooru images with IDs modulo 0000-0899.  
Validated on images with IDs modulo 0950-0999.  
Images with less than 10 general tags were filtered out.  
Tags with less than 600 images were filtered out.

## Validation results
`v1.0: P=R: threshold = 0.5296, F1 = 0.4772`

## What's new
Model v1.0/Dataset v3:  
More training images, more and up-to-date tags (up to 2024-02-28).  
Now `timm` compatible! Load it up and give it a spin using the canonical one-liner!  
ONNX model is compatible with code developed for the v2 series of models.  
The batch dimension of the ONNX model is not fixed to 1 anymore. Now you can go crazy with batch inference.  
Switched to Macro-F1 to measure model performance since it gives me a better gauge of overall training progress.

# Runtime deps
ONNX model requires `onnxruntime >= 1.17.0`

# Inference code examples
For timm: https://github.com/neggles/wdv3-timm  
For ONNX: https://huggingface.co/spaces/SmilingWolf/wd-tagger  
For JAX: https://github.com/SmilingWolf/wdv3-jax

## Final words
Subject to change and updates.
Downstream users are encouraged to use tagged releases rather than relying on the head of the repo.
