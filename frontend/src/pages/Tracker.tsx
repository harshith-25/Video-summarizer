import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ChevronLeft as ChevronLeftIcon, 
  RefreshCw as RefreshCwIcon, 
  AlertTriangle as AlertTriangleIcon 
} from 'lucide-react';
import { api } from '../api';

type TrackerProps = {
  setErrorMsg: (msg: string | null) => void;
  setSuccessMsg: (msg: string | null) => void;
};

export default function Tracker({ setErrorMsg, setSuccessMsg }: TrackerProps) {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<any>({ progress: 0, message: 'Initiating pipeline...', status: 'queued' });
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) return;

    // First fetch
    fetchStatus();

    // Start polling every 2 seconds
    intervalRef.current = window.setInterval(async () => {
      await fetchStatus();
    }, 8000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [jobId]);

  const fetchStatus = async () => {
    if (!jobId) return;
    try {
      const res = await api.getJobStatus(jobId);
      if (res.job) {
        setJob(res.job);
        if (res.job.status === 'completed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setSuccessMsg('Video summary generated successfully!');
          if (res.job.video_id) {
            navigate(`/summary/${res.job.video_id}`);
          } else {
            navigate('/');
          }
        } else if (res.job.status === 'failed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setErrorMsg(res.job.error_message || 'Processing failed.');
        }
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  return (
    <div className="tracker-wrapper glass-panel">
      <h2 style={{ fontFamily: 'var(--font-display)', marginBottom: '1rem' }}>Processing Pipeline</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
        Your video is currently running through the Speech-to-Text and AI Summary pipeline.
      </p>

      <div className="progress-bar-container" style={{ height: '12px' }}>
        <div className="progress-bar-fill" style={{ width: `${job.progress}%` }}></div>
      </div>

      <div className="tracker-message">{job.message}</div>
      <div className="tracker-submessage">Progress: {job.progress}%</div>

      {job.status === 'failed' && (
        <div className="error-box" style={{ marginTop: '2rem' }}>
          <AlertTriangleIcon size={18} />
          <span>Error: {job.error_message || 'Pipeline process crashed.'}</span>
        </div>
      )}

      <div style={{ marginTop: '2.5rem', display: 'flex', justifyContent: 'center', gap: '1rem' }}>
        <button 
          onClick={() => navigate('/')} 
          className="btn btn-secondary"
        >
          <ChevronLeftIcon size={16} />
          <span>Dashboard Library</span>
        </button>
        {job.status === 'failed' && (
          <button 
            onClick={fetchStatus}
            className="btn btn-primary"
          >
            <RefreshCwIcon size={14} />
            <span>Retry Status Check</span>
          </button>
        )}
      </div>
    </div>
  );
}
