// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

type CryptoWithOptionalRandomUuid = Omit<Crypto, 'randomUUID'> & {
  randomUUID?: () => string;
};

export function installRandomUuidFallback(
  cryptoObject: CryptoWithOptionalRandomUuid = globalThis.crypto,
): void {
  if (typeof cryptoObject.randomUUID === 'function') return;
  if (typeof cryptoObject.getRandomValues !== 'function') {
    throw new Error('Secure random number generation is unavailable in this browser.');
  }

  Object.defineProperty(cryptoObject, 'randomUUID', {
    configurable: true,
    enumerable: false,
    writable: true,
    value: () => createUuidV4(cryptoObject),
  });
}

function createUuidV4(cryptoObject: Pick<Crypto, 'getRandomValues'>): string {
  const bytes = new Uint8Array(16);
  cryptoObject.getRandomValues(bytes);

  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0'));
  return [
    hex.slice(0, 4).join(''),
    hex.slice(4, 6).join(''),
    hex.slice(6, 8).join(''),
    hex.slice(8, 10).join(''),
    hex.slice(10, 16).join(''),
  ].join('-');
}
