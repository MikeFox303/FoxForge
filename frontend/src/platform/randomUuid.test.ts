// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 MikeFox303

import { describe, expect, it, vi } from 'vitest';

import { installRandomUuidFallback } from './randomUuid';

describe('installRandomUuidFallback', () => {
  it('preserves a native randomUUID implementation', () => {
    const nativeRandomUuid = vi.fn(() => 'native-uuid');
    const getRandomValues = vi.fn();
    const cryptoObject = {
      randomUUID: nativeRandomUuid,
      getRandomValues,
    } as unknown as Crypto;

    installRandomUuidFallback(cryptoObject);

    expect(cryptoObject.randomUUID()).toBe('native-uuid');
    expect(getRandomValues).not.toHaveBeenCalled();
  });

  it('installs an RFC 4122 v4 UUID using getRandomValues when randomUUID is unavailable', () => {
    const getRandomValues = vi.fn((bytes: Uint8Array) => {
      bytes.set([
        0x00, 0x11, 0x22, 0x33,
        0x44, 0x55,
        0x66, 0x77,
        0x88, 0x99,
        0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff,
      ]);
      return bytes;
    });
    const cryptoObject = { getRandomValues } as unknown as Crypto;

    installRandomUuidFallback(cryptoObject);

    expect(typeof cryptoObject.randomUUID).toBe('function');
    expect(cryptoObject.randomUUID()).toBe('00112233-4455-4677-8899-aabbccddeeff');
    expect(getRandomValues).toHaveBeenCalledTimes(1);
  });

  it('fails explicitly when neither randomUUID nor getRandomValues is available', () => {
    const cryptoObject = {} as Crypto;

    expect(() => installRandomUuidFallback(cryptoObject)).toThrow(
      'Secure random number generation is unavailable in this browser.',
    );
  });
});
