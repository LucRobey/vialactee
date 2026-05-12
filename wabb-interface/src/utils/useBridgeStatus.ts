import { useEffect, useState } from 'react';
import { getBridgeStatus, subscribeBridgeStatus, type SocketStatus } from './controlBridge';

export const useBridgeStatus = () => {
  const [status, setStatus] = useState<SocketStatus>(getBridgeStatus());

  useEffect(() => {
    return subscribeBridgeStatus(setStatus);
  }, []);

  return status;
};
