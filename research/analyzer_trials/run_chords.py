"""Chord recognition trial -> output/chords/<id>.json

Tool: BTC (Bi-directional Transformer for Chord recognition, Park et al. ISMIR 2019), large vocabulary
(170 labels: 12 roots x 14 qualities + N + X). Cloned into vendor/BTC-ISMIR19 (weights ship in the repo).
Re-implements the repo's test.py loop with our own decoding so it works on current numpy/librosa/torch.

Output: {"chords": [[start_s, end_s, "C:maj7"], ...]}

Usage: python run_chords.py [track ids...]
"""
from __future__ import annotations

import json
import sys
import time

import librosa
import numpy as np
import torch

from common import HERE, load_audio, load_tracks, out_path, parse_only

# The 2019 BTC code uses numpy aliases that numpy >= 1.24 removed; restore them instead of editing vendor/.
for _alias, _type in (("float", float), ("int", int), ("bool", bool)):
    if not hasattr(np, _alias):
        setattr(np, _alias, _type)

BTC = HERE / "vendor" / "BTC-ISMIR19"
sys.path.insert(0, str(BTC))

from btc_model import BTC_model  # noqa: E402
from utils.hparams import HParams  # noqa: E402
from utils.mir_eval_modules import idx2voca_chord  # noqa: E402


def features(y: np.ndarray, config) -> tuple[np.ndarray, float]:
    """Same chunked CQT as the repo's audio_file_to_features, on an already-decoded 22.05 kHz mono signal."""
    sr = config.mp3["song_hz"]
    chunk = int(sr * config.mp3["inst_len"])
    kw = dict(
        sr=sr,
        n_bins=config.feature["n_bins"],
        bins_per_octave=config.feature["bins_per_octave"],
        hop_length=config.feature["hop_length"],
    )
    parts = []
    pos = 0
    while len(y) > pos + chunk:
        parts.append(librosa.cqt(y[pos : pos + chunk], **kw))
        pos += chunk
    parts.append(librosa.cqt(y[pos:], **kw))
    feat = np.log(np.abs(np.concatenate(parts, axis=1)) + 1e-6)
    return feat, config.mp3["inst_len"] / config.model["timestep"]


def main() -> None:
    import yaml

    # HParams.load() uses the old yaml.load() signature, so build it from safe_load ourselves.
    config = HParams(**yaml.safe_load((BTC / "run_config.yaml").read_text(encoding="utf-8")))
    config.feature["large_voca"] = True
    config.model["num_chords"] = 170
    idx_to_chord = idx2voca_chord()

    model = BTC_model(config=config.model)
    ckpt = torch.load(BTC / "test" / "btc_model_large_voca.pt", map_location="cpu", weights_only=False)
    mean, std = ckpt["mean"], ckpt["std"]
    model.load_state_dict(ckpt["model"])
    model.eval()
    n_ts = config.model["timestep"]

    for t in load_tracks(parse_only(sys.argv[1:])):
        dest = out_path("chords", t["id"])
        if dest.exists():
            print(f"[{t['id']}] exists, skipping")
            continue
        t0 = time.time()
        y, _ = load_audio(t["path"], sr=config.mp3["song_hz"], mono=True)
        feat, unit = features(y[0], config)
        feat = (feat.T - mean) / std
        n_frames = feat.shape[0]
        feat = np.pad(feat, ((0, n_ts - n_frames % n_ts), (0, 0)))
        x = torch.tensor(feat, dtype=torch.float32)[None]

        labels: list[int] = []
        with torch.no_grad():
            for k in range(x.shape[1] // n_ts):
                attn, _ = model.self_attn_layers(x[:, n_ts * k : n_ts * (k + 1), :])
                pred, _ = model.output_layer(attn)
                labels.extend(pred.squeeze().tolist())
        labels = labels[:n_frames]

        segs: list[list] = []
        start, prev = 0.0, labels[0]
        for i, lab in enumerate(labels[1:], start=1):
            if lab != prev:
                segs.append([round(start, 3), round(i * unit, 3), idx_to_chord[prev]])
                start, prev = i * unit, lab
        segs.append([round(start, 3), round(n_frames * unit, 3), idx_to_chord[prev]])

        dest.write_text(json.dumps({"id": t["id"], "file": t["file"], "chords": segs}), encoding="utf-8")
        vocab = {}
        for s, e, c in segs:
            vocab[c] = vocab.get(c, 0) + (e - s)
        top = sorted(vocab, key=vocab.get, reverse=True)[:5]
        print(f"[{t['id']}] {len(segs):4d} segments, top: {top}, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
