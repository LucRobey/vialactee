import { TopologyEditor } from './TopologyEditor';
import { loadConfigurationFileStore } from '../../utils/configurationStore';

const CONFIGURATOR_MODES = ['MODIFY', 'BUILD'] as const;

export const Configurator = () => (
  <TopologyEditor
    allowedModes={CONFIGURATOR_MODES}
    configurationStoreLoader={loadConfigurationFileStore}
    syncPlaylistsFromModeMaster={false}
  />
);
