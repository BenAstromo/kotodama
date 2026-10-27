# Verdicts for the two re-ask files (first-pass points + points missed in batches 4/5/7),
# 2026-10-14, after checking each sentence.
# Gemini flagged, kept as real uses: te-kuru 2 (持ってくれば = 持って来れば), mitai 5
# (したいみたい), o-komete 4 (力をこめて), o-chuushin-ni 2 (君を中心に回っている),
# o-moto-ni 4 (財産をもとに: もと "basis", not 元手).
# Added by me: tatte-datte 6 (かけたってマジかよ, a quote), aida 2 (若者の間に, "among").
# Known residual: koto-wa-nai 4 (気を落とすことはない, "never" vs "no need": meaning).
V = {
    "koto-da": ([1, 2, 3, 4, 5, 6, 7], {}),
    "koto-wa-nai": ([1, 2, 3, 5, 7, 8], {2: "hodo-wa-nai", 5: "hodo-wa-nai"}),
    "ni-tsuite": ([2], {}),
    "you-na-you-ni-like": ([1, 3, 4, 5], {}),
    "to-shite": ([1, 2, 3, 5], {}),
    "tara-ta": ([3, 5, 6, 7], {}),
    "tatte-datte": ([4, 6, 7], {}),
    "muki-muke": ([3, 7, 8], {}),
    "kiru-kirenai": ([2, 3, 4, 8], {}),
    "au": ([2], {}),
    "aida-aida-ni": ([2, 3, 5, 6], {}),
    "dasu": ([4], {}),
    "made-ni": ([1, 3, 6], {}),
    "koto-ga-aru": ([1, 6, 8], {}),
    "o-suru": ([7], {}),
    "naide": ([6], {}),
    "shidai": ([1, 3, 5, 6, 8], {}),
    "shidai-da-shidai-de": ([2], {}),
    "sue-ni": ([3], {}),
    "ta-tokoro-de": ([1, 2, 5, 6, 8], {}),
    "ta-tokoro": (None, {n: "tokoro-da" for n in range(1, 8)}),
    "bakari-ka": ([3], {}),
    "bakari-ni": (None, {n: "n-bakari" for n in range(1, 9)}),
    "bakari-da": ([1, 2, 3, 4, 6, 7, 8], {}),
    "hanmen": ([1, 4], {}),
    # kept as they are (Gemini wrong)
    "te-kuru": ([], {}), "mitai": ([], {}), "o-komete": ([], {}), "o-chuushin-ni": ([], {}),
    "o-moto-ni": ([], {}),
}
