import sys, soundfile as sf, json
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from kokoro_onnx import Kokoro
import render
k = Kokoro("kokoro/kokoro-v1.0.onnx", "kokoro/voices-v1.0.bin")
lines = [(0.3, 4.7, "Everyone keeps telling me AI is going to change everything.")] + [(s, e, t) for s, e, t in render.CAPTIONS[1:]]
lines = [(s,e,t.replace("“","\"").replace("”","\"").replace("$10k","ten K")) for s,e,t in lines]
import os; os.makedirs("vo", exist_ok=True)
out = {}
for voice in sys.argv[1:]:
    res = []
    for i,(s,e,t) in enumerate(lines):
        a, sr = k.create(t, voice=voice, speed=1.1, lang="en-us")
        fn = f"vo/{voice}_{i:02d}.wav"; sf.write(fn, a, sr)
        res.append((s, e, len(a)/sr, fn)); print(voice, i, f"slot {e-s:.2f} audio {len(a)/sr:.2f}", t)
    out[voice]=res
json.dump(out, open("vo/index.json","w"))
