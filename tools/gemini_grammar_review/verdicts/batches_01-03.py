# Verdicts for Gemini batches 1–3 after checking each sentence myself.
# id: (wrong sentence numbers, {sentence number: other id it should credit instead})
# None for wrong = all sentences wrong.
V = {
    "katawara": ([1, 2, 3], {}),
    "ga-hayai-ka": ([1, 2, 3, 4], {}),
    "tara-saigo-ga-saigo": ([1, 3, 4, 5, 6, 7, 8], {}),
    "tomo-naru-to-tomo-nareba": ([1], {}),
    "atte-no": ([2], {}),
    "you-ga-you-to": ([1, 2, 6], {}),
    "you-ni-mo-nai": (None, {}),
    "koto-tote": ([1], {}),
    "tari-tomo": ([2, 4, 5, 6, 7], {}),
    "de-are-de-are-de-are": ([1, 4, 6, 8], {}),   # 7 also has どうであれ、 (real)
    "to-atte": ([1, 2, 4], {}),
    "to-areba": ([4, 6, 7], {}),
    "to-kitara": ([1], {}),
    "nari-nari": ([1, 2, 3, 4], {}),
    "nari-ni-nari-no": ([1, 2, 3, 4, 5, 6, 8], {}),
    "ni-atte": ([1, 2, 3, 4, 6, 7], {}),
    "wa-oroka": ([1, 3, 5, 7], {}),
    "made-da-made-no-koto-da": ([2, 3, 5, 6, 7, 8], {}),
    "o-oite": (None, {}),
    "o-kagiri-ni": ([], {}),   # 声を限りに is OpenJLPT's own example: kept
    "tada-nomi": ([3], {}),
    "tomo-arou": ([2, 3], {}),
    "to-wa-ie": ([1, 2, 3, 4, 5, 6, 8], {}),
    "jimiru-jimita": ([1, 5], {}),
    "gurumi": (None, {}),
    "kare-kare": ([8], {}),
    "ni-kuwaete": ([2], {}),
    "o-megutte": ([1], {}),
    "o-tsuujite-o-tooshite": ([1, 5], {}),
    "o-nozoite": ([2], {}),
    "kaneru": ([2, 4], {2: "kanenai", 4: "kanenai"}),
    "te-wa-irarenai": ([1, 2, 4, 5, 7, 8], {n: "zu-ni-wa-irarenai" for n in (1, 2, 4, 5, 7, 8)}),
    "mono-ka": ([4, 5, 6, 7, 8], {}),
    "mono-no": ([1, 2, 3, 5, 6, 7], {}),
    # Gemini flagged these, I kept them (real uses): gatera 5, ni-itaru 8,
    # gotoki 4, beku-shite 1, ni-taeru 7, ni-oujite 8.
    "gatera": ([], {}), "ni-itaru-ni-itatte-ni-itatte-wa": ([], {}),
    "gotoki-gotoku": ([], {}), "beku-shite": ([], {}),
    "ni-taeru-ni-taenai": ([], {}), "ni-oujite": ([], {}),
}
