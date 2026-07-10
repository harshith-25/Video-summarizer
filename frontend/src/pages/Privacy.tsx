import { useNavigate } from 'react-router-dom';
import { ChevronLeft as ChevronLeftIcon } from 'lucide-react';

export default function Privacy() {
  const navigate = useNavigate();

  return (
    <div className="summary-container" style={{ maxWidth: '800px', margin: '2rem auto' }}>
      <div>
        <button
          onClick={() => navigate('/')}
          className="btn btn-secondary"
          style={{ padding: '0.5rem 0.75rem', fontSize: '0.9rem', marginBottom: '1.5rem' }}
        >
          <ChevronLeftIcon size={16} />
          <span>Back to Home</span>
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '2.5rem', lineHeight: '1.8' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', marginBottom: '1.5rem', color: 'var(--accent-primary)' }}>
          Privacy Policy
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '2rem' }}>
          Last Updated: July 9, 2026
        </p>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>1. Introduction</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Welcome to the AI Video Summarizer. We are committed to protecting your privacy and handling your data securely. 
            This Privacy Policy explains how our application interacts with your Google account, YouTube API services, and any other data you upload.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>2. Information We Access and Process</h3>
          <ul style={{ color: 'var(--text-secondary)', paddingLeft: '1.5rem', listStyleType: 'disc' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>YouTube Captions/Subtitles:</strong> When you summarize a YouTube video, our application accesses the video's public subtitles or captions. If the video does not have captions, we process the video's public audio stream to transcribe the audio into text using AI Speech-to-Text.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Video Metadata:</strong> We retrieve the video title, thumbnail, duration, and author name to present them in your summarization dashboard.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>User Account Information:</strong> We store your registered email and username to manage your personal dashboard, job tracking history, and generated PDF/Word documents.
            </li>
          </ul>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>3. How We Use Google OAuth Data</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Our application integrates with Google OAuth to retrieve captions and details of YouTube videos on your behalf.
          </p>
          <ul style={{ color: 'var(--text-secondary)', paddingLeft: '1.5rem', listStyleType: 'disc' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              We only use OAuth authorization to download captions and access video metadata.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              We do not store or cache your long-lived Google OAuth tokens. Tokens are used strictly during the request session and are immediately discarded.
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              We do not modify, write, or delete any data on your Google account or your YouTube channel.
            </li>
          </ul>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>4. Data Sharing and Third-Party Services</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            We do not sell, rent, or trade your personal data or video contents to third parties. To generate video summaries, the extracted text segments of the video are sent securely to <strong>Mistral AI APIs</strong> for processing. No personal identifiers are shared with Mistral AI.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>5. Data Security</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            We implement industry-standard security measures (SSL/TLS encryption, secure database hashing) to protect your accounts and generated documents from unauthorized access, modification, or disclosure.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>6. Contact Us</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            If you have any questions or concerns regarding this Privacy Policy or your data usage, please contact us at: <br />
            <strong>Email:</strong> support@silfratech.in
          </p>
        </section>
      </div>
    </div>
  );
}