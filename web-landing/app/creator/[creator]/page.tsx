import React from 'react';
import { listCreatorDesigns } from '../../../lib/api';

export default async function CreatorPage({ params }: { params: { creator: string } }) {
  const res = await listCreatorDesigns(params.creator);
  const items = res.designs || [];
  return (
    <main className="page">
      <div className="wrap">
        <div className="panel">
          <h1 className="title">{params.creator}</h1>
          <p className="subtitle">Public designs by this creator.</p>
        </div>
        <div className="grid">
          {items.map((d: any) => (
            <a key={d.id} className="card" href={`/design/${d.slug}`}>
              <div style={{ fontWeight: 800 }}>{d.title}</div>
              <div className="meta">{d.family} • {d.print_confidence ? `${d.print_confidence}% print confidence` : 'No score yet'}</div>
            </a>
          ))}
        </div>
      </div>
    </main>
  );
}
