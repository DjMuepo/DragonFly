# Beta Smoke Test Plan

## Core publish/share flow
1. Open mobile app
2. Capture or load a design
3. Confirm draft renders
4. Apply learned defaults
5. Open Print Ready
6. Generate STL
7. Publish design
8. Confirm share URL is returned
9. Confirm preview URL is returned
10. Open hosted design page
11. Confirm Open in App CTA is present

## Deep link flow
1. Open `/tools/deep-link`
2. Trigger sample deep link
3. Confirm app opens expected route
4. Open hosted design page in browser
5. Confirm universal link fallback behavior

## Community flow
1. Open community feed
2. Open a design detail page
3. Like a design
4. Confirm like count updates
5. Confirm creator page loads

## Auth flow
1. Sign up with strong password
2. Confirm login works
3. Confirm weak passwords are rejected
4. Confirm repeated auth attempts eventually rate-limit

## Printer flow
1. Open nearby printers
2. Confirm nearby nodes load
3. Confirm online/offline state influences sort order
4. Submit print request
5. Confirm ETA/status returned
6. Open `/tools/printer-nodes`
7. Toggle printer state and queue depth
8. Confirm refresh shows updated values

## Queue/worker flow
1. Open `/tools/job-queue`
2. Enqueue preview job
3. Open `/tools/worker`
4. Run worker once
5. Confirm processed count increments
6. Confirm job status changes from queued -> running -> done

## Web/landing flow
1. Open `/design/<slug>`
2. Confirm title, creator, preview, tags, likes display
3. Confirm OpenGraph metadata renders a preview image URL
4. Open `/creator/<creator>`
5. Confirm creator designs list loads
6. Open `/get-app`
7. Confirm install buttons render

## API health flow
1. Call `/health`
2. Call `/v1/db/postgres-health`
3. Confirm responses are valid
