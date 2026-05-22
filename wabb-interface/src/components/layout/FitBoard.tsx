import { useEffect, useRef, useState, type ReactNode } from 'react';

export const FitBoard = ({ width, height, children }: { width: number; height: number; children: ReactNode }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const update = () => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const bottomPadding = Number.parseFloat(window.getComputedStyle(el.parentElement ?? el).paddingBottom) || 0;
      setScale(Math.max(0.1, Math.min(1, rect.width / width, (window.innerHeight - rect.top - bottomPadding) / height)));
    };

    update();
    const observer = new ResizeObserver(update);
    if (ref.current) observer.observe(ref.current);
    window.addEventListener('resize', update);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [height, width]);

  return (
    <div ref={ref} style={{ width: '100%', height: `${height * scale}px`, overflow: 'hidden' }}>
      <div style={{ width, height, transform: `scale(${scale})`, transformOrigin: 'top left' }}>
        {children}
      </div>
    </div>
  );
};
