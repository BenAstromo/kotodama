# Verdicts for Gemini batches 10–13 (2026-10-14) after checking each sentence.
# Gemini flagged, kept as real uses: to-iu-say 5 (言えないまでも), shika-nai 4 7 (でしかない),
# nai-to-ikenai 8, no-koto-nominalizer 1 4 5 8 (real nominalizers; SKIP rejected), e 6 (への),
# to-with 7 (お父さんと一緒に), ka-question 6, to-to-dochira-ga 3, de-wa-arimasen 2,
# ato-de 8 (労働の後で), ni-iku 8 (映画に行きたがって), ga-jouzu 5, na-na-adjective 1
# (Gemini described a different sentence), to-iu-named 6.
# Added by me: to-iu-say 1 2 (そんなこと言った), ni-iku 2 7 (places / events),
# mou-ta 3 7 8 (もう一台 / もう一度).
# Known residuals: ni-suru 3 (灰にした, "make into").
V = {
    "to-omou": ([4], {}),
    "to-iu-say": ([1, 2], {}),
    "bakari": ([8], {}),
    "o-ni-naru": ([5, 6], {}),
    "tara-dou": ([2, 3, 5], {}),
    "hou-ga-ii": ([4], {}),
    "toka-toka": ([1], {}),
    "oki-ni": ([1, 8], {}),
    "ni-time": ([2, 8], {}),
    "ni-destination": ([3], {}),
    "ni-location": ([8], {}),
    "ni-indirect-object": ([4], {}),
    "de-means": ([8], {}),
    "to-and": ([2, 4], {}),
    "to-with": ([6], {6: "to-and"}),
    "ya": ([4], {}),
    "ka-or": ([2, 3, 5, 6, 7], {}),   # 2 どちらか一方 = "one of", not "A or B" (my call)
    "deshita": ([6], {}),
    "te-kudasai": ([6], {}),
    "te-mo-ii": ([7], {}),
    "te": ([7, 8], {}),
    "mae-ni": ([2], {}),
    "ato-de": ([1, 2, 4, 5, 6], {}),
    "nagara": ([5], {}),
    "ni-iku": ([2, 6, 7], {}),
    "kara-reason": ([1, 2], {}),
    "ni-suru": ([4, 7], {}),
    "mou-ta": ([3, 4, 6, 7, 8], {}),
    "amari-nai": ([5], {}),
    "dake": ([6], {}),
    "ku-nai-katta-ku-nakatta": ([1, 2, 4, 5, 7], {}),
    "to-iu-named": ([1, 2, 3, 4, 5, 7, 8], {}),
    # kept as they are (Gemini wrong)
    "shika-nai": ([], {}), "nai-to-ikenai-nakucha": ([], {}), "no-koto-nominalizer": ([], {}),
    "e": ([], {}), "ka-question": ([], {}), "to-to-dochira-ga": ([], {}),
    "de-wa-arimasen-ja-nai": ([], {}), "ga-jouzu-ga-heta": ([], {}), "na-na-adjective": ([], {}),
}
