import json
import math
import os

# Base vocabulary - diverse domains
BASE_WORDS = [
    # Science
    "neural", "quantum", "logic", "orbit", "signal", "photon", "atom",
    "electron", "proton", "neutron", "plasma", "fusion", "fission", "entropy",
    "symmetry", "tensor", "vector", "matrix", "scalar", "gradient",
    # Technology
    "sensor", "processor", "memory", "cache", "kernel", "socket", "buffer",
    "compiler", "runtime", "pointer", "offset", "register", "interrupt",
    "protocol", "router", "packet", "cipher", "hash", "index", "cluster",
    # Biology
    "neuron", "synapse", "cortex", "genome", "protein", "enzyme", "membrane",
    "receptor", "antibody", "chromosome", "mitosis", "osmosis", "catalyst",
    # Mathematics
    "algebra", "calculus", "topology", "manifold", "theorem", "axiom",
    "integral", "derivative", "polynomial", "eigenvalue", "determinant",
    # Language
    "syntax", "semantics", "morpheme", "phoneme", "lexicon", "grammar",
    "context", "inference", "abstraction", "encoding", "decoding",
    # Commerce
    "market", "capital", "equity", "dividend", "revenue", "margin",
    "inflation", "currency", "commodity", "derivative", "futures",
    # Geography
    "nairobi", "kenya", "africa", "savanna", "highland", "valley",
    "equator", "latitude", "longitude", "meridian", "altitude",
    # General
    "system", "network", "pattern", "structure", "process", "method",
    "concept", "theory", "model", "design", "engine", "bridge",
    "layer", "module", "pipeline", "framework", "platform", "interface",
]

PREFIXES = [
    "ultra", "micro", "macro", "nano", "poly", "mono", "meta",
    "hyper", "sub", "super", "anti", "non", "pre", "post", "inter",
    "intra", "multi", "cross", "deep", "high", "low", "auto",
]

SUFFIXES = [
    "tion", "ment", "ness", "ity", "ism", "ist", "ize", "ify",
    "ing", "ed", "er", "al", "ic", "ous", "ive", "ary", "ory",
    "ward", "wise", "like", "able", "less", "ful", "hood",
]

def generate_entries():
    entries = set()

    # Add base words
    for word in BASE_WORDS:
        entries.add(word)

    # Add prefixed variants
    for prefix in PREFIXES:
        for word in BASE_WORDS:
            entries.add(prefix + word)

    # Add suffixed variants
    for suffix in SUFFIXES:
        for word in BASE_WORDS:
            entries.add(word + suffix)

    # Add compound words
    for i, word_a in enumerate(BASE_WORDS):
        for word_b in BASE_WORDS[i+1:i+8]:
            entries.add(word_a + "_" + word_b)

    # Convert to sorted list, trim or pad to exactly 10000
    entry_list = sorted(entries)

    # If under 10000, add numeric variants
    idx = 0
    while len(entry_list) < 10000:
        entry_list.append(BASE_WORDS[idx % len(BASE_WORDS)] + str(idx))
        idx += 1

    return entry_list[:10000]

def char_vector(word, dims=24):
    """Character-level feature vector — same dimensionality as GDE HashVector."""
    import math
    vec = [0.0] * dims
    PI = 3.141592653589793
    signal_len = 32
    signal = [0.0] * signal_len
    lowered = word.lower()[:signal_len]
    for i, ch in enumerate(lowered):
        signal[i] = float(ord(ch))
    scale = math.sqrt(1.0 / signal_len)
    for k in range(dims):
        s = 0.0
        for n in range(signal_len):
            s += signal[n] * math.cos(PI * k * (n + 0.5) / signal_len)
        vec[k] = scale * s
    return vec

if __name__ == "__main__":
    print("Generating 10,000 knowledge base entries...")
    entries = generate_entries()
    print(f"Generated: {len(entries)} entries")

    print("Computing vectors...")
    kb = []
    for i, word in enumerate(entries):
        vec = char_vector(word)
        kb.append({"word": word, "vector": vec})
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/10000 vectorised")

    # Save knowledge base
    os.makedirs("data", exist_ok=True)
    with open("data/knowledge_base.json", "w") as f:
        json.dump(kb, f)

    # Save word list separately for GDE
    with open("data/word_list.txt", "w") as f:
        for entry in entries:
            f.write(entry + "\n")

    print("Saved: data/knowledge_base.json")
    print("Saved: data/word_list.txt")
    print("Knowledge base ready.")
