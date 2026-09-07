// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import type { PrinterConfigurationView } from '../../data/printerSetupClient';

type Labels = {
  configured: string;
  refresh: string;
  noConfigured: string;
  bambu: string;
  moonraker: string;
  configuredSecret: string;
  reconnect: string;
  reconnecting: string;
  remove: string;
  deleting: string;
};

export function ConfiguredPrintersPanel({
  configurations,
  loading,
  busyPrinter,
  labels,
  onRefresh,
  onReconnect,
  onRemove,
}: {
  configurations: readonly PrinterConfigurationView[];
  loading: boolean;
  busyPrinter: string | null;
  labels: Labels;
  onRefresh: () => void;
  onReconnect: (printerId: string) => void;
  onRemove: (printerId: string) => void;
}) {
  return (
    <section className="setup-section">
      <div className="setup-section-head">
        <h3>{labels.configured}</h3>
        <button className="text-button" type="button" onClick={onRefresh}>{labels.refresh}</button>
      </div>
      {loading ? (
        <div className="setup-placeholder">…</div>
      ) : configurations.length === 0 ? (
        <div className="setup-placeholder">{labels.noConfigured}</div>
      ) : (
        <div className="configured-printers">
          {configurations.map((printer) => {
            const busy = busyPrinter === printer.printerId;
            return (
              <article className="configured-printer" key={printer.printerId}>
                <div>
                  <strong>{printer.displayName}</strong>
                  <span>{printer.kind === 'bambu' ? labels.bambu : labels.moonraker}</span>
                  <small>{printer.kind === 'bambu' ? printer.connection.host : printer.connection.baseUrl}</small>
                  {(printer.connection.accessCodeConfigured || printer.connection.apiKeyConfigured) && (
                    <small>{labels.configuredSecret}</small>
                  )}
                </div>
                <div className="configured-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={busy}
                    onClick={() => onReconnect(printer.printerId)}
                  >
                    {busy ? labels.reconnecting : labels.reconnect}
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    disabled={busy}
                    onClick={() => onRemove(printer.printerId)}
                  >
                    {busy ? labels.deleting : labels.remove}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
