import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ChevronLeft as ChevronLeftIcon, 
  RefreshCw as RefreshCwIcon, 
  Download as DownloadIcon, 
  BookOpen as BookOpenIcon, 
  FileText as FileTextIcon, 
  Clock as ClockIcon,
  ListTodo as ListTodoIcon,
  HelpCircle as HelpCircleIcon,
  CheckCircle2 as CheckCircle2Icon,
  Play as PlayIcon,
  AlignLeft as AlignLeftIcon
} from 'lucide-react';
import { api, getToken, BASE_URL } from '../api';
import './Details.css';

type SummaryData = {
  video: {
    id: number;
    title: string;
    source_type: string;
    source_url: string | null;
    file_size: number;
    duration: number;
    created_at: string;
  };
  summary: {
    id: number;
    executive_summary: string;
    detailed_summary: string;
    key_topics: any[];
    action_items: any[];
    timeline: any[];
    conclusion: string;
  };
  transcript?: {
    id: number;
    video_id: number;
    raw_text: string;
    cleaned_text: string;
    segments_json: any[] | null;
    model_name: string;
    language: string;
    created_at: string;
  } | null;
};

type DetailsProps = {
  setErrorMsg: (msg: string | null) => void;
};

export function Details({ setErrorMsg }: DetailsProps) {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();

  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryTab, setSummaryTab] = useState<'OVERVIEW' | 'DETAILED' | 'TOPICS' | 'ACTIONS' | 'TIMELINE' | 'TRANSCRIPT'>('OVERVIEW');
  const [videoError, setVideoError] = useState<string | null>(null);
  const [showPlayer, setShowPlayer] = useState(false);
  const [pendingSeek, setPendingSeek] = useState<number | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  const getYoutubeId = (url: string) => {
    if (!url) return null;
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
  };

  const youtubeId = summaryData?.video?.source_type === 'youtube' && summaryData?.video?.source_url
    ? getYoutubeId(summaryData.video.source_url)
    : null;

  useEffect(() => {
    if (videoId) {
      loadSummary(parseInt(videoId));
    }
  }, [videoId]);

  useEffect(() => {
    setVideoError(null);
  }, [summaryData?.video.id]);

  const loadSummary = async (id: number) => {
    setLoadingSummary(true);
    try {
      const res = await api.getSummary(id);
      if (res.success) {
        setSummaryData(res);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load summary.');
      navigate('/');
    } finally {
      setLoadingSummary(false);
    }
  };

  const parseTimestampToSeconds = (timeStr: string): number => {
    if (!timeStr) return 0;
    const cleanStr = timeStr.replace(/[\[\]]/g, '').trim();
    
    if (/^\d+(\.\d+)?$/.test(cleanStr)) {
      return parseFloat(cleanStr);
    }
    
    const parts = cleanStr.split(':');
    let hours = 0;
    let minutes = 0;
    let seconds = 0;
    
    if (parts.length === 3) {
      hours = parseFloat(parts[0]) || 0;
      minutes = parseFloat(parts[1]) || 0;
      seconds = parseFloat(parts[2]) || 0;
    } else if (parts.length === 2) {
      minutes = parseFloat(parts[0]) || 0;
      seconds = parseFloat(parts[1]) || 0;
    } else if (parts.length === 1) {
      seconds = parseFloat(parts[0]) || 0;
    }
    
    return (hours * 3600) + (minutes * 60) + seconds;
  };

  const isClickableTimestamp = (timeStr: string) => {
    if (!timeStr || !summaryData) return false;
    const val = parseTimestampToSeconds(timeStr);
    return !isNaN(val) && val <= summaryData.video.duration;
  };

  const executeSeek = (val: number) => {
    if (youtubeId) {
      const iframe = document.getElementById('youtube-player') as HTMLIFrameElement;
      if (iframe && iframe.contentWindow) {
        // Send command to seek to the specified seconds and start playing
        iframe.contentWindow.postMessage(
          JSON.stringify({
            event: 'command',
            func: 'seekTo',
            args: [val, true]
          }),
          '*'
        );
        iframe.contentWindow.postMessage(
          JSON.stringify({
            event: 'command',
            func: 'playVideo',
            args: []
          }),
          '*'
        );
      }
      const playerEl = document.getElementById('youtube-player');
      if (playerEl) {
        playerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } else {
      const video = videoRef.current;
      if (!video) return;
      video.currentTime = val;
      video.play().catch((err) => setVideoError('Playback failed: ' + err.message));
      video.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleTimestampClick = (timeStr: string) => {
    if (!isClickableTimestamp(timeStr)) return;
    const val = parseTimestampToSeconds(timeStr);

    if (!showPlayer) {
      setPendingSeek(val);
      setShowPlayer(true);
    } else {
      executeSeek(val);
    }
  };

  useEffect(() => {
    if (showPlayer && pendingSeek !== null) {
      const timer = setTimeout(() => {
        executeSeek(pendingSeek);
        setPendingSeek(null);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [showPlayer, pendingSeek]);

  const formatDuration = (seconds: number) => {
    if (!seconds) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hrs > 0) {
      return `${hrs}:${styleNumber(mins)}:${styleNumber(secs)}`;
    }
    return `${mins}:${styleNumber(secs)}`;
  };

  const styleNumber = (num: number) => {
    return num.toString().padStart(2, '0');
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTimestamp = (timeStr: string) => {
    if (!timeStr) return '00:00';
    const val = parseTimestampToSeconds(timeStr);
    if (!isNaN(val)) {
      if (summaryData && val > summaryData.video.duration) {
        return timeStr;
      }
      return formatDuration(val);
    }
    return timeStr;
  };

  const videoStreamUrl = summaryData
    ? `${BASE_URL}/api/video/${summaryData.video.id}/stream?token=${getToken()}`
    : '';


  console.log(summaryData);

  return (
    <div className="summary-container">
      <div>
        <button
          onClick={() => navigate('/')}
          className="btn btn-secondary"
          style={{ padding: '0.5rem 0.75rem', fontSize: '0.9rem' }}
        >
          <ChevronLeftIcon size={16} />
          <span>Library Dashboard</span>
        </button>
      </div>

      {loadingSummary && !summaryData ? (
        <div className="glass-panel" style={{ padding: '5rem', textAlign: 'center' }}>
          <RefreshCwIcon size={32} className="spin" style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }} />
          <h3>Fetching Summary Data...</h3>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Loading transcript, executive details, action items, and timelines...</p>
        </div>
      ) : summaryData ? (
        <>
          {/* Summary Header */}
          <div className="summary-header-card glass-panel">
            <div className="summary-title-section">
              <h1>{summaryData.video.title}</h1>
              <div className="summary-meta-row">
                <span>Source: <strong style={{ textTransform: 'capitalize' }}>{summaryData.video.source_type}</strong></span>
                {summaryData.video.duration > 0 && (
                  <span>Duration: <strong>{formatDuration(summaryData.video.duration)}</strong></span>
                )}
                {summaryData.video.source_type !== 'youtube' && (
                  <span>Size: <strong>{formatBytes(summaryData.video.file_size)}</strong></span>
                )}
              </div>
            </div>

            {/* Document Downloads */}
            <div className="download-dropdown">
              <button
                onClick={() => api.downloadFile(summaryData.video.id, 'pdf', `${summaryData.video.title}_summary.pdf`)}
                className="btn btn-secondary"
                style={{ fontSize: '0.85rem' }}
              >
                <DownloadIcon size={14} />
                <span>PDF</span>
              </button>
              <button
                onClick={() => api.downloadFile(summaryData.video.id, 'docx', `${summaryData.video.title}_summary.docx`)}
                className="btn btn-secondary"
                style={{ fontSize: '0.85rem' }}
              >
                <DownloadIcon size={14} />
                <span>Word</span>
              </button>
              <button
                onClick={() => api.downloadFile(summaryData.video.id, 'md', `${summaryData.video.title}_summary.md`)}
                className="btn btn-secondary"
                style={{ fontSize: '0.85rem' }}
              >
                <DownloadIcon size={14} />
                <span>Markdown</span>
              </button>
            </div>
          </div>

          {/* Interactive Split-Screen Workspace Grid */}
          <div className="details-layout-grid">

            {/* Column 1: Audio/Video Player Panel */}
            {!showPlayer ? (
              <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', border: '1px solid var(--border-color)', width: '100%' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>Playback is currently hidden.</span>
                <button className="btn btn-primary" onClick={() => setShowPlayer(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                  <PlayIcon size={14} fill="currentColor" />
                  <span>Open Video Player</span>
                </button>
              </div>
            ) : (
              <div className="video-player-card glass-panel">
                <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', maxWidth: '960px' }}>
                  <h3 style={{ fontFamily: 'var(--font-display)', margin: 0, fontSize: '1.1rem', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <PlayIcon size={16} fill="var(--accent-primary)" />
                    <span>Playback Media</span>
                  </h3>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }} onClick={() => setShowPlayer(false)}>
                    Hide Player
                  </button>
                </div>

                {/* Isolated stacking context so no glass-panel overlay/pseudo-element can intercept clicks on the native controls */}
                <div className="video-click-guard">
                  {youtubeId ? (
                    <iframe
                      id="youtube-player"
                      key={summaryData.video.id}
                      src={`https://www.youtube.com/embed/${youtubeId}?enablejsapi=1&autoplay=0`}
                      title={summaryData.video.title}
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                      className="details-video-el"
                      style={{ border: 'none' }}
                    />
                  ) : (
                    <video
                      key={summaryData.video.id}
                      ref={videoRef}
                      src={videoStreamUrl}
                      controls
                      playsInline
                      preload="metadata"
                      onError={() => {
                        const err = videoRef.current?.error;
                        let msg = 'Unknown video error.';
                        if (err) {
                          switch (err.code) {
                            case err.MEDIA_ERR_ABORTED:
                              msg = 'Playback was aborted.';
                              break;
                            case err.MEDIA_ERR_NETWORK:
                              msg = 'Network error while loading the video.';
                              break;
                            case err.MEDIA_ERR_DECODE:
                              msg = 'Video could not be decoded (unsupported format or codec).';
                              break;
                            case err.MEDIA_ERR_SRC_NOT_SUPPORTED:
                              msg = 'Video source not supported or failed to load. Check the stream URL, token, and CORS headers on the backend.';
                              break;
                          }
                        }
                        setVideoError(msg);
                        console.error('Video error:', err, videoStreamUrl);
                      }}
                      onCanPlay={() => setVideoError(null)}
                      className="details-video-el"
                    />
                  )}
                </div>

                {videoError && (
                  <div
                    style={{
                      marginTop: '0.6rem',
                      padding: '0.6rem 0.8rem',
                      borderRadius: '8px',
                      background: 'rgba(220,38,38,0.1)',
                      color: '#dc2626',
                      fontSize: '0.85rem',
                      lineHeight: 1.4
                    }}
                  >
                    ⚠️ {videoError}
                  </div>
                )}

                <div style={{ marginTop: '0.85rem', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.5', textAlign: 'center' }}>
                  💡 Click timestamps in the <strong>Interactive Timeline</strong> or <strong>Source Transcript</strong> tab to jump directly to topics of interest.
                </div>
              </div>
            )}

            {/* Column 2: Document summaries navigation tabs */}
            <div className="details-content-card">
              {/* Sub Tab Bar Navigation */}
              <div className="summary-tabs">
                <button
                  className={`summary-tab-btn ${summaryTab === 'OVERVIEW' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('OVERVIEW')}
                >
                  <BookOpenIcon size={16} />
                  <span>Overview</span>
                </button>
                <button
                  className={`summary-tab-btn ${summaryTab === 'DETAILED' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('DETAILED')}
                >
                  <FileTextIcon size={16} />
                  <span>Detailed Summary</span>
                </button>
                <button
                  className={`summary-tab-btn ${summaryTab === 'TOPICS' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('TOPICS')}
                >
                  <HelpCircleIcon size={16} />
                  <span>Key Topics</span>
                </button>
                <button
                  className={`summary-tab-btn ${summaryTab === 'ACTIONS' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('ACTIONS')}
                >
                  <ListTodoIcon size={16} />
                  <span>Action Items</span>
                </button>
                <button
                  className={`summary-tab-btn ${summaryTab === 'TIMELINE' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('TIMELINE')}
                >
                  <ClockIcon size={16} />
                  <span>Interactive Timeline</span>
                </button>
                <button
                  className={`summary-tab-btn ${summaryTab === 'TRANSCRIPT' ? 'active' : ''}`}
                  onClick={() => setSummaryTab('TRANSCRIPT')}
                >
                  <AlignLeftIcon size={16} />
                  <span>Source Transcript</span>
                </button>
              </div>

              {/* Tab content panel */}
              <div className="tab-content-wrapper">

                {/* TAB 1: OVERVIEW */}
                {summaryTab === 'OVERVIEW' && (
                  <div>
                    <div className="executive-summary-box glass-panel">
                      <strong style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-display)', fontSize: '1.15rem' }}>Executive Summary</strong>
                      {summaryData.summary.executive_summary}
                    </div>

                    <div className="section-card glass-panel">
                      <h3>Conclusion</h3>
                      <p>{summaryData.summary.conclusion}</p>
                    </div>
                  </div>
                )}

                {/* TAB 2: DETAILED SUMMARY */}
                {summaryTab === 'DETAILED' && (
                  <div className="section-card glass-panel">
                    <h3>Detailed Summary Breakdown</h3>
                    <p style={{ whiteSpace: 'pre-line', fontSize: '1.05rem', lineHeight: '1.8' }}>
                      {summaryData.summary.detailed_summary}
                    </p>
                  </div>
                )}

                {/* TAB 3: KEY TOPICS */}
                {summaryTab === 'TOPICS' && (
                  <div>
                    <h3 style={{ marginBottom: '1.25rem', fontFamily: 'var(--font-display)' }}>Key Topics Mentioned</h3>
                    {(!summaryData.summary.key_topics || summaryData.summary.key_topics.length === 0) ? (
                      <div className="empty-state glass-panel">
                        <p>No key topics extracted for this video.</p>
                      </div>
                    ) : (
                      <div className="topics-grid">
                        {summaryData.summary.key_topics.map((item, idx) => (
                          <div key={idx} className="topic-card glass-panel">
                            <span className="topic-title">
                              {typeof item === 'string' ? item : item.topic || `Topic ${idx + 1}`}
                            </span>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                              {typeof item === 'string' ? 'Important discussion topic in the video.' : item.summary || item.description || ''}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 4: ACTION ITEMS */}
                {summaryTab === 'ACTIONS' && (
                  <div className="section-card glass-panel">
                    <h3>Extracted Action Items</h3>
                    {(!summaryData.summary.action_items || summaryData.summary.action_items.length === 0) ? (
                      <div className="empty-state">
                        <CheckCircle2Icon size={24} style={{ color: 'var(--color-success)' }} />
                        <p>No explicit action items found in the video transcript.</p>
                      </div>
                    ) : (
                      <ul className="action-items-list">
                        {summaryData.summary.action_items.map((item, idx) => (
                          <li key={idx} className="action-item-row">
                            <CheckCircle2Icon size={16} className="action-item-bullet" />
                            <span>{typeof item === 'string' ? item : item.item || item.description || ''}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {/* TAB 5: TIMELINE */}
                {summaryTab === 'TIMELINE' && (
                  <div className="section-card glass-panel">
                    <h3 style={{ marginBottom: '1rem' }}>Interactive Timeline Mapping</h3>
                    {(!summaryData.summary.timeline || summaryData.summary.timeline.length === 0) ? (
                      <div className="empty-state">
                        <p>No timeline elements were extracted for this video.</p>
                      </div>
                    ) : (
                      <div className="timeline">
                        {summaryData.summary.timeline.map((item, idx) => {
                          const clickable = isClickableTimestamp(item.timestamp);
                          return (
                            <div
                              key={idx}
                              className={`timeline-item ${clickable ? 'timeline-item-interactive' : ''}`}
                              style={{ cursor: clickable ? 'pointer' : 'default' }}
                              onClick={() => clickable && handleTimestampClick(item.timestamp)}
                            >
                              <div className="timeline-dot"></div>
                              <div className="timeline-time" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: clickable ? 'var(--accent-primary)' : 'var(--text-secondary)', fontWeight: 'bold' }}>
                                {clickable && <PlayIcon size={10} fill="var(--accent-primary)" />}
                                <span>{formatTimestamp(item.timestamp)}</span>
                              </div>
                              <div className="timeline-content" style={{ marginTop: '0.2rem' }}>
                                {item.event || item.summary || item.description || item.text || ''}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 6: SOURCE TRANSCRIPT */}
                {summaryTab === 'TRANSCRIPT' && (
                  <div className="section-card glass-panel">
                    <h3 style={{ marginBottom: '1.25rem', fontFamily: 'var(--font-display)' }}>Source Transcript</h3>
                    {summaryData.transcript ? (
                      <div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            Source: <strong style={{ color: 'var(--accent-primary)' }}>
                              {summaryData.transcript.model_name === 'youtube-captions' ? 'YouTube Subtitles / Captions' : 'AI Speech-to-Text (Whisper)'}
                            </strong>
                          </span>
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            Language: <strong style={{ textTransform: 'uppercase' }}>{summaryData.transcript.language || 'en'}</strong>
                          </span>
                        </div>
                        
                        {(!summaryData.transcript.segments_json || summaryData.transcript.segments_json.length === 0) ? (
                          <div style={{ whiteSpace: 'pre-line', fontSize: '1.05rem', lineHeight: '1.8', color: 'var(--text-primary)' }}>
                            {summaryData.transcript.cleaned_text || summaryData.transcript.raw_text}
                          </div>
                        ) : (
                          <div className="transcript-scroll-container" style={{ maxHeight: '550px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                            <div className="transcript-segments-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              {summaryData.transcript.segments_json.map((seg: any, idx: number) => {
                                const clickable = isClickableTimestamp(seg.start);
                                return (
                                  <div 
                                    key={idx} 
                                    className={`transcript-segment-row ${clickable ? 'timeline-item-interactive' : ''}`}
                                    style={{ 
                                      display: 'flex', 
                                      gap: '1rem', 
                                      alignItems: 'flex-start', 
                                      padding: '0.6rem 0.8rem', 
                                      borderRadius: '8px', 
                                      cursor: clickable ? 'pointer' : 'default',
                                      borderLeft: '2px solid transparent',
                                      transition: 'all 0.2s ease'
                                    }}
                                    onClick={() => clickable && handleTimestampClick(seg.start)}
                                  >
                                    <div className="timeline-time" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: 'var(--accent-primary)', fontWeight: 'bold', minWidth: '85px', flexShrink: 0 }}>
                                      {clickable && <PlayIcon size={10} fill="var(--accent-primary)" />}
                                      <span>{formatTimestamp(seg.start)}</span>
                                    </div>
                                    <div className="segment-text" style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                                      {seg.text}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="empty-state">
                        <p>No transcript source data available for this video.</p>
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>

          </div>
        </>
      ) : null}
    </div>
  );
}

export default Details;