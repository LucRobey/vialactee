import { TopologyEditor } from './TopologyEditor';
import { loadConfigurationStore } from '../../utils/configurationStore';

const CONFIGURATOR_MODES = ['MODIFY', 'BUILD'] as const;

export const Configurator = () => (
  <TopologyEditor
    allowedModes={CONFIGURATOR_MODES}
    configurationStoreLoader={loadConfigurationStore}
    syncPlaylistsFromModeMaster={false}
  />
);
