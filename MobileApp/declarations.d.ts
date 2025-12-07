// In declarations.d.ts

declare module 'react-native-udp' {
  // We can add more specific types here, but for now, just declaring the
  // module is enough to solve the "Cannot find module" error.
  const dgram: any;
  export default dgram;
}

declare module 'base-64' {
  // Also declare the base-64 module to be safe
  export function encode(input: string): string;
  export function decode(input: string): string;
}