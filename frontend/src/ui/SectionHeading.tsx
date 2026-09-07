// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { ReactNode } from 'react';

export function SectionHeading({
  eyebrow,
  title,
  trailing,
  compact = false,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  trailing?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={`printer-section-heading ${compact ? 'compact-heading' : ''}`.trim()}>
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h3>{title}</h3>
      </div>
      {trailing !== undefined && trailing !== null ? trailing : null}
    </div>
  );
}
