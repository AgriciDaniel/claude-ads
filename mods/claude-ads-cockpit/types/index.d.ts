// Original declaration for the companion's session-only cached drawing.
declare module 'claude-code' {
  interface PluginState {
    'ads-cockpit': {
      view: {
        visible: boolean
        selected: string | null
        tab: 'Run' | 'Evidence' | 'Inputs' | 'Compare' | 'Reports'
        snapshot: unknown
        doctor: unknown
        receipt: unknown
        error: string | null
        busy: boolean
        demo: unknown
        baseline: string
        context: { kind: 'inputs'; workerId: string; missingInput: string; inputIds: string[]; match: 'text' | 'platform' | 'none' } | { kind: 'finding'; platform: string; controlId: string } | null
      }
    }
  }
}
