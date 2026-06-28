import os

REQUIRED = [
    "APP_ENV",
    "API_BASE_URL",
    "WEB_BASE_URL",
    "PREVIEW_PUBLIC_BASE",
    "AUTH_TOKEN_SECRET",
]

OPTIONAL = [
    "DATABASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "APP_SCHEME",
]

print("Beta Environment Validation")
print("===========================")

missing = []
for key in REQUIRED:
    value = os.environ.get(key)
    ok = bool(value and value.strip())
    print(f"{key}: {'OK' if ok else 'MISSING'}")
    if not ok:
        missing.append(key)

for key in OPTIONAL:
    value = os.environ.get(key)
    print(f"{key}: {'SET' if value else 'not set'}")

print("\nResult:")
if missing:
    print("FAIL")
    print("Missing required env vars:", ", ".join(missing))
else:
    print("PASS")
