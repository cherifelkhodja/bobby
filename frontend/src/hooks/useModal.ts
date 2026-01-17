/**
 * useModal - Hook for modal state management
 *
 * Provides open/close state and data management for modals.
 * Supports passing data when opening a modal.
 *
 * @example
 * // Simple modal
 * const modal = useModal();
 * <Button onClick={modal.open}>Open</Button>
 * <Modal isOpen={modal.isOpen} onClose={modal.close}>...</Modal>
 *
 * // Modal with data
 * const detailModal = useModal<User>();
 * <Button onClick={() => detailModal.openWith(user)}>View</Button>
 * <Modal isOpen={detailModal.isOpen} onClose={detailModal.close}>
 *   {detailModal.data && <UserDetail user={detailModal.data} />}
 * </Modal>
 */

import { useState, useCallback } from 'react';

interface UseModalResult<T = undefined> {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Data passed to the modal */
  data: T | null;
  /** Open the modal without data */
  open: () => void;
  /** Open the modal with data */
  openWith: (data: T) => void;
  /** Close the modal and clear data */
  close: () => void;
  /** Toggle the modal */
  toggle: () => void;
  /** Update the modal data without changing open state */
  setData: (data: T | null) => void;
}

export function useModal<T = undefined>(): UseModalResult<T> {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<T | null>(null);

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const openWith = useCallback((modalData: T) => {
    setData(modalData);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    // Clear data after animation completes
    setTimeout(() => setData(null), 200);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  return {
    isOpen,
    data,
    open,
    openWith,
    close,
    toggle,
    setData,
  };
}
