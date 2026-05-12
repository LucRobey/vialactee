import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type MouseEvent } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { NoticeBanner } from '../common/NoticeBanner';
import { initialTopology, type TopologySegment } from '../../constants/topologyData';
import { sendInstruction, subscribeModeMasterState, type ModeMasterState } from '../../utils/controlBridge';
import { loadConfigurationStore, saveConfigurationStore, type ModeSettingsMap, type SegmentConfiguration } from '../../utils/configurationStore';
import { useBridgeStatus } from '../../utils/useBridgeStatus';
import { TopologyConfigurationPanel } from '../topology/TopologyConfigurationPanel';
import { TopologyEditorModeSwitch } from '../topology/TopologyEditorModeSwitch';
import { TopologyInspectorShell } from '../topology/TopologyInspectorShell';
import { TopologyMap } from '../topology/TopologyMap';
import { TopologyPlaylistPanel } from '../topology/TopologyPlaylistPanel';
import { TopologySegmentInspector } from '../topology/TopologySegmentInspector';
import type { EditorMode, TopologyNotice, TopologyNoticeTone } from '../topology/types';

type LiveSegmentPending = { mode?: string; direction?: 'UP' | 'DOWN' };

const liveModeNamesMatch = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();
const sameName = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();

const cloneModeSettings = (modeSettings: ModeSettingsMap = {}) =>
  Object.fromEntries(
    Object.entries(modeSettings).map(([modeName, settings]) => [modeName, { ...settings }])
  ) as ModeSettingsMap;

const initialAvailableModes = Array.from(new Set(initialTopology.map(segment => segment.mode))).sort((a, b) => a.localeCompare(b));

