// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const sourceRoot = path.resolve(process.cwd(), 'src');

describe('application composition', () => {
  it('renders exactly one PrinterSetupLauncher tree', () => {
    const main = fs.readFileSync(path.join(sourceRoot, 'main.tsx'), 'utf8');
    const app = fs.readFileSync(path.join(sourceRoot, 'FoxForgeApp.tsx'), 'utf8');
    const occurrences = `${main}\n${app}`.match(/<PrinterSetupLauncher\b/g) ?? [];

    expect(occurrences).toHaveLength(1);
  });
});
