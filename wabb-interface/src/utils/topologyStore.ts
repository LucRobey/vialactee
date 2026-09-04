import { MAP_OFFSET_C, MAP_OFFSET_R, type TopologySegment } from '../constants/topologyData';

export type TopologyCable = {
  start: [number, number];
  end: [number, number];
  cp1: [number, number];
  cp2: [number, number];
};

export type RawSegmentDefinition = {
  id?: string;
  name: string;
  size?: number;
  order?: number;
  orientation?: 'horizontal' | 'vertical';
  ui?: {
    col?: number;
    row?: number;
    w?: number;
    h?: number;
    color?: string;
  };
};

export type TopologyPayload = {
  segments: RawSegmentDefinition[];
  cables?: TopologyCable[];
};

export type TopologyStore = {
  segments: TopologySegment[];
  cables: TopologyCable[];
};

export const normalizeTopologySegments = (rawSegments: RawSegmentDefinition[]): TopologySegment[] => {
  return rawSegments.map(raw => {
    const id = raw.id || raw.name.replace(/^Segment\s+/, '').trim();
    const ui = raw.ui || {};
    const col = (ui.col ?? 0) + MAP_OFFSET_C;
    const row = (ui.row ?? 0) + MAP_OFFSET_R;
    const w = ui.w ?? 2;
    const h = ui.h ?? 2;
    const color = ui.color || '#3264ff';
    const orientation = raw.orientation || 'horizontal';

    return {
      id,
      name: raw.name,
      col,
      row,
      w,
      h,
      color,
      orientation,
      mode: 'Rainbow',
      direction: 'UP',
    };
  });
};

export const loadTopology = async (): Promise<TopologyStore> => {
  const response = await fetch('/api/topology');
  if (!response.ok) {
    throw new Error(`Failed to load topology from /api/topology: ${response.status} ${response.statusText}`);
  }

  const data: TopologyPayload = await response.json();
  const segments = normalizeTopologySegments(Array.isArray(data.segments) ? data.segments : []);
  const cables = Array.isArray(data.cables) ? data.cables : [];

  return { segments, cables };
};
