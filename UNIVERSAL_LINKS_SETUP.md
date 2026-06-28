# Universal Links / App Links Setup

## Included in v43
- `web-landing/public/.well-known/apple-app-site-association`
- `web-landing/public/.well-known/assetlinks.json`
- Expo app scheme: `eyeplatform://`
- Example associated domains / Android intent filters in `eye-expo/app.json`

## What to replace before production
- `ABCDE12345.com.muepo.eyeplatform` with real Apple Team ID + bundle identifier
- `example.com` with your real domain
- Android SHA256 certificate fingerprint with your release signing cert
- App Store / Play Store URLs in web landing env

## Result
Shared links can:
- open directly in app if installed
- fall back to hosted landing page if not installed
