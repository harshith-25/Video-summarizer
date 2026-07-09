import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Link as LinkIcon, 
  Upload as UploadIcon, 
  FileText as FileTextIcon, 
  Trash2 as Trash2Icon, 
  RefreshCw as RefreshCwIcon, 
  Video as VideoIcon
} from 'lucide-react';
import { api, BASE_URL, getToken } from '../api';

type VideoItem = {
  id: number | null;
  job_id: string | null;
  title: string;
  source_type: string;
  source_url: string | null;
  file_size: number;
  duration: number;
  created_at: string | null;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error_message: string | null;
};

type DashboardProps = {
  setErrorMsg: (msg: string | null) => void;
  setSuccessMsg: (msg: string | null) => void;
};

const LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi (हिंदी)' },
  { code: 'kn', name: 'Kannada (ಕನ್ನಡ)' },
  { code: 'bn', name: 'Bengali (বাংলা)' },
  { code: 'gu', name: 'Gujarati (ગુજરાતી)' },
  { code: 'ml', name: 'Malayalam (മലയാളം)' },
  { code: 'mr', name: 'Marathi (मराठी)' },
  { code: 'pa', name: 'Punjabi (ਪੰਜਾਬੀ)' },
  { code: 'ta', name: 'Tamil (தமிழ்)' },
  { code: 'te', name: 'Telugu (తెలుగు)' },
  { code: 'ur', name: 'Urdu (اردو)' }
];

