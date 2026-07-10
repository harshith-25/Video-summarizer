import { useNavigate } from 'react-router-dom';
import { ChevronLeft as ChevronLeftIcon } from 'lucide-react';

export default function Terms() {
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
          Terms of Service
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '2rem' }}>
          Last Updated: July 9, 2026
        </p>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>1. Agreement to Terms</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            By accessing or using the Video Summarizer application ("Service") provided by SilfraTech, you agree to be bound by these Terms of Service. If you do not agree to all of these terms, do not use the Service.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>2. Description of Service</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            The Service provides AI-driven transcription, summarization, and analysis of videos. The accuracy of summaries is dependent on the clarity of the source audio and language-model behavior. Summaries are provided for convenience and information.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>3. User Accounts</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            You must register for an account to access some features. You are responsible for keeping your password secure. You must notify us immediately of any breach of security or unauthorized use of your account.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>4. Content and intellectual Property</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            You retain all ownership rights to any video files or links you upload. By using the Service, you grant us a temporary, worldwide, non-exclusive license to process your content solely to generate transcriptions and summaries as requested.
          </p>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            We do not sell, rent, or distribute your uploaded files or the generated transcripts to any third-party organizations.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>5. Limitation of Liability</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            In no event shall SilfraTech or its developers be liable for any direct, indirect, incidental, special, or consequential damages resulting from the use or inability to use this service, including data loss or translation inaccuracies.
          </p>
        </section>

        <section style={{ marginBottom: '2rem' }}>
          <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.75rem' }}>6. Modifications to Terms</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            We reserve the right to modify these Terms of Service at any time. We will indicate changes by updating the "Last Updated" date at the top of this document.
          </p>
        </section>
      </div>
    </div>
  );
}