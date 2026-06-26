import React, { createContext, useContext } from 'react';

import { useAuth } from '../hooks/use-auth';
import { useRelationshipState, UseRelationshipStateResult } from '../hooks/use-relationship-state';

// ── Context ───────────────────────────────────────────────────────────────────

const RelationshipStateContext = createContext<UseRelationshipStateResult | null>(null);

// ── Provider ─────────────────────────────────────────────────────────────────
//
// Mount this once above all tab screens. Both the Discovery screen and the
// My Events screen consume the same state instance, so an intent toggle on
// either screen is instantly reflected everywhere.

export function RelationshipStateProvider({ children }: { children: React.ReactNode }) {
  const { accessToken } = useAuth();
  const value = useRelationshipState(accessToken);
  return (
    <RelationshipStateContext.Provider value={value}>
      {children}
    </RelationshipStateContext.Provider>
  );
}

// ── Consumer hook ─────────────────────────────────────────────────────────────

export function useRelationshipContext(): UseRelationshipStateResult {
  const ctx = useContext(RelationshipStateContext);
  if (!ctx) throw new Error('useRelationshipContext must be used inside <RelationshipStateProvider>');
  return ctx;
}
