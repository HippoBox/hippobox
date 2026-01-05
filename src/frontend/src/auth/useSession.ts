import { useSyncExternalStore } from 'react';

import { getAccessToken, subscribeToAccessToken } from './session';

export const useAccessToken = () =>
    useSyncExternalStore(subscribeToAccessToken, getAccessToken, getAccessToken);
