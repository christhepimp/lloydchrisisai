#!/usr/bin/env python3
"""
Train Lloyd's Image Pattern Learning Model
==========================================
Hardcodes 100 images as exact pixel arrays, then trains ~100 epochs.

Usage (local or Google Colab / Cloud):
    python train_image_patterns.py
    python train_image_patterns.py --epochs 100 --images 100

After training, weights are saved to image_pattern.npz
"""

import argparse
from pathlib import Path
import sys

# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from model.image_pattern_learner import ImagePatternLearner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--images", type=int, default=100)
    parser.add_argument("--lr", type=float, default=0.015)
    parser.add_argument("--out", type=str, default="image_pattern.npz")
    args = parser.parse_args()

    print("=" * 50)
    print("Lloyd Image Pattern Learning")
    print("Hardcoding", args.images, "pixel arrays into memory...")
    print("=" * 50)

    learner = ImagePatternLearner()
    n = learner.load_hardcoded_images(n=args.images)
    print(f"Stored {n} images as numerical arrays (exact pixel values).")

    print(f"\nTraining for {args.epochs} epochs (image mathematics / MSE)...")
    result = learner.train(epochs=args.epochs, lr=args.lr, log_every=10)
    print("\nResult:", result)

    out = Path(args.out)
    learner.save(out)
    print(f"\nSaved weights → {out.resolve()}")
    print("Done. Lloyd can now generate / interpolate / vary from learned patterns.")


if __name__ == "__main__":
    main()
