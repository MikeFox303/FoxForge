// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';

import '../alphaTranslations';
import '../alphaTranslationsExtra';
import '../i18n';
import { RealtimeQueryBridge } from '../data/realtime';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <RealtimeQueryBridge />
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}