export const TopologyEditor = () => {
  const [segments, setSegments] = useState<TopologySegment[]>(initialTopology);
  const [selectedSegId, setSelectedSegId] = useState(initialTopology[0].id);
  const [editorMode, setEditorMode] = useState<EditorMode>('LIVE');
  const [configName, setConfigName] = useState('');
  const [selectedConfigName, setSelectedConfigName] = useState('');
  const [apiPlaylists, setApiPlaylists] = useState<string[]>([]);
  const [apiConfigurations, setApiConfigurations] = useState<Record<string, SegmentConfiguration[]>>({});
  const [activeModeSettings, setActiveModeSettings] = useState<ModeSettingsMap>({});
  const [availableModes, setAvailableModes] = useState<string[]>(initialAvailableModes);
  const [playlistIndex, setPlaylistIndex] = useState(0);
  const [playlistNameDraft, setPlaylistNameDraft] = useState('');
  const [isSavingStore, setIsSavingStore] = useState(false);
  const [notice, setNotice] = useState<TopologyNotice | null>(null);
  const playlist = apiPlaylists[playlistIndex] || '';
  const playlistLightColor = playlist ? (playlistIndex % 2 === 0 ? '#00ffff' : '#ff00ff') : '#555';
  const bridgeStatus = useBridgeStatus();

  const pendingLiveSegmentEditsRef = useRef<Map<string, LiveSegmentPending>>(new Map());
  const isMountedRef = useRef(true);
  const noticeTimerRef = useRef<number | null>(null);

  const showNotice = useCallback((tone: TopologyNoticeTone, title: string, message: string) => {
    setNotice({ tone, title, message });
    if (noticeTimerRef.current !== null) {
      window.clearTimeout(noticeTimerRef.current);
    }
    noticeTimerRef.current = window.setTimeout(() => {
      setNotice(current => (current?.message === message ? null : current));
    }, 4200);
  }, []);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (noticeTimerRef.current !== null) {
        window.clearTimeout(noticeTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (editorMode !== 'LIVE') {
      pendingLiveSegmentEditsRef.current.clear();
    }
  }, [editorMode]);

  const applyStoredConfigurationToSegments = useCallback((playlistKey: string, configurationName: string) => {
    if (!playlistKey || !configurationName) {
      return;
    }

    const configsForPlaylist = apiConfigurations[playlistKey] || [];
    const selectedConfig = configsForPlaylist.find(config => sameName(config.name, configurationName));
    if (!selectedConfig) {
      return;
    }

    setSegments(prev =>
      prev.map(seg => {
        const key = `Segment ${seg.id}`;
        const mode = selectedConfig.modes[key] || seg.mode;
        const direction = (selectedConfig.way?.[key] as TopologySegment['direction'] | undefined) || seg.direction || 'UP';
        return { ...seg, mode, direction };
      })
    );
  }, [apiConfigurations]);

  const applyModeMasterState = useCallback((state: ModeMasterState) => {
    if (state.playlists.length > 0) {
      setApiPlaylists(state.playlists);
    }
    if (state.availableModes.length > 0) {
      setAvailableModes(state.availableModes);
    }

    setActiveModeSettings(cloneModeSettings(state.modeSettings));

    if (editorMode !== 'LIVE') {
      return;
    }

    if (state.activePlaylist) {
      const playlists = state.playlists.length > 0 ? state.playlists : apiPlaylists;
      const nextPlaylistIndex = playlists.findIndex(name => sameName(name, state.activePlaylist ?? ''));
      if (nextPlaylistIndex >= 0) {
        setPlaylistIndex(nextPlaylistIndex);
        setPlaylistNameDraft(playlists[nextPlaylistIndex] || '');
      }
    }

    if (state.activeConfiguration) {
      setConfigName(state.activeConfiguration);
      setSelectedConfigName(state.activeConfiguration);
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
  }, [apiPlaylists, editorMode]);

  useEffect(() => {
    loadConfigurationStore()
      .then(store => {
        if (!isMountedRef.current) {
          return;
        }
        setApiPlaylists(store.playlists);
        setApiConfigurations(store.configurations);
        setPlaylistNameDraft(store.playlists[0] || '');
      })
      .catch(error => {
        console.error('Could not load configurations', error);
        showNotice('error', 'CONFIGURATION STORE', error instanceof Error ? error.message : 'Could not load configurations.');
      });
  }, [showNotice]);

  useEffect(() => subscribeModeMasterState(applyModeMasterState), [applyModeMasterState]);

  const runStoreMutation = useCallback(async (operation: () => Promise<void>) => {
    if (isSavingStore) {
      showNotice('warning', 'SAVE IN PROGRESS', 'Please wait for the current configuration write to finish.');
      return false;
    }

    setIsSavingStore(true);
    try {
      await operation();
      return true;
    } catch (error) {
      console.error(error);
      showNotice('error', 'SAVE FAILED', error instanceof Error ? error.message : 'Could not persist the configuration store.');
      return false;
    } finally {
      if (isMountedRef.current) {
        setIsSavingStore(false);
      }
    }
  }, [isSavingStore, showNotice]);

  const persistPlaylistStore = useCallback(async (
    playlists: string[],
    configurations: Record<string, SegmentConfiguration[]>,
    selectedIndex: number,
    nextSelectedConfigName = configName,
    successMessage = 'Playlist store updated.',
  ) => {
    return runStoreMutation(async () => {
      const payload = { playlists, configurations };
      await saveConfigurationStore(payload);
      if (!isMountedRef.current) {
        return;
      }

      const boundedIndex = playlists.length === 0 ? 0 : Math.max(0, Math.min(selectedIndex, playlists.length - 1));
      const nextPlaylist = playlists[boundedIndex] || '';
      setApiPlaylists(playlists);
      setApiConfigurations(configurations);
      setPlaylistIndex(boundedIndex);
      setPlaylistNameDraft(nextPlaylist);
      setConfigName(nextSelectedConfigName);
      setSelectedConfigName(nextSelectedConfigName);

      if (nextPlaylist) {
        sendInstruction({
          page: 'topology',
          action: 'modify_configuration',
          payload: { playlist: nextPlaylist, configuration: nextSelectedConfigName }
        });
      }

      showNotice('success', 'CONFIGURATION STORE', successMessage);
    });
  }, [configName, runStoreMutation, showNotice]);

  const handleCreatePlaylist = async () => {
    const newName = playlistNameDraft.trim();
    if (!newName) {
      showNotice('warning', 'PLAYLIST', 'Please enter a playlist name.');
      return;
    }
    if (apiPlaylists.some(name => sameName(name, newName))) {
      showNotice('warning', 'PLAYLIST', `Playlist "${newName}" already exists.`);
      return;
    }

    const nextPlaylists = [...apiPlaylists, newName];
    const nextConfigurations = { ...apiConfigurations, [newName]: [] };
    await persistPlaylistStore(nextPlaylists, nextConfigurations, nextPlaylists.length - 1, '', `Playlist "${newName}" created.`);
  };

  const handleRenamePlaylist = async () => {
    const newName = playlistNameDraft.trim();
    if (!playlist) {
      showNotice('warning', 'PLAYLIST', 'Please select a playlist to rename.');
      return;
    }
    if (!newName) {
      showNotice('warning', 'PLAYLIST', 'Please enter a playlist name.');
      return;
    }
    if (sameName(newName, playlist)) {
      return;
    }
    if (apiPlaylists.some(name => !sameName(name, playlist) && sameName(name, newName))) {
      showNotice('warning', 'PLAYLIST', `Playlist "${newName}" already exists.`);
      return;
    }

    const nextPlaylists = apiPlaylists.map(name => sameName(name, playlist) ? newName : name);
    const nextConfigurations = { ...apiConfigurations, [newName]: apiConfigurations[playlist] || [] };
    delete nextConfigurations[playlist];
    await persistPlaylistStore(nextPlaylists, nextConfigurations, playlistIndex, selectedConfigName, `Playlist renamed to "${newName}".`);
  };

  const handleDeletePlaylist = async () => {
    if (!playlist) {
      showNotice('warning', 'PLAYLIST', 'Please select a playlist to delete.');
      return;
    }
    if (!window.confirm(`Delete playlist "${playlist}" and all of its saved configurations?`)) {
      return;
    }

    const nextPlaylists = apiPlaylists.filter(name => !sameName(name, playlist));
    const nextConfigurations = { ...apiConfigurations };
    delete nextConfigurations[playlist];
    const nextIndex = nextPlaylists.length === 0 ? 0 : Math.min(playlistIndex, nextPlaylists.length - 1);
    const nextPlaylist = nextPlaylists[nextIndex] || '';
    const nextConfigName = nextPlaylist ? (nextConfigurations[nextPlaylist]?.[0]?.name ?? '') : '';

    await persistPlaylistStore(nextPlaylists, nextConfigurations, nextIndex, nextConfigName, `Playlist "${playlist}" deleted.`);
  };

  const handlePlaylistCycle = (direction: 1 | -1) => {
    if (apiPlaylists.length === 0) {
      return;
    }

    setPlaylistIndex(prev => {
      let next = prev + direction;
      if (next >= apiPlaylists.length) next = 0;
      if (next < 0) next = apiPlaylists.length - 1;

      const selectedPlaylist = apiPlaylists[next];
      setPlaylistNameDraft(selectedPlaylist);
      sendInstruction({
        page: 'topology',
        action: 'select_playlist_slot',
        payload: { playlist: selectedPlaylist, direction: direction === 1 ? 'next' : 'previous' }
      });
      return next;
    });
  };

  const handleConfigSelect = (event: ChangeEvent<HTMLSelectElement>) => {
    if (!playlist) {
      return;
    }

    const selectedName = event.target.value;
    setConfigName(selectedName);
    setSelectedConfigName(selectedName);
    sendInstruction({
      page: 'topology',
      action: 'select_configuration',
      payload: { playlist, configuration: selectedName }
    });
    applyStoredConfigurationToSegments(playlist, selectedName);
  };

  const handleSave = async () => {
    if (editorMode === 'LIVE') {
      showNotice('warning', 'LIVE MODE', 'Switch to MODIFY or BUILD to save a preset. Live mode only sends runtime changes.');
      return;
    }
    const trimmedConfigName = configName.trim();
    if (!trimmedConfigName) {
      showNotice('warning', 'CONFIGURATION', 'Please enter a configuration name.');
      return;
    }
    if (!playlist) {
      showNotice('warning', 'CONFIGURATION', 'Please select a playlist before saving.');
      return;
    }

    const newModes: Record<string, string> = {};
    const newWay: Record<string, string> = {};
    segments.forEach(seg => {
      const key = `Segment ${seg.id}`;
      newModes[key] = seg.mode;
      newWay[key] = seg.direction;
    });

    const existingConfig = (apiConfigurations[playlist] || []).find(config => sameName(config.name, selectedConfigName || trimmedConfigName)) ?? null;
    const nextModeSettings =
      Object.keys(activeModeSettings).length > 0
        ? cloneModeSettings(activeModeSettings)
        : cloneModeSettings(existingConfig?.modeSettings || {});

    const nextConfig: SegmentConfiguration = {
      name: trimmedConfigName,
      modes: newModes,
      way: newWay,
      modeSettings: nextModeSettings,
    };

    const updatedConfigs = { ...apiConfigurations };
    const configsForPlaylist = [...(updatedConfigs[playlist] || [])];
    updatedConfigs[playlist] = configsForPlaylist;

    if (editorMode === 'MODIFY') {
      const configToUpdate = selectedConfigName || trimmedConfigName;
      const idx = configsForPlaylist.findIndex(config => sameName(config.name, configToUpdate));
      if (idx >= 0) {
        configsForPlaylist[idx] = nextConfig;
      } else {
        configsForPlaylist.push(nextConfig);
      }
    } else {
      const existingIndex = configsForPlaylist.findIndex(config => sameName(config.name, trimmedConfigName));
      if (existingIndex >= 0) {
        const confirmed = window.confirm(`Configuration "${trimmedConfigName}" already exists in ${playlist}. Overwrite it instead of creating a duplicate?`);
        if (!confirmed) {
          showNotice('warning', 'CONFIGURATION', 'Save cancelled. Pick a different name or confirm overwrite.');
          return;
        }
        configsForPlaylist[existingIndex] = nextConfig;
      } else {
        configsForPlaylist.push(nextConfig);
      }
    }

    await runStoreMutation(async () => {
      const payload = { playlists: apiPlaylists, configurations: updatedConfigs };
      await saveConfigurationStore(payload);
      if (!isMountedRef.current) {
        return;
      }

      setApiConfigurations(updatedConfigs);
      setSelectedConfigName(trimmedConfigName);
      setConfigName(trimmedConfigName);
      sendInstruction({
        page: 'topology',
        action: editorMode === 'BUILD' ? 'build_configuration' : 'modify_configuration',
        payload: { playlist, configuration: trimmedConfigName }
      });
      showNotice('success', 'CONFIGURATION', `Configuration "${trimmedConfigName}" saved to ${playlist}.`);
    });
  };

  const handleRenameConfiguration = async () => {
    const newName = configName.trim();
    if (!playlist) {
      showNotice('warning', 'CONFIGURATION', 'Please select a playlist first.');
      return;
    }
    if (!selectedConfigName) {
      showNotice('warning', 'CONFIGURATION', 'Please select a configuration to rename.');
      return;
    }
    if (!newName) {
      showNotice('warning', 'CONFIGURATION', 'Please enter a new configuration name.');
      return;
    }
    if (sameName(newName, selectedConfigName)) {
      return;
    }

    const configsForPlaylist = apiConfigurations[playlist] || [];
    if (configsForPlaylist.some(config => !sameName(config.name, selectedConfigName) && sameName(config.name, newName))) {
      showNotice('warning', 'CONFIGURATION', `Configuration "${newName}" already exists in ${playlist}.`);
      return;
    }

    const updatedConfigs = {
      ...apiConfigurations,
      [playlist]: configsForPlaylist.map(config =>
        sameName(config.name, selectedConfigName) ? { ...config, name: newName } : config
      ),
    };

    await runStoreMutation(async () => {
      const payload = { playlists: apiPlaylists, configurations: updatedConfigs };
      await saveConfigurationStore(payload);
      if (!isMountedRef.current) {
        return;
      }

      setApiConfigurations(updatedConfigs);
      setSelectedConfigName(newName);
      setConfigName(newName);
      sendInstruction({
        page: 'topology',
        action: 'modify_configuration',
        payload: { playlist, configuration: newName }
      });
      showNotice('success', 'CONFIGURATION', `Configuration renamed to "${newName}".`);
    });
  };

  const handleDeleteConfiguration = async () => {
    if (!playlist) {
      showNotice('warning', 'CONFIGURATION', 'Please select a playlist first.');
      return;
    }
    if (!selectedConfigName) {
      showNotice('warning', 'CONFIGURATION', 'Please select a configuration to delete.');
      return;
    }
    if (!window.confirm(`Delete configuration "${selectedConfigName}" from ${playlist}?`)) {
      return;
    }

    const configsForPlaylist = apiConfigurations[playlist] || [];
    const updatedPlaylistConfigs = configsForPlaylist.filter(config => !sameName(config.name, selectedConfigName));
    const nextConfigName = updatedPlaylistConfigs[0]?.name || '';
    const updatedConfigs = {
      ...apiConfigurations,
      [playlist]: updatedPlaylistConfigs,
    };

    await runStoreMutation(async () => {
      const payload = { playlists: apiPlaylists, configurations: updatedConfigs };
      await saveConfigurationStore(payload);
      if (!isMountedRef.current) {
        return;
      }

      setApiConfigurations(updatedConfigs);
      setSelectedConfigName(nextConfigName);
      setConfigName(nextConfigName);
      sendInstruction({
        page: 'topology',
        action: 'modify_configuration',
        payload: { playlist, configuration: nextConfigName }
      });
      showNotice('success', 'CONFIGURATION', `Configuration "${selectedConfigName}" deleted.`);
    });
  };

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
    if (editorMode === 'LIVE') {
      const prev = pendingLiveSegmentEditsRef.current.get(selectedSegId) ?? {};
      pendingLiveSegmentEditsRef.current.set(selectedSegId, { ...prev, mode: modeName });
    }
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
      if (editorMode === 'LIVE') {
        const prevPending = pendingLiveSegmentEditsRef.current.get(id) ?? {};
        pendingLiveSegmentEditsRef.current.set(id, { ...prevPending, direction });
      }
      return { ...seg, direction };
    }));
  };

  const handleSegmentSelect = (segmentId: string) => {
    setSelectedSegId(segmentId);
    sendInstruction({ page: 'topology', action: 'select_segment', payload: { segmentId } });
  };

  const handleEditorModeChange = (mode: EditorMode) => {
    const previousMode = editorMode;
    setEditorMode(mode);
    sendInstruction({ page: 'topology', action: 'set_editor_mode', payload: { mode } });
    if (previousMode === 'LIVE' && mode === 'MODIFY' && playlist && selectedConfigName) {
      applyStoredConfigurationToSegments(playlist, selectedConfigName);
    }
  };

  return (
    <div style={{ width: '100%', height: 'calc(35 * var(--stud))', overflowX: 'auto', overflowY: 'auto' }}>
      <div style={{ position: 'relative', width: `${LEGO_MATH.physicalSize(68)}px`, minWidth: '100%', height: `${LEGO_MATH.physicalSize(38)}px` }}>
        {bridgeStatus !== 'open' ? (
          <div style={{ position: 'absolute', top: '12px', left: '770px', width: '470px', zIndex: 40 }}>
            <NoticeBanner tone={bridgeStatus === 'connecting' ? 'warning' : 'error'} title="TOPOLOGY LINK">
              {bridgeStatus === 'connecting'
                ? 'Reconnecting to the live controller. Segment changes may be delayed for a moment.'
                : 'Controller offline. Segment changes cannot be confirmed and saved presets may drift from live state.'}
            </NoticeBanner>
          </div>
        ) : null}

        {notice ? (
          <div style={{ position: 'absolute', top: bridgeStatus !== 'open' ? '96px' : '12px', left: '770px', width: '470px', zIndex: 41 }}>
            <NoticeBanner tone={notice.tone} title={notice.title}>
              {notice.message}
            </NoticeBanner>
          </div>
        ) : null}

        <TopologyMap
          segments={segments}
          selectedSegId={selectedSegId}
          onSelectSegment={handleSegmentSelect}
          onToggleDirection={handleDirectionToggle}
        />

        <TopologyEditorModeSwitch
          editorMode={editorMode}
          onModeChange={handleEditorModeChange}
        />

        <TopologyInspectorShell />

        <TopologySegmentInspector
          selectedSeg={selectedSeg}
          availableModes={availableModes}
          onModeSelect={handleModeSelect}
        />

        <TopologyConfigurationPanel
          editorMode={editorMode}
          playlist={playlist}
          apiConfigurations={apiConfigurations}
          selectedConfigName={selectedConfigName}
          configName={configName}
          isSaving={isSavingStore}
          onConfigSelect={handleConfigSelect}
          onConfigNameChange={setConfigName}
          onRenameConfiguration={handleRenameConfiguration}
          onDeleteConfiguration={handleDeleteConfiguration}
          onSave={handleSave}
        />

        <TopologyPlaylistPanel
          editorMode={editorMode}
          playlist={playlist}
          playlistNameDraft={playlistNameDraft}
          playlistLightColor={playlistLightColor}
          isSaving={isSavingStore}
          onPlaylistNameChange={setPlaylistNameDraft}
          onCreatePlaylist={handleCreatePlaylist}
          onRenamePlaylist={handleRenamePlaylist}
          onDeletePlaylist={handleDeletePlaylist}
          onPlaylistCycle={handlePlaylistCycle}
        />
      </div>
    </div>
  );
};
