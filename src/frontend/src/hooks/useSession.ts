import { useSyncExternalStore } from 'react';

import { getAccessToken, subscribeToAccessToken } from '../store/session';

export const useAccessToken = () =>
    useSyncExternalStore(subscribeToAccessToken, getAccessToken, getAccessToken);