export function Dashboard({ setErrorMsg, setSuccessMsg }: DashboardProps) {
  const navigate = useNavigate();
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissionTab, setSubmissionTab] = useState<'URL' | 'UPLOAD'>('URL');

  // URL Form
  const [videoUrl, setVideoUrl] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [targetLanguage, setTargetLanguage] = useState('en');

  // Upload Form
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchVideos();
    
    // Check for YouTube OAuth errors passed from backend redirect
    const params = new URLSearchParams(window.location.search);
    const error = params.get('error');
    if (error) {
      setErrorMsg(error);
      // Clean up URL query parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const fetchVideos = async () => {
    setLoadingVideos(true);
    try {
      const res = await api.getVideos();
      if (res.videos) {
        setVideos(res.videos);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to fetch videos.');
    } finally {
      setLoadingVideos(false);
    }
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoUrl) return;

    setErrorMsg(null);

    const isYouTubeUrl = (url: string) => {
      const lower = url.toLowerCase();
      return lower.includes('youtube.com') || lower.includes('youtu.be');
    };

    if (isYouTubeUrl(videoUrl)) {
      const token = getToken();
      if (!token) {
        setErrorMsg('Authentication token not found. Please log in again.');
        return;
      }
      
      const queryParams = new URLSearchParams({
        video_url: videoUrl,
        token: token,
        language: targetLanguage,
      });
      if (customTitle) {
        queryParams.append('title', customTitle);
      }
      
      window.location.href = `${BASE_URL}/api/youtube/auth/initiate?${queryParams.toString()}`;
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.submitUrl(videoUrl, customTitle || undefined, targetLanguage);
      if (res.job_id) {
        setVideoUrl('');
        setCustomTitle('');
        setTargetLanguage('en');
        navigate(`/tracker/${res.job_id}`);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Submission failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setErrorMsg(null);
    setSubmitting(true);
    setUploadProgress(0);

    try {
      const res: any = await api.uploadFile(
        selectedFile,
        customTitle || undefined,
        targetLanguage,
        (pct) => setUploadProgress(pct)
      );
      if (res.job_id) {
        setSelectedFile(null);
        setCustomTitle('');
        setTargetLanguage('en');
        setUploadProgress(0);
        navigate(`/tracker/${res.job_id}`);
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Upload failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteVideo = async (e: React.MouseEvent, videoId: number) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this video summary and all linked files?')) {
      return;
    }

    try {
      await api.deleteSummary(videoId);
      setSuccessMsg('Video summary deleted successfully.');
      fetchVideos();
    } catch (e: any) {
      setErrorMsg(e.message || 'Delete operation failed.');
    }
  };

  const handleDeleteJob = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this job record?')) {
      return;
    }

    try {
      await api.deleteJob(jobId);
      setSuccessMsg('Deleted successfully.');
      fetchVideos();
    } catch (e: any) {
      setErrorMsg(e.message || 'Delete operation failed.');
    }
  };

  const formatDuration = (seconds: number) => {
    if (!seconds) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="dashboard-grid">
      {/* Left Column: Video Submission */}
      <div className="dashboard-panel glass-panel">
        <h2 className="panel-title">
          <PlusIconWrapper />
          <span>Summarize Video</span>
        </h2>

        <div className="tab-switch">
          <button 
            className={`tab-switch-btn ${submissionTab === 'URL' ? 'active' : ''}`}
            onClick={() => { setSelectedFile(null); setSubmissionTab('URL'); }}
          >
            <LinkIcon size={14} />
            <span>URL Source</span>
          </button>
          <button 
            className={`tab-switch-btn ${submissionTab === 'UPLOAD' ? 'active' : ''}`}
            onClick={() => { setVideoUrl(''); setSubmissionTab('UPLOAD'); }}
          >
            <UploadIcon size={14} />
            <span>Local File</span>
          </button>
        </div>

        {submissionTab === 'URL' ? (
          <form onSubmit={handleUrlSubmit}>
            <div className="form-group">
              <label className="form-label">Video URL</label>
              <input 
                type="url" 
                className="form-input" 
                placeholder="YouTube, Vimeo, Drive, Dropbox..." 
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                required 
              />
              <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Supports YouTube, Vimeo, Drive, OneDrive, Dropbox, or direct video links.
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Custom Title (Optional)</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder="My summarized video" 
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Target Summary Language</label>
              <select 
                className="form-input" 
                value={targetLanguage} 
                onChange={(e) => setTargetLanguage(e.target.value)}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={submitting}>
              {submitting ? 'Submitting...' : 'Analyze Video'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleUploadSubmit}>
            <div className="form-group">
              <label className="form-label">Select Video File</label>
              <input 
                type="file" 
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm"
                onChange={handleFileChange}
              />
              <div 
                className={`drop-zone ${dragActive ? 'active' : ''}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadIcon size={32} className="drop-zone-icon" />
                <div>
                  <strong>Click to browse</strong> or drag & drop here
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  MP4, MOV, AVI, MKV, WebM up to 500MB
                </div>
              </div>
            </div>

            {selectedFile && (
              <div className="selected-file-banner">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 0 }}>
                  <FileTextIcon size={16} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {selectedFile.name} ({formatBytes(selectedFile.size)})
                  </span>
                </div>
                <button type="button" className="btn-secondary" style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-danger)', fontWeight: 'bold' }} onClick={() => setSelectedFile(null)}>✕</button>
              </div>
            )}

            <div className="form-group" style={{ marginTop: '1.25rem' }}>
              <label className="form-label">Custom Title (Optional)</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder={selectedFile ? selectedFile.name.split('.')[0] : "My video file"} 
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Target Summary Language</label>
              <select 
                className="form-input" 
                value={targetLanguage} 
                onChange={(e) => setTargetLanguage(e.target.value)}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
            </div>

            {uploadProgress > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  <span>Uploading...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="progress-bar-container" style={{ margin: '0', height: '6px' }}>
                  <div className="progress-bar-fill" style={{ width: `${uploadProgress}%` }}></div>
                </div>
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={!selectedFile || submitting}>
              {submitting ? 'Processing Upload...' : 'Upload and Summarize'}
            </button>
          </form>
        )}
      </div>

      {/* Right Column: Library */}
      <div className="dashboard-panel glass-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h2 className="panel-title" style={{ margin: 0 }}>
            <HistoryIconWrapper />
            <span>Your Library</span>
          </h2>
          <button onClick={fetchVideos} className="btn btn-secondary" style={{ padding: '0.45rem 0.65rem' }} disabled={loadingVideos}>
            <RefreshCwIcon size={14} className={loadingVideos ? 'spin' : ''} />
          </button>
        </div>

        {loadingVideos && videos.length === 0 ? (
          <div className="empty-state">
            <RefreshCwIcon size={24} className="spin" />
            <p>Loading library records...</p>
          </div>
        ) : videos.length === 0 ? (
          <div className="empty-state">
            <VideoIcon size={32} className="empty-state-icon" />
            <p>No video summaries in your library yet.</p>
            <p style={{ fontSize: '0.85rem' }}>Submit a URL or upload a file above to begin.</p>
          </div>
        ) : (
          <div className="video-list">
            {videos.map((vid, idx) => (
              <div 
                key={vid.id || vid.job_id || idx} 
                className="video-card glass-panel" 
                style={{ cursor: vid.status === 'completed' ? 'pointer' : 'default' }}
                onClick={() => vid.status === 'completed' && vid.id && navigate(`/summary/${vid.id}`)}
              >
                <div className="video-card-info">
                  <div className="video-card-title" title={vid.title}>
                    {vid.title.length > 30 ? vid.title.substring(0, 30) + '...' : vid.title}
                  </div>
                  <div className="video-card-meta">
                    <span>{vid.source_type.toUpperCase()}</span>
                    {vid.duration > 0 && (
                      <>
                        <span>•</span>
                        <span>{formatDuration(vid.duration)}</span>
                      </>
                    )}
                    <span>•</span>
                    <span className={`status-badge status-${vid.status}`}>
                      {vid.status}
                    </span>
                  </div>
                  {vid.status === 'processing' && (
                    <div style={{ marginTop: '0.35rem' }}>
                      <div className="progress-bar-container" style={{ margin: '0', height: '4px' }}>
                        <div className="progress-bar-fill" style={{ width: `${vid.progress}%` }}></div>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', marginTop: '0.15rem', display: 'block' }}>
                        {vid.message} ({vid.progress}%)
                      </span>
                    </div>
                  )}
                  {vid.status === 'failed' && vid.error_message && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-danger)', marginTop: '0.15rem', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      Error: {vid.error_message}
                    </span>
                  )}
                  {vid.status === 'queued' && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-warning)', marginTop: '0.15rem', display: 'block' }}>
                      {vid.message}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {vid.status === 'completed' && (
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>View</span>
                  )}
                  {(vid.status === 'failed' || vid.status === 'processing' || vid.status === 'queued') && vid.job_id && (
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '0.35rem 0.55rem' }} 
                      onClick={(e) => { e.stopPropagation(); navigate(`/tracker/${vid.job_id}`); }}
                    >
                      Track
                    </button>
                  )}
                  {(vid.id || vid.job_id) && (
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        if (vid.id) {
                          handleDeleteVideo(e, vid.id);
                        } else if (vid.job_id) {
                          handleDeleteJob(e, vid.job_id);
                        }
                      }}
                      className="btn btn-danger" 
                      style={{ padding: '0.45rem' }}
                      title={vid.id ? "Delete summary" : "Delete job record"}
                    >
                      <Trash2Icon size={14} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function PlusIconWrapper() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary)' }}>
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  );
}

function HistoryIconWrapper() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary)' }}>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
      <polyline points="3 3 3 8 8 8"></polyline>
      <line x1="12" y1="7" x2="12" y2="12"></line>
      <line x1="12" y1="12" x2="16" y2="14"></line>
    </svg>
  );
}

export default Dashboard;