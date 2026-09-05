// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303
/// <reference types="vite/client" />

import { describe, expect, it } from 'vitest';

const stylesheets = import.meta.glob<string>('./**/*.css', {
  query: '?raw',
  import: 'default',
  eager: true,
});

const declarationPattern = /(--[A-Za-z0-9_-]+)\s*:/g;
const usagePattern = /var\(\s*(--[A-Za-z0-9_-]+)(\s*,)?/g;

describe('CSS custom properties', () => {
  it('does not use undefined custom properties without a fallback', () => {
    const declared = new Set<string>();

    for (const source of Object.values(stylesheets)) {
      declarationPattern.lastIndex = 0;
      for (let match = declarationPattern.exec(source); match; match = declarationPattern.exec(source)) {
        declared.add(match[1]);
      }
    }

    const unresolved: string[] = [];
    for (const [path, source] of Object.entries(stylesheets)) {
      usagePattern.lastIndex = 0;
      for (let match = usagePattern.exec(source); match; match = usagePattern.exec(source)) {
        const [, token, fallback] = match;
        if (!declared.has(token) && !fallback) {
          unresolved.push(`${path}: ${token}`);
        }
      }
    }

    expect(unresolved).toEqual([]);
  });
});
