"""Text Check's file decoding: Shift-JIS must not be read as UTF-16."""
import stubenv as E
tc = E.load("text_check")
src = open(E.load("text_check_view").__file__, encoding="utf-8").read()
E.check("the tab decodes through text_check.decode_text", "decode_text(" in src)
S = "1\n00:00:01,000 --> 00:00:02,000\n今日はいい天気ですね。\n"
cases = {
    "utf-8": S.encode("utf-8"), "utf-8 BOM": b"\xef\xbb\xbf" + S.encode("utf-8"),
    "utf-16 LE BOM": S.encode("utf-16"), "utf-16 BE BOM": b"\xfe\xff" + S.encode("utf-16-be"),
    "utf-16 LE no BOM": S.encode("utf-16-le"),
    "Shift-JIS odd": S.encode("cp932"), "Shift-JIS even": S.encode("cp932") + b"\n",
    "EUC-JP": S.encode("euc_jp"),
}
for name, b in cases.items():
    got = getattr(tc, "decode_text", lambda b: None)(b)
    E.check(f"{name} ({len(b)} bytes) decodes right", got is not None and got.replace("\r", "").strip() == S.strip())
E.check("binary junk → None", getattr(tc, "decode_text", lambda b: 1)(bytes(range(256)) * 3) is None)
E.finish()
