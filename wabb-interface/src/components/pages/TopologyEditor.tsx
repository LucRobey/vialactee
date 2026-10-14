import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { FitBoard } from '../layout/FitBoard';
import { NoticeBanner } from '../common/NoticeBanner';
import { initialTopology, type TopologySegment } from '../../constants/topologyData';
import { loadTopology, type TopologyCable } from '../../utils/topologyStore';
import { sendInstruction, subscribeModeMasterState, type ModeMasterState } from '../../utils/controlBridge';
import { useBridgeStatus } from '../../utils/useBridgeStatus';
import { TopologyInspectorShell } from '../topology/TopologyInspectorShell';
import { TopologyMap } from '../topology/TopologyMap';
import { TopologySegmentInspector } from '../topology/TopologySegmentInspector';

type LiveSegmentPending = { mode?: string; direction?: 'UP' | 'DOWN' };

const liveModeNamesMatch = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

const initialAvailableModes = Array.from(new Set(initialTopology.map(segment => segment.mode))).sort((a, b) => a.localeCompare(b));

const TOPOLOGY_VISUAL_SCALE = 1.2;
const BASE_BOARD_WIDTH = LEGO_MATH.physicalSize(71);
const BASE_BOARD_HEIGHT = LEGO_MATH.physicalSize(38);
const BOARD_WIDTH = BASE_BOARD_WIDTH * TOPOLOGY_VISUAL_SCALE;
const BOARD_HEIGHT = BASE_BOARD_HEIGHT * TOPOLOGY_VISUAL_SCALE;

