import React from 'react';

export default function GetAppPage() {
  const ios = process.env.NEXT_PUBLIC_APPSTORE_URL;
  const android = process.env.NEXT_PUBLIC_PLAYSTORE_URL;
  return (
    <main className="page">
      <div className="wrap">
        <div className="panel">
          <h1 className="title">Get the App</h1>
          <p className="subtitle">Install Eye Platform to open shared designs, remix them, and send them to a nearby printer.</p>
        </div>
        <div className="panel">
          {ios || android ? (
            <div className="row">
              {ios ? <a className="btn primary" href={ios}>Download for iPhone</a> : null}
              {android ? <a className="btn secondary" href={android}>Download for Android</a> : null}
            </div>
          ) : (
            <p className="subtitle">App store listings are not available yet.</p>
          )}
        </div>
      </div>
    </main>
  );
}
