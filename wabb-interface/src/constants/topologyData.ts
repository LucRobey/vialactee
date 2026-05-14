export const MAP_OFFSET_C = 2;
export const MAP_OFFSET_R = 3;
export const INSPECTOR_OFFSET_C = 2;
export const INSPECTOR_OFFSET_R = 5;
export const CONFIGURATOR_OFFSET_C = 49;
export const CONFIGURATOR_OFFSET_R = 5;

export type SegmentOrientation = 'horizontal' | 'vertical';
export type SegmentDirection = 'UP' | 'DOWN';

export type TopologySegment = {
  id: string;
  name: string;
  col: number;
  row: number;
  w: number;
  h: number;
  color: string;
  orientation: SegmentOrientation;
  mode: string;
  direction: SegmentDirection;
};

export const relativeTopology: TopologySegment[] = [
  // Strip 0
  { id: "v4", name: "segment_v4", col: 43, row: 1, w: 2, h: 18, color: '#3264ff', orientation: 'vertical', mode: 'Plasma Fire', direction: 'UP' },
  { id: "h32", name: "segment_h32", col: 38, row: -3, w: 6, h: 2, color: '#ff3232', orientation: 'horizontal', mode: 'Hyper Strobe', direction: 'UP' },
  { id: "h31", name: "segment_h31", col: 38, row: 7, w: 6, h: 2, color: '#ff00ff', orientation: 'horizontal', mode: 'Rainbow', direction: 'UP' },
  { id: "h30", name: "segment_h30", col: 38, row: 16, w: 6, h: 2, color: '#969696', orientation: 'horizontal', mode: 'Shining Stars', direction: 'UP' },
  { id: "v3", name: "segment_v3", col: 38, row: -1, w: 2, h: 18, color: '#00ffff', orientation: 'vertical', mode: 'Matrix Rain', direction: 'UP' },
  { id: "h20", name: "segment_h20", col: 29, row: 4, w: 10, h: 2, color: '#96ff96', orientation: 'horizontal', mode: 'Synesthesia', direction: 'UP' },
  { id: "h00", name: "segment_h00", col: 0, row: -1, w: 22, h: 2, color: '#0000ff', orientation: 'horizontal', mode: 'Coloured Middle Wave', direction: 'UP' },
  // Strip 1
  { id: "v2", name: "segment_v2", col: 29, row: 4, w: 2, h: 18, color: '#00ff00', orientation: 'vertical', mode: 'Opposite Sides', direction: 'UP' },
  { id: "h11", name: "segment_h11", col: 21, row: 2, w: 9, h: 2, color: '#ff9664', orientation: 'horizontal', mode: 'Flying Ball', direction: 'UP' },
  { id: "h10", name: "segment_h10", col: 21, row: 16, w: 9, h: 2, color: '#9632c8', orientation: 'horizontal', mode: 'PSG', direction: 'UP' },
  { id: "v1", name: "segment_v1", col: 21, row: -1, w: 2, h: 18, color: '#ffff00', orientation: 'vertical', mode: 'Bary Rainbow', direction: 'UP' },
];

export const initialTopology = relativeTopology.map(seg => ({
  ...seg,
  col: seg.col + MAP_OFFSET_C,
  row: seg.row + MAP_OFFSET_R
}));
