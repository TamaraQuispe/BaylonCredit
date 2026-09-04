interface PublicKeyCredentialDescriptorLike {
  id: ArrayBuffer
  type?: string
  transports?: string[]
}

interface WebauthnRequestOptions {
  challenge: ArrayBuffer
  rpId?: string
  timeout?: number
  userVerification?: string
  allowCredentials?: PublicKeyCredentialDescriptorLike[]
  pubKeyCredParams?: Array<{ type: string; alg: number }>
  attestation?: string
  authenticatorSelection?: Record<string, unknown>
  extensions?: Record<string, unknown>
}

interface WebauthnResponseData {
  authenticatorData?: ArrayBuffer
  clientDataJSON: ArrayBuffer
  signature?: ArrayBuffer
  userHandle?: ArrayBuffer
  attestationObject?: ArrayBuffer
  transports?: string[]
}

interface WebauthnCredential {
  id: ArrayBuffer
  rawId: ArrayBuffer
  type: string
  authenticatorAttachment?: string
  response: WebauthnResponseData
}

interface WebauthnUserCredential extends WebauthnCredential {
  source: string
}

interface WebauthnCredentialMediator {
  get(
    options: { publicKey: WebauthnRequestOptions },
  ): Promise<WebauthnCredential | WebauthnUserCredential | null>
  create(
    options: { publicKey: Record<string, unknown> },
  ): Promise<WebauthnCredential | WebauthnUserCredential | null>
}

interface WebauthnNavigatorCredentials {
  get?: (options: { publicKey: WebauthnRequestOptions }) => Promise<WebauthnCredential | null>
  create?: (
    options: { publicKey: Record<string, unknown> },
  ) => Promise<WebauthnCredential | null>
}
