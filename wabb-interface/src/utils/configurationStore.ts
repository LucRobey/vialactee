export type SegmentConfiguration = {
  name: string;
  modes: Record<string, string>;
  way?: Record<string, string>;
};

export type ConfigurationStore = {
  playlists: string[];
  configurations: Record<string, SegmentConfiguration[]>;
};

export const emptyConfigurationStore: ConfigurationStore = {
  playlists: [],
  configurations: {},
};

export const loadConfigurationStore = async (): Promise<ConfigurationStore> => {
  const response = await fetch('/api/configurations');
  if (!response.ok) {
    throw new Error(`Could not load configurations.json (${response.status})`);
  }

  const data = await response.json() as Partial<ConfigurationStore>;
  return {
    playlists: Array.isArray(data.playlists) ? data.playlists.filter((name): name is string => typeof name === 'string') : [],
    configurations: data.configurations && typeof data.configurations === 'object' ? data.configurations : {},
  };
};

export const saveConfigurationStore = async (store: ConfigurationStore): Promise<void> => {
  const response = await fetch('/api/configurations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(store, null, 2),
  });

  if (!response.ok) {
    throw new Error(`Could not save configurations.json (${response.status})`);
  }
};