export const TopologyEditor = () => {
  const [segments, setSegments] = useState<TopologySegment[]>(initialTopology);
  const [selectedSegId, setSelectedSegId] = useState(initialTopology[0].id);
  const [availableModes, setAvailableModes] = useState<string[]>(initialAvailableModes);
  const [cables, setCables] = useState<TopologyCable[]>([]);
  const bridgeStatus = useBridgeStatus();

  const pendingLiveSegmentEditsRef = useRef<Map<string, LiveSegmentPending>>(new Map());
  const isMountedRef = useRef(true);
  const currentHardwareProfileRef = useRef<string | null>(null);

  useEffect(() => {
    loadTopology()
      .then(store => {
        if (!isMountedRef.current) return;
        if (store.segments.length > 0) {
          setSegments(store.segments);
          setSelectedSegId(prev => (store.segments.some(s => s.id === prev) ? prev : store.segments[0].id));
        }
        setCables(store.cables);
      })
      .catch(err => {
        console.error('TopologyEditor: Could not load dynamic topology', err);
      });
  }, []);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const applyModeMasterState = useCallback((state: ModeMasterState) => {
    if (state.hardwareProfile && currentHardwareProfileRef.current !== null && state.hardwareProfile !== currentHardwareProfileRef.current) {
      currentHardwareProfileRef.current = state.hardwareProfile;
      loadTopology()
        .then(store => {
          if (!isMountedRef.current) return;
          if (store.segments.length > 0) {
            setSegments(store.segments);
            setSelectedSegId(store.segments[0].id);
          }
          setCables(store.cables);
        })
        .catch(err => console.error('TopologyEditor: Could not reload topology', err));
    } else if (state.hardwareProfile && currentHardwareProfileRef.current === null) {
      currentHardwareProfileRef.current = state.hardwareProfile;
    }

    if (state.availableModes.length > 0) {
      setAvailableModes(state.availableModes);
    }

    setSegments(prev => prev.map(seg => {
      const liveSegment = state.segments.find(remote => remote.id === seg.id);
      if (!liveSegment) {
        return seg;
      }

      const map = pendingLiveSegmentEditsRef.current;
      let mode = liveSegment.mode;
      let direction = liveSegment.direction;

      const consumePending = (id: string, next: LiveSegmentPending | undefined) => {
        if (!next || (next.mode === undefined && next.direction === undefined)) {
          map.delete(id);
        } else {
          map.set(id, next);
        }
      };

      let pending = map.get(seg.id);
      if (pending?.mode !== undefined) {
        if (liveModeNamesMatch(liveSegment.mode, pending.mode)) {
          const rest: LiveSegmentPending = { ...pending };
          delete rest.mode;
          pending = Object.keys(rest).length ? rest : undefined;
          consumePending(seg.id, pending);
        } else {
          mode = pending.mode;
        }
      }

      pending = map.get(seg.id);
      if (pending?.direction !== undefined) {
        if (liveSegment.direction === pending.direction) {
          const rest: LiveSegmentPending = { ...pending };
          delete rest.direction;
          pending = Object.keys(rest).length ? rest : undefined;
          consumePending(seg.id, pending);
          direction = liveSegment.direction;
        } else {
          direction = pending.direction;
        }
      }

      return { ...seg, mode, direction };
    }));
  }, []);

  useEffect(() => subscribeModeMasterState(applyModeMasterState), [applyModeMasterState]);

  const selectedSeg = useMemo(
    () => segments.find(segment => segment.id === selectedSegId) ?? segments[0],
    [segments, selectedSegId]
  );

  const handleModeSelect = (modeName: string) => {
    sendInstruction({
      page: 'topology',
      action: 'select_segment_mode',
      payload: { segmentId: selectedSegId, mode: modeName }
    });
    const prev = pendingLiveSegmentEditsRef.current.get(selectedSegId) ?? {};
    pendingLiveSegmentEditsRef.current.set(selectedSegId, { ...prev, mode: modeName });
    setSegments(prev => prev.map(seg => seg.id === selectedSegId ? { ...seg, mode: modeName } : seg));
  };

  const handleDirectionToggle = (event: MouseEvent, id: string) => {
    event.stopPropagation();
    setSegments(prev => prev.map(seg => {
      if (seg.id !== id) {
        return seg;
      }
      const direction: TopologySegment['direction'] = seg.direction === 'UP' ? 'DOWN' : 'UP';
      sendInstruction({
        page: 'topology',
        action: 'toggle_segment_direction',
        payload: { segmentId: id, direction }
      });
      const prevPending = pendingLiveSegmentEditsRef.current.get(id) ?? {};
      pendingLiveSegmentEditsRef.current.set(id, { ...prevPending, direction });
      return { ...seg, direction };
    }));
  };

  const handleSegmentSelect = (segmentId: string) => {
    setSelectedSegId(segmentId);
  };

  return (
    <FitBoard width={BOARD_WIDTH} height={BOARD_HEIGHT}>
      <div style={{
        position: 'relative',
        width: `${BASE_BOARD_WIDTH}px`,
        height: `${BASE_BOARD_HEIGHT}px`,
        transform: `scale(${TOPOLOGY_VISUAL_SCALE})`,
        transformOrigin: 'top left',
      }}>
        {bridgeStatus !== 'open' ? (
          <div style={{ position: 'absolute', top: '12px', left: '770px', width: '470px', zIndex: 40 }}>
            <NoticeBanner tone={bridgeStatus === 'connecting' ? 'warning' : 'error'} title="TOPOLOGY LINK">
              {bridgeStatus === 'connecting'
                ? 'Reconnecting to the live controller. Segment changes may be delayed for a moment.'
                : 'Controller offline. Segment changes cannot be confirmed right now.'}
            </NoticeBanner>
          </div>
        ) : null}

        <TopologyMap
          segments={segments}
          selectedSegId={selectedSegId}
          onSelectSegment={handleSegmentSelect}
          onToggleDirection={handleDirectionToggle}
          segmentShiftCols={2}
          cables={cables}
        />

        <TopologyInspectorShell />

        <TopologySegmentInspector
          selectedSeg={selectedSeg}
          availableModes={availableModes}
          onModeSelect={handleModeSelect}
        />
      </div>
    </FitBoard>
  );
};
