// Lightweight compile shims used only when node_modules are unavailable in this sandbox.
declare namespace JSX {
  interface Element {}
  interface ElementChildrenAttribute { children: {} }
  interface IntrinsicElements { [elemName: string]: any }
}

declare namespace React { type ReactNode = any; }

declare module 'react' {
  export type ReactNode = any;
  export function useEffect(effect: any, deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps?: any[]): T;
  export function useState<T>(initial: T | (() => T)): [T, (value: T | ((previous: T) => T)) => void];
  const React: any;
  export default React;
}

declare module 'next' { export type Metadata = any; }
declare module 'clsx' { export default function clsx(...args: any[]): string; }
declare module 'lucide-react' {
  export const Activity: any; export const Archive: any; export const Box: any; export const Boxes: any; export const CheckCircle2: any;
  export const Cpu: any; export const Database: any; export const FileJson: any; export const FileText: any; export const Gauge: any;
  export const HardDrive: any; export const Info: any; export const Layers3: any; export const PackageCheck: any; export const Play: any;
  export const PlayCircle: any; export const Radar: any; export const RefreshCcw: any; export const RotateCw: any; export const Search: any;
  export const Server: any; export const ServerCog: any; export const Settings2: any; export const ShieldAlert: any; export const ShieldCheck: any;
  export const TerminalSquare: any; export const UploadCloud: any; export const XCircle: any; export const Zap: any;
}
declare module 'recharts' { export const Area: any; export const AreaChart: any; export const CartesianGrid: any; export const ResponsiveContainer: any; export const Tooltip: any; export const XAxis: any; export const YAxis: any; }

declare const process: { env: Record<string, string | undefined> };
declare module 'tailwindcss' { export type Config = any; }
