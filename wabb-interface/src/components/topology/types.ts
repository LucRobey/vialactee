export type EditorMode = 'LIVE' | 'MODIFY' | 'BUILD';

export type TopologyNoticeTone = 'info' | 'success' | 'warning' | 'error';

export type TopologyNotice = {
  tone: TopologyNoticeTone;
  title: string;
  message: string;
};
