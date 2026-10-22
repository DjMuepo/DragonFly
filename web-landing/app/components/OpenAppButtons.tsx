import React from 'react';

export default function OpenAppButtons({ slug }: { slug: string }) {
  const scheme = (process.env.NEXT_PUBLIC_APP_SCHEME || 'eyeplatform://').replace(/\/$/, '');
  const appLink = `${scheme}/design/${encodeURIComponent(slug)}`;
  const ios = process.env.NEXT_PUBLIC_APPSTORE_URL;
  const android = process.env.NEXT_PUBLIC_PLAYSTORE_URL;
  return (
    <div className="row">
      <a className="btn primary" href={appLink}>Open in App</a>
      {ios ? <a className="btn secondary" href={ios}>Get iPhone App</a> : null}
      {android ? <a className="btn secondary" href={android}>Get Android App</a> : null}
      {!ios && !android ? <p className="subtitle">App store listings are not available yet.</p> : null}
    </div>
  );
}
