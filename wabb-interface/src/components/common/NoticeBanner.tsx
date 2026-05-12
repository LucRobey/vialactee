import type { ReactNode } from 'react';

type NoticeTone = 'info' | 'success' | 'warning' | 'error';

const TONE_STYLES: Record<NoticeTone, { border: string; glow: string; background: string; text: string }> = {
  info: {
    border: '#63b3ed',
    glow: 'rgba(99, 179, 237, 0.35)',
    background: 'rgba(12, 20, 28, 0.94)',
    text: '#d7ecff',
  },
  success: {
    border: '#48bb78',
    glow: 'rgba(72, 187, 120, 0.35)',
    background: 'rgba(10, 26, 17, 0.94)',
    text: '#dcffe9',
  },
  warning: {
    border: '#f6ad55',
    glow: 'rgba(246, 173, 85, 0.35)',
    background: 'rgba(31, 20, 8, 0.94)',
    text: '#fff1dc',
  },
  error: {
    border: '#fc8181',
    glow: 'rgba(252, 129, 129, 0.35)',
    background: 'rgba(32, 11, 11, 0.94)',
    text: '#ffe1e1',
  },
};

export const NoticeBanner = ({
  tone = 'info',
  title,
  children,
}: {
  tone?: NoticeTone;
  title?: string;
  children: ReactNode;
}) => {
  const palette = TONE_STYLES[tone];

  return (
    <div
      style={{
        border: `1px solid ${palette.border}`,
        boxShadow: `0 0 0 1px rgba(0,0,0,0.35), 0 0 16px ${palette.glow}`,
        background: palette.background,
        color: palette.text,
        borderRadius: '8px',
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
      }}
    >
      {title ? (
        <span style={{ fontSize: '0.75rem', fontWeight: 900, letterSpacing: '0.08em' }}>
          {title}
        </span>
      ) : null}
      <div style={{ fontSize: '0.82rem', lineHeight: 1.45 }}>
        {children}
      </div>
    </div>
  );
};
