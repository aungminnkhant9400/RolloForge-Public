import Link from 'next/link';
import { ExternalLink, Calendar, User, Clock, FileText } from 'lucide-react';
import { BookmarkWithAnalysis, getBookmarkAgeDays, getEffectiveBucket, getEffectivePriority, getReadingTime } from '@/lib/data';
import { useState } from 'react';

interface BookmarkCardProps {
  bookmark: BookmarkWithAnalysis;
}

const bucketClasses = {
  test_this_week: 'test',
  build_later: 'build',
  archive: 'archive',
  ignore: 'ignore',
};

const bucketLabels = {
  test_this_week: 'Test This Week',
  build_later: 'Build Later',
  archive: 'Archive',
  ignore: 'Ignore',
};

export function BookmarkCard({ bookmark }: BookmarkCardProps) {
  const [htmlView, setHtmlView] = useState(false);
  const [htmlContent, setHtmlContent] = useState('');
  const [loadingHtml, setLoadingHtml] = useState(false);
  
  const analysis = bookmark.analysis;
  const bucket = getEffectiveBucket(analysis) || 'archive';
  const priority = getEffectivePriority(analysis);
  const ageDays = getBookmarkAgeDays(bookmark);
  
  // Only show reading time for X/Twitter posts (fully scraped)
  const isXPost = bookmark.source === 'x' || bookmark.url.includes('x.com') || bookmark.url.includes('twitter.com');
  const readingTime = isXPost ? getReadingTime(bookmark.text || '') : null;
  
  const loadHtmlView = async () => {
    if (htmlContent) {
      setHtmlView(true);
      return;
    }
    setLoadingHtml(true);
    try {
      const res = await fetch('/api/html-view', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: bookmark.title,
          text: bookmark.text,
          author: bookmark.author,
          url: bookmark.url,
          summary: analysis?.summary,
          insights: analysis?.key_insights,
        }),
      });
      const data = await res.json();
      if (data.html) {
        setHtmlContent(data.html);
        setHtmlView(true);
      }
    } catch (e) {
      console.error('Failed to load HTML view:', e);
    } finally {
      setLoadingHtml(false);
    }
  };
  
  if (htmlView) {
    return (
      <article className="bookmark-card html-view">
        <div className="html-view-header">
          <button 
            onClick={() => setHtmlView(false)}
            className="html-view-back"
          >
            ← Back to card
          </button>
          <span className="html-view-label">HTML View</span>
        </div>
        <iframe 
          srcDoc={htmlContent}
          className="html-view-frame"
          sandbox="allow-scripts"
        />
      </article>
    );
  }

  return (
    <article className="bookmark-card">
      <div className="card-header">
        <span className={`badge ${bucketClasses[bucket]}`}>
          {bucketLabels[bucket]}
        </span>
        
        {typeof priority === 'number' && (
          <span className="priority">
            Priority: <strong>{priority.toFixed(1)}</strong>
          </span>
        )}
      </div>
      
      <div className="card-title-row">
        <h3 className="card-title">
          <Link href={bookmark.url} target="_blank" rel="noopener noreferrer">
            {bookmark.title}
            <ExternalLink size={16} className="external-icon" />
          </Link>
        </h3>
        <button 
          onClick={loadHtmlView}
          disabled={loadingHtml}
          className="html-view-btn"
          title="View as styled HTML"
        >
          <FileText size={14} />
          {loadingHtml ? '...' : 'HTML'}
        </button>
      </div>
      
      {analysis?.summary && (
        <p className="card-summary">
          {analysis.summary
            .replace(/\.{3,}$/, '')
            .replace(/\.$/, '')
            .trim()}
          .
        </p>
      )}
      
      <div className="card-meta">
        {bookmark.author && (
          <span>
            <User size={14} />
            {bookmark.author}
          </span>
        )}
        <span>
          <Calendar size={14} />
          {new Date(bookmark.bookmarked_at).toLocaleDateString()}
        </span>

        {ageDays !== null && (
          <span>
            <Clock size={14} />
            {ageDays}d old
          </span>
        )}
        
        {readingTime && (
          <span>
            <Clock size={14} />
            {readingTime} min read
          </span>
        )}
        
        {analysis && typeof analysis.worth_score === 'number' && typeof analysis.effort_score === 'number' && (
          <span style={{ fontSize: '0.75rem' }}>
            Worth: {analysis.worth_score.toFixed(1)} | 
            Effort: {analysis.effort_score.toFixed(1)}
          </span>
        )}
      </div>
      
      {bookmark.tags?.length > 0 && (
        <div className="tags">
          {bookmark.tags.map((tag) => (
            <span key={tag} className="tag">#{tag}</span>
          ))}
        </div>
      )}
    </article>
  );
}