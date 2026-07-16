/**
 * NetworkStatus - Component to show network connectivity status
 *
 * Displays a banner when the user is offline.
 */

import { useEffect, useState } from 'react';
import { WifiOff, Wifi } from 'lucide-react';

export function NetworkStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [showReconnected, setShowReconnected] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowReconnected(true);
      // Hide the reconnected message after 3 seconds
      setTimeout(() => setShowReconnected(false), 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowReconnected(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Show nothing if online and not showing reconnected message
  if (isOnline && !showReconnected) {
    return null;
  }

  return (
    <div
      className={`fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl border shadow-lg flex items-center gap-2 transition-all duration-300 ${
        isOnline
          ? 'bg-grn-bg text-grn-fg border-[color-mix(in_oklab,var(--grn-fg)_25%,transparent)]'
          : 'bg-amb-bg text-amb-fg border-[color-mix(in_oklab,var(--amb-fg)_25%,transparent)]'
      }`}
    >
      {isOnline ? (
        <>
          <Wifi className="h-4 w-4" />
          <span className="text-[13px] font-medium">Connexion rétablie</span>
        </>
      ) : (
        <>
          <WifiOff className="h-4 w-4" />
          <span className="text-[13px] font-medium">
            Vous êtes hors ligne
          </span>
        </>
      )}
    </div>
  );
}

/**
 * useNetworkStatus - Hook to get network status
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return { isOnline };
}
