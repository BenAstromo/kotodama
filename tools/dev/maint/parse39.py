import ast, glob, os, sys
A = sys.argv[1]; bad = 0
for p in sorted(glob.glob(os.path.join(A, "*.py"))):
    try:
        ast.parse(open(p, encoding="utf-8").read(), p, feature_version=(3, 9))
    except SyntaxError as e:
        bad += 1; print("FAIL", os.path.basename(p), e)
print("parse-3.9:", "OK" if not bad else f"{bad} failed")
