import React from 'react';

export const GridSpot = ({ col, row, children, style }: { col: number, row: number, children: React.ReactNode, style?: React.CSSProperties }) => (
  <div style={{ position: 'absolute', left: `${col * 30}px`, top: `${row * 30}px`, ...style }}>
    {children}
  </div>
);
