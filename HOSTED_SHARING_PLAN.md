# Hosted Landing Pages + External Sharing Plan

## Included in v39
- Next.js web landing foundation in `/web-landing`
- Public routes:
  - `/design/[slug]`
  - `/creator/[creator]`
  - `/get-app`
- Open-in-app CTA via app scheme deep link
- Basic metadata generation for design pages

## Intended flow
1. User publishes design in mobile app
2. App shares public URL like:
   - `https://yourdomain.com/design/<slug>`
3. Landing page shows:
   - title
   - creator
   - family
   - print confidence
   - CTA buttons
4. User can:
   - open in app
   - download/install app

## Production next steps
- Universal links / Android App Links
- Hosted preview image generation
- Real App Store / Play Store links
- Subscriber download rules for STL/CAD
- Cloud database + media hosting
