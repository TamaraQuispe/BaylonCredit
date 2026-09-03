function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function base64UrlToBytes(value: string): Uint8Array {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padding = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4))
  const b64 = base64 + padding
  const binary = atob(b64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

export function bufferToBase64Url(buffer: ArrayBuffer | Uint8Array): string {
  return bytesToBase64Url(new Uint8Array(buffer))
}

export function base64UrlToBuffer(value: string): ArrayBuffer {
  const typed = base64UrlToBytes(value)
  const copy = new Uint8Array(typed.length)
  copy.set(typed)
  return copy.buffer as ArrayBuffer
}

export function base64UrlToString(value: string): string {
  const bytes = base64UrlToBytes(value)
  return new TextDecoder().decode(bytes)
}