// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

export type NavigationKey =
  | 'overview'
  | 'printers'
  | 'queue'
  | 'materials'
  | 'inventory'
  | 'farm'
  | 'system';

export interface NavigationItem {
  path: string;
  icon: string;
  key: NavigationKey;
}

export const navigation: readonly NavigationItem[] = [
  { path: '/', icon: 'OV', key: 'overview' },
  { path: '/printers', icon: 'PR', key: 'printers' },
  { path: '/queue', icon: 'QU', key: 'queue' },
  { path: '/materials', icon: 'MT', key: 'materials' },
  { path: '/inventory', icon: 'SP', key: 'inventory' },
  { path: '/farm', icon: 'FM', key: 'farm' },
  { path: '/system', icon: 'SY', key: 'system' },
];

export function activeNavigationItem(pathname: string): NavigationItem {
  return navigation.find((item) => (
    item.path === '/' ? pathname === '/' : pathname === item.path || pathname.startsWith(`${item.path}/`)
  )) ?? navigation[0];
}
