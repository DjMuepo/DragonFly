import React from 'react';
import { getDesign, getDesignPageUrl } from '../../../lib/api';
import OpenAppButtons from '../../components/OpenAppButtons';

export async function generateMetadata({ params }: { params: { slug: string } }) {
  try {
    const res = await getDesign(params.slug);
    const d = res.design;
    return {
      title: `${d.title} • Eye Platform`,
      description: d.description || 'View this printable design on Eye Platform.',
      openGraph: { title: `${d.title} • Eye Platform`, description: d.description || 'View this printable design on Eye Platform.', url: getDesignPageUrl(params.slug), images: d.preview_url ? [d.preview_url] : undefined },
    };
  } catch {
    return { title: 'Design • Eye Platform' };
  }
}

export default async function DesignPage({ params }: { params: { slug: string } }) {
  const res = await getDesign(params.slug);
  const d = res.design;
  return (
    <main className="page">
      <div className="wrap">
        <div className="panel">
          <h1 className="title">{d.title}</h1>
          <p className="subtitle">{d.family} • by {d.creator}</p>
        </div>
        <div className="hero">{d.preview_url ? <img src={d.preview_url} alt={d.title} style={{width:'100%',height:'100%',objectFit:'cover',borderRadius:16}} /> : 'Design preview'}</div>
        <div className="panel">
          <p className="subtitle">{d.description || 'No description yet.'}</p>
          <div className="grid" style={{ marginTop: 12 }}>
            <div className="meta">Print confidence: {d.print_confidence ? `${d.print_confidence}%` : 'N/A'}</div>
            <div className="meta">Tags: {(d.tags || []).join(', ') || 'none'}</div>
            <div className="meta">Likes: {d.likes || 0}</div>
          </div>
        </div>
        <div className="panel">
          <p className="subtitle">Open this design in the app to remix, print, or send to a nearby printer.</p>
          <OpenAppButtons slug={params.slug} />
        </div>
      </div>
    </main>
  );
}
