"""Build the chaptered English MP3 from the spoken adaptation."""
import argparse
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from kokoro_onnx import Kokoro


AUDIO = Path(__file__).resolve().parent
RATE = 24000
VOICE = "af_heart"
WORDS = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split() + ["twenty one", "twenty two", "twenty three", "twenty four"]
PRONUNCIATIONS = {
    "kubelet": "kube let", "etcd": "et see dee", "kubectl": "kube control",
    "ConfigMap": "config map", "ReplicaSet": "replica set", "EndpointSlice": "endpoint slice",
    "HTTPRoute": "H T T P route", "HTTP": "H T T P", "StatefulSet": "stateful set",
    "DaemonSet": "daemon set", "CronJob": "cron job", "ServiceAccount": "service account",
    "RoleBinding": "role binding", "NetworkPolicy": "network policy", "GitOps": "git ops",
    "Kustomize": "customize", "subPath": "sub path", "GatewayClass": "gateway class",
}


def spoken(text):
    for original, reading in PRONUNCIATIONS.items():
        text = re.sub(r"\b" + original + r"s?\b",
                      lambda m: reading + ("s" if m[0].endswith("s") and not original.endswith("s") else ""),
                      text)
    return text


def narrate(model_dir, temporary):
    model = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    source = (AUDIO / "narration.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## (\d+)\. ([^\n]+)\n\n(.*?)(?=^## |\Z)", source, re.M | re.S)
    if [int(n) for n, _, _ in sections] != list(range(1, 25)):
        raise ValueError("Expected chapters 1 to 24 in sequence")
    markers = []
    frames = 0
    wav_path = temporary / "book.wav"
    with wave.open(str(wav_path), "wb") as out:
        out.setparams((1, 2, RATE, 0, "NONE", "uncompressed"))

        def silence(seconds):
            nonlocal frames
            samples = round(RATE * seconds)
            out.writeframesraw(bytes(samples * 2))
            frames += samples

        for number, title, body in sections:
            start = round(frames * 1000 / RATE)
            print(f"Chapter {number} at {start / 1000:.1f}s", flush=True)
            paragraphs = [f"Chapter {WORDS[int(number) - 1]}. {title.rstrip('.?!')}."]
            if number == "01":
                paragraphs.insert(0, "Kubernetes in Practice. From your first Pod to your first incident.")
            paragraphs.extend(body.strip().split("\n\n"))
            for paragraph in paragraphs:
                for sentence in re.split(r"(?<=[.!?])\s+", spoken(paragraph)):
                    samples, sr = model.create(sentence, voice=VOICE, speed=0.96, lang="en-us")
                    if sr != RATE or len(samples) < RATE / 8 or not np.isfinite(samples).all():
                        raise ValueError(f"Invalid speech in chapter {number}")
                    pcm = (np.clip(samples, -1.0, 1.0) * 32760).astype("<i2")
                    if np.max(np.abs(pcm.astype(float))) < 100:
                        raise ValueError(f"Silent speech in chapter {number}")
                    out.writeframesraw(pcm.tobytes())
                    frames += len(pcm)
                    silence(0.13)
                silence(0.32)
            silence(0.85)
            markers.append((start, round(frames * 1000 / RATE), f"{number}. {title}"))
    return wav_path, markers


def encode(wav_path, markers, temporary):
    metadata = temporary / "chapters.ffmeta"
    header = ";FFMETADATA1\ntitle=Kubernetes in Practice\nalbum=Kubernetes in Practice\nlanguage=eng\n"
    metadata.write_text(header + "".join(
        f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={a}\nEND={b}\ntitle={title}\n"
        for a, b, title in markers), encoding="utf-8")
    outfile = AUDIO / "kubernetes-in-practice-en.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path),
                    "-i", str(metadata), "-map", "0:a:0", "-map_metadata", "1", "-map_chapters", "1",
                    "-af", "loudnorm=I=-18:TP=-1.5:LRA=9", "-ar", str(RATE), "-ac", "1",
                    "-codec:a", "libmp3lame", "-b:a", "80k", "-id3v2_version", "3", str(outfile)], check=True)
    data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_chapters",
                      "-show_streams", "-show_format", "-of", "json", str(outfile)]))
    if (len(data["chapters"]) != len(markers) or data["streams"][0]["codec_name"] != "mp3"
            or abs(float(data["format"]["duration"]) - markers[-1][1]/1000) > 1):
        raise ValueError("Encoded MP3 failed verification")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(outfile), "-f", "null", "-"], check=True)
    index = ["# Listening guide", "", "Synthetic narration in American English using the Kokoro Heart voice. "
             "The MP3 includes ID3 chapter markers. Times also work in players without chapter navigation.",
             "", "| Start | Chapter |", "| --- | --- |"]
    for start, _, title in markers:
        minutes, seconds = divmod(start // 1000, 60)
        index.append(f"| {minutes}:{seconds:02d} | {title} |")
    (AUDIO / "chapters.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"{len(markers)} chapters, {data['format']['duration']} seconds, {outfile.stat().st_size} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_dir", type=Path)
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        wav, chapters = narrate(parser.parse_args().model_dir, directory)
        encode(wav, chapters, directory)
