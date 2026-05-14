import type { ModeSettingValue } from './controlBridge';
import configurationsJsonRaw from '../../../data/configurations.json?raw';

export type ModeSettingsMap = Record<string, Record<string, ModeSettingValue>>;

export type SegmentConfiguration = {
  name: string;
  modes: Record<string, string>;
  way?: Record<string, string>;
  modeSettings?: ModeSettingsMap;
};

export type ConfigurationStore = {
  playlists: string[];
  configurations: Record<string, SegmentConfiguration[]>;
};

export const emptyConfigurationStore: ConfigurationStore = {
  playlists: [],
  configurations: {},
};

const normalizeConfigurationStore = (data: Partial<ConfigurationStore>): ConfigurationStore => {
  const rawConfigurations = data.configurations && typeof data.configurations === 'object' ? data.configurations : {};
  const normalizedConfigurations: Record<string, SegmentConfiguration[]> = {};

  Object.entries(rawConfigurations).forEach(([playlistName, configs]) => {
    if (!Array.isArray(configs)) {
      return;
    }

    normalizedConfigurations[playlistName] = configs
      .filter((config): config is SegmentConfiguration => Boolean(config) && typeof config === 'object')
      .map((config) => ({
        name: typeof config.name === 'string' ? config.name : '',
        modes: config.modes && typeof config.modes === 'object' ? config.modes : {},
        way: config.way && typeof config.way === 'object' ? config.way : {},
        modeSettings: config.modeSettings && typeof config.modeSettings === 'object' ? config.modeSettings : {},
      }));
  });

  return {
    playlists: Object.keys(normalizedConfigurations),
    configurations: normalizedConfigurations,
  };
};

const loadConfigurationStoreFrom = async (sourceUrl: string): Promise<ConfigurationStore> => {
  const response = await fetch(sourceUrl);
  if (!response.ok) {
    throw new Error(`Could not load configurations.json (${response.status})`);
  }

  const data = await response.json() as Partial<ConfigurationStore>;
  return normalizeConfigurationStore(data);
};

export const loadConfigurationStore = async (): Promise<ConfigurationStore> =>
  loadConfigurationStoreFrom('/api/configurations');

export const loadConfigurationFileStore = async (): Promise<ConfigurationStore> =>
  Promise.resolve(normalizeConfigurationStore(JSON.parse(configurationsJsonRaw) as Partial<ConfigurationStore>));

export const saveConfigurationStore = async (store: ConfigurationStore): Promise<void> => {
  const response = await fetch('/api/configurations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ configurations: store.configurations }, null, 2),
  });

  if (!response.ok) {
    throw new Error(`Could not save configurations.json (${response.status})`);
  }
};